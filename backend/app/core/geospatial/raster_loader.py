"""GeoTIFF raster inspection, validation, and serialization module."""

from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import numpy as np
import tifffile

from backend.app.core.geospatial.coordinate_systems import is_geographic_crs
from backend.app.schemas.geospatial import RasterMetadata

# GeoTIFF Standard Tag IDs
TIFFTAG_MODEL_PIXEL_SCALE = 33550
TIFFTAG_MODEL_TIEPOINT = 33922
TIFFTAG_MODEL_TRANSFORMATION = 34264
TIFFTAG_GEO_KEY_DIRECTORY = 34735
TIFFTAG_GEO_DOUBLE_PARAMS = 34736
TIFFTAG_GEO_ASCII_PARAMS = 34737
TIFFTAG_GDAL_NODATA = 42113


def inspect_geotiff(file_path: Path) -> Tuple[np.ndarray, RasterMetadata]:
    """Inspect and validate a GeoTIFF raster file.
    
    Returns:
        (raster_array, validated_metadata_schema)
    Raises:
        ValueError: If file is not a valid GeoTIFF or cannot be read.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Raster file not found: {file_path}")

    try:
        with tifffile.TiffFile(str(file_path)) as tif:
            if not tif.pages:
                raise ValueError("TIFF file contains no valid image pages.")

            page = tif.pages[0]
            data = page.asarray()
            tags = {tag.code: tag.value for tag in page.tags}
    except Exception as err:
        raise ValueError(f"Failed to decode GeoTIFF raster: {str(err)}")

    # Extract dimensions and shape
    if data.ndim == 2:
        height, width = data.shape
        bands = 1
    elif data.ndim == 3:
        # Check if bands are first or last dimension
        if data.shape[0] < data.shape[2]:
            bands, height, width = data.shape
            data = data[0]  # Take primary band for single-band analysis
        else:
            height, width, bands = data.shape
            data = data[:, :, 0]
    else:
        raise ValueError(f"Unsupported array dimensions: {data.ndim}")

    validation_messages = []
    status = "VALID"

    # Extract Affine Georeferencing
    pixel_scale = tags.get(TIFFTAG_MODEL_PIXEL_SCALE)
    tiepoint = tags.get(TIFFTAG_MODEL_TIEPOINT)
    model_trans = tags.get(TIFFTAG_MODEL_TRANSFORMATION)

    if pixel_scale and tiepoint and len(pixel_scale) >= 2 and len(tiepoint) >= 6:
        scale_x = float(pixel_scale[0])
        scale_y = float(pixel_scale[1])
        # Tiepoint: (I, J, K, X, Y, Z) where (I, J) is pixel coord, (X, Y) is world coord
        x_origin = float(tiepoint[3])
        y_origin = float(tiepoint[4])

        minx = x_origin
        maxx = x_origin + width * scale_x
        maxy = y_origin
        miny = y_origin - height * scale_y
    elif model_trans and len(model_trans) >= 16:
        # 4x4 Affine transformation matrix (standard in many GDAL/GIS tools)
        m = [float(val) for val in model_trans]
        scale_x = abs(m[0])
        scale_y = abs(m[5])
        rot_xy = m[1]
        rot_yx = m[4]
        x_origin = m[3]
        y_origin = m[7]

        minx = x_origin
        maxx = x_origin + width * scale_x
        maxy = y_origin
        miny = y_origin - height * scale_y

        if abs(rot_xy) > 1e-6 or abs(rot_yx) > 1e-6:
            validation_messages.append(
                "Raster contains a rotated affine matrix. "
                "Regular-grid terrain gradient analysis assumes north-up alignment."
            )
            status = "ROTATED_TRANSFORM"
    else:
        # Fallback bounding box if unreferenced
        scale_x = 1.0
        scale_y = 1.0
        minx, miny, maxx, maxy = 0.0, 0.0, float(width), float(height)
        validation_messages.append("Raster lacks georeferencing tiepoint, pixel scale, or transformation tags.")
        status = "UNREFERENCED"

    # Check for invalid non-positive pixel scale
    if scale_x <= 0 or scale_y <= 0:
        validation_messages.append("Non-positive pixel resolution detected in georeferencing tags.")
        status = "INVALID_RESOLUTION"

    # Extract CRS metadata
    crs_str = None
    ascii_params = tags.get(TIFFTAG_GEO_ASCII_PARAMS)
    geo_keys = tags.get(TIFFTAG_GEO_KEY_DIRECTORY)

    if ascii_params:
        if isinstance(ascii_params, bytes):
            ascii_params = ascii_params.decode("utf-8", errors="ignore")
        crs_str = str(ascii_params).strip().replace("|", " ").strip()

    if not crs_str and geo_keys:
        # Parse GeoKey directory: header is 4 shorts, followed by key entries (4 shorts each)
        key_list = list(geo_keys)
        if len(key_list) >= 8:
            for i in range(4, len(key_list) - 3, 4):
                key_id = key_list[i]
                val = key_list[i + 3]
                if key_id in (2048, 3072):  # GeographicTypeGeoKey or ProjectedCSTypeGeoKey
                    crs_str = f"EPSG:{val}"
                    break

    if not crs_str:
        # Check coordinate bounds
        if -180.0 <= minx <= 180.0 and -90.0 <= miny <= 90.0:
            crs_str = "EPSG:4326 (Inferred WGS84 Geographic)"
            validation_messages.append("CRS unstated in GeoKeys; inferred EPSG:4326 from coordinate bounds.")
        else:
            validation_messages.append("Coordinate Reference System is unspecified.")
            if status == "VALID":
                status = "MISSING_CRS"

    # Extract Nodata
    nodata_val = None
    nodata_tag = tags.get(TIFFTAG_GDAL_NODATA)
    if nodata_tag is not None:
        try:
            if isinstance(nodata_tag, bytes):
                nodata_tag = nodata_tag.decode("utf-8")
            nodata_val = float(str(nodata_tag).strip())
        except (ValueError, TypeError):
            nodata_val = None

    # Count valid vs nodata pixels across integer and floating datatypes
    if nodata_val is not None:
        if np.isnan(nodata_val):
            nodata_mask = np.isnan(data) if np.issubdtype(data.dtype, np.floating) else np.zeros_like(data, dtype=bool)
        else:
            nodata_mask = np.isclose(data.astype(np.float64), nodata_val)
            if np.issubdtype(data.dtype, np.floating):
                nodata_mask |= np.isnan(data)
        nodata_count = int(np.sum(nodata_mask))
    else:
        nodata_mask = np.isnan(data) if np.issubdtype(data.dtype, np.floating) else np.zeros_like(data, dtype=bool)
        nodata_count = int(np.sum(nodata_mask))

    valid_count = int(data.size - nodata_count)

    metadata = RasterMetadata(
        filename=file_path.name,
        width=width,
        height=height,
        bands=bands,
        dtype=str(data.dtype),
        crs=crs_str,
        is_geographic=is_geographic_crs(crs_str),
        pixel_size_x=scale_x,
        pixel_size_y=scale_y,
        bounds={"minx": minx, "miny": miny, "maxx": maxx, "maxy": maxy},
        nodata_value=nodata_val,
        valid_pixel_count=valid_count,
        nodata_pixel_count=nodata_count,
        elevation_unit="meters",
        validation_status=status,
        validation_messages=validation_messages,
    )

    return data, metadata


def write_geotiff(
    output_path: Path,
    array: np.ndarray,
    bounds: Dict[str, float],
    pixel_size_x: float,
    pixel_size_y: float,
    nodata_value: Optional[float] = -9999.0,
    crs_str: str = "WGS 84 / UTM zone 10N | EPSG:32610",
) -> Path:
    """Write a 2D numpy array to a validated GeoTIFF with full georeferencing tags."""
    minx = float(bounds["minx"])
    maxy = float(bounds["maxy"])

    # Prepare GeoTIFF tags
    extratags = [
        # ModelPixelScaleTag: scale_x, scale_y, scale_z
        (TIFFTAG_MODEL_PIXEL_SCALE, "d", 3, (float(pixel_size_x), float(pixel_size_y), 0.0), False),
        # ModelTiepointTag: I, J, K, X, Y, Z
        (TIFFTAG_MODEL_TIEPOINT, "d", 6, (0.0, 0.0, 0.0, minx, maxy, 0.0), False),
    ]

    if nodata_value is not None:
        extratags.append((TIFFTAG_GDAL_NODATA, "s", 0, str(nodata_value), False))

    if crs_str:
        ascii_bytes = (crs_str + "|").encode("ascii", errors="replace")
        extratags.append((TIFFTAG_GEO_ASCII_PARAMS, "s", len(ascii_bytes), ascii_bytes, False))

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert array to float32
    out_arr = array.astype(np.float32)
    tifffile.imwrite(str(output_path), out_arr, extratags=extratags)
    return output_path


def validate_and_inspect_uploaded_raster(
    file_path: Path, expected_layer_type: str = "dem"
) -> Dict[str, Any]:
    """Validate an uploaded raster layer against expected scientific criteria.
    
    Checks:
    - GeoTIFF georeferencing and CRS
    - Spatial dimensions and resolution
    - NoData proportion
    - Physical value ranges (e.g. DEM elevations, NDVI values)
    """
    arr, meta = inspect_geotiff(file_path)
    valid_mask = arr != meta.nodata_value if meta.nodata_value is not None else ~np.isnan(arr)
    valid_pixels = arr[valid_mask]

    warnings = list(meta.validation_messages)
    errors = []

    if valid_pixels.size == 0:
        errors.append("Raster contains zero valid data pixels.")
        return {
            "is_valid": False,
            "errors": errors,
            "warnings": warnings,
            "metadata": meta.model_dump(),
        }

    min_val = float(np.min(valid_pixels))
    max_val = float(np.max(valid_pixels))
    mean_val = float(np.mean(valid_pixels))

    # Scientific value checks by layer type
    if expected_layer_type.lower() == "dem":
        if min_val < -500.0 or max_val > 9000.0:
            warnings.append(
                f"DEM elevation range [{min_val:.1f} m, {max_val:.1f} m] extends outside typical terrestrial topography."
            )
        if meta.height < 5 or meta.width < 5:
            errors.append(f"DEM resolution too low ({meta.width}x{meta.height}) for meaningful slope analysis.")
    elif expected_layer_type.lower() == "ndvi":
        if min_val < -1.1 or max_val > 1.1:
            warnings.append(
                f"NDVI range [{min_val:.2f}, {max_val:.2f}] extends outside standard theoretical range [-1.0, 1.0]."
            )
    elif expected_layer_type.lower() in ("red", "nir"):
        if min_val < 0.0:
            warnings.append(f"Spectral reflectance band contains negative values ({min_val:.2f}).")

    valid_pct = (valid_pixels.size / arr.size) * 100.0
    if valid_pct < 20.0:
        warnings.append(f"Low valid data coverage: only {valid_pct:.1f}% of pixels contain data.")

    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "layer_type": expected_layer_type,
        "width": meta.width,
        "height": meta.height,
        "pixel_size_x": meta.pixel_size_x,
        "pixel_size_y": meta.pixel_size_y,
        "bounds": meta.bounds,
        "crs": meta.crs,
        "min_value": round(min_val, 3),
        "max_value": round(max_val, 3),
        "mean_value": round(mean_val, 3),
        "valid_percent": round(valid_pct, 1),
        "nodata_value": meta.nodata_value,
        "metadata": meta.model_dump(),
    }


def align_and_resample_raster(
    source_path: Path, reference_path: Path, output_path: Path
) -> Path:
    """Align and resample a source raster to precisely match a reference raster grid.
    
    Uses bilinear interpolation to match the reference raster dimensions and bounds.
    """
    src_arr, src_meta = inspect_geotiff(source_path)
    ref_arr, ref_meta = inspect_geotiff(reference_path)

    if src_meta.width == ref_meta.width and src_meta.height == ref_meta.height:
        # Already same dimensions, write copy
        return write_geotiff(
            output_path=output_path,
            array=src_arr,
            bounds=ref_meta.bounds,
            pixel_size_x=ref_meta.pixel_size_x,
            pixel_size_y=ref_meta.pixel_size_y,
            nodata_value=src_meta.nodata_value or -9999.0,
            crs_str=ref_meta.crs or src_meta.crs or "EPSG:4326",
        )

    # Resample using scipy ndimage zoom
    from scipy.ndimage import zoom
    zoom_y = ref_meta.height / float(src_meta.height)
    zoom_x = ref_meta.width / float(src_meta.width)
    resampled = zoom(src_arr.astype(np.float32), (zoom_y, zoom_x), order=1)

    # Crop or pad to exact dimensions if float rounding occurs
    target_arr = np.full((ref_meta.height, ref_meta.width), src_meta.nodata_value or -9999.0, dtype=np.float32)
    h_use = min(ref_meta.height, resampled.shape[0])
    w_use = min(ref_meta.width, resampled.shape[1])
    target_arr[:h_use, :w_use] = resampled[:h_use, :w_use]

    return write_geotiff(
        output_path=output_path,
        array=target_arr,
        bounds=ref_meta.bounds,
        pixel_size_x=ref_meta.pixel_size_x,
        pixel_size_y=ref_meta.pixel_size_y,
        nodata_value=src_meta.nodata_value or -9999.0,
        crs_str=ref_meta.crs or "EPSG:4326",
    )

