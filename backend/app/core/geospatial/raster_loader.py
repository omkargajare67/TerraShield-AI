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
    else:
        # Fallback bounding box if unreferenced
        scale_x = 1.0
        scale_y = 1.0
        minx, miny, maxx, maxy = 0.0, 0.0, float(width), float(height)
        validation_messages.append("Raster lacks georeferencing tiepoint or pixel scale tags.")
        status = "UNREFERENCED"

    # Extract CRS metadata
    crs_str = None
    ascii_params = tags.get(TIFFTAG_GEO_ASCII_PARAMS)
    geo_keys = tags.get(TIFFTAG_GEO_KEY_DIRECTORY)

    if ascii_params:
        if isinstance(ascii_params, bytes):
            ascii_params = ascii_params.decode("utf-8", errors="ignore")
        crs_str = str(ascii_params).strip().replace("|", " ").strip()

    if not crs_str and geo_keys:
        # Check for standard EPSG codes in GeoKeys
        # GeoKey directory format: [Header (4 ints), KeyID, TIFFTagLocation, Count, Value_Offset, ...]
        key_list = list(geo_keys)
        if len(key_list) >= 8:
            for i in range(4, len(key_list) - 3, 4):
                key_id = key_list[i]
                val = key_list[i + 3]
                if key_id in (2048, 3072):  # GeographicTypeGeoKey or ProjectedCSTypeGeoKey
                    crs_str = f"EPSG:{val}"
                    break

    if not crs_str:
        # If in range of typical lat/lon bounds
        if -180.0 <= minx <= 180.0 and -90.0 <= miny <= 90.0:
            crs_str = "EPSG:4326 (Inferred WGS84 Geographic)"
            validation_messages.append("CRS unstated in GeoKeys; inferred EPSG:4326 from coordinate bounds.")
        else:
            validation_messages.append("Coordinate Reference System is unspecified.")
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

    # Count valid vs nodata pixels
    if nodata_val is not None:
        nodata_mask = np.isnan(data) if np.isnan(nodata_val) else np.isclose(data, nodata_val)
        nodata_count = int(np.sum(nodata_mask))
    else:
        nodata_mask = np.isnan(data)
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
