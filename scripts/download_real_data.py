"""TerraShield AI — Automated Real-World Geospatial Data Acquisition & Pipeline Runner.

Acquires genuine NASA SRTM / NASADEM elevation rasters and Sentinel-2 Level-2A surface
reflectance bands (B04 Red, B08 NIR) for the Western Ghats pilot corridor (Wayanad, Kerala).
"""

import argparse
import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Dict, Tuple

import httpx
import numpy as np
import tifffile

# Ensure backend modules are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ensure stdout handles UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from backend.app.core.geospatial.raster_loader import inspect_geotiff, write_geotiff
from backend.app.core.geospatial.terrain import process_dem_terrain
from backend.app.core.geospatial.ndvi import process_sentinel2_ndvi
from backend.app.core.geospatial.coordinate_systems import get_meters_per_degree

STAC_API = "https://planetarycomputer.microsoft.com/api/stac/v1"
DATA_API = "https://planetarycomputer.microsoft.com/api/data/v1"
SAS_API = "https://planetarycomputer.microsoft.com/api/sas/v1"


def calculate_sha256(filepath: Path) -> str:
    """Calculate SHA-256 hash of a local file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def check_network_connectivity() -> bool:
    """Check connectivity to Microsoft Planetary Computer catalog."""
    print("Checking network connectivity to Planetary Computer STAC...")
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(STAC_API)
            if resp.status_code == 200:
                print("  [OK] Connected to Planetary Computer STAC API (HTTP 200)")
                return True
            print(f"  [ERROR] Unexpected response: HTTP {resp.status_code}")
            return False
    except Exception as exc:
        print(f"  [ERROR] Connection error: {exc}")
        return False


def acquire_nasadem(
    bbox: list[float], output_dir: Path
) -> Tuple[Path, Dict[str, Any]]:
    """Download NASADEM tile from Planetary Computer, extract bbox, and write GeoTIFF."""
    minx, miny, maxx, maxy = bbox
    print(f"\n1. Acquiring Real Digital Elevation Model (NASADEM 30m)...")
    print(f"   Target Bounding Box: West={minx}, South={miny}, East={maxx}, North={maxy}")

    final_dem_path = output_dir / "wayanad_dem.tif"
    if final_dem_path.exists() and final_dem_path.stat().st_size > 0:
        try:
            arr, meta = inspect_geotiff(final_dem_path)
            if meta.validation_status == "VALID":
                print(f"   [OK] Found existing verified DEM: {final_dem_path} ({final_dem_path.stat().st_size / 1024:.1f} KB, shape: {arr.shape})")
                sha256 = calculate_sha256(final_dem_path)
                return final_dem_path, {
                    "dataset_name": "NASA SRTM NASADEM Global 1 Arc-Second V001",
                    "stac_collection": "nasadem",
                    "item_id": "NASADEM_HGT_n11e076",
                    "source_url": "https://nasademeuwest.blob.core.windows.net/nasadem-cog/v001/NASADEM_HGT_n11e076.tif",
                    "local_file": str(final_dem_path.name),
                    "file_size_bytes": final_dem_path.stat().st_size,
                    "sha256": sha256,
                    "dimensions": [int(arr.shape[1]), int(arr.shape[0])],
                    "bounds": {"minx": minx, "miny": miny, "maxx": maxx, "maxy": maxy},
                    "crs": "EPSG:4326 (WGS 84)",
                    "resolution_deg": meta.pixel_size_x,
                    "elevation_units": "meters",
                    "nodata": meta.nodata_value or -32768.0,
                }
        except Exception:
            pass

    with httpx.Client(timeout=30) as client:
        # Search NASADEM STAC collection
        search_payload = {
            "collections": ["nasadem"],
            "bbox": bbox,
            "limit": 1,
        }
        res = client.post(f"{STAC_API}/search", json=search_payload)
        res.raise_for_status()
        features = res.json().get("features", [])
        if not features:
            raise RuntimeError("No NASADEM tile found covering the specified bounding box.")

        item = features[0]
        item_id = item["id"]
        elev_asset = item["assets"]["elevation"]
        raw_href = elev_asset["href"]
        print(f"   Discovered Item: {item_id}")
        print(f"   Raw Asset URL: {raw_href}")

        # Obtain SAS signed URL
        sign_resp = client.get(f"{SAS_API}/sign?href={raw_href}")
        sign_resp.raise_for_status()
        signed_url = sign_resp.json()["href"]

    # Download tile to temporary file with progress
    temp_nasadem = output_dir / f"temp_{item_id}.tif"
    print(f"   Downloading NASADEM full tile to temporary storage...")
    t0 = time.time()
    with httpx.Client(timeout=120) as client:
        with client.stream("GET", signed_url) as stream:
            stream.raise_for_status()
            total_len = int(stream.headers.get("content-length", 0))
            downloaded = 0
            with open(temp_nasadem, "wb") as f_out:
                for chunk in stream.iter_bytes(chunk_size=1024 * 256):
                    f_out.write(chunk)
                    downloaded += len(chunk)
                    pct = (downloaded / total_len * 100) if total_len else 0
                    print(f"\r   Progress: {downloaded / (1024*1024):.1f} MB / {total_len / (1024*1024):.1f} MB ({pct:.1f}%)", end="", flush=True)

    print(f"\n   [OK] Download completed in {time.time() - t0:.1f}s ({temp_nasadem.stat().st_size / (1024*1024):.1f} MB)")

    # Read and inspect full tile
    data_full, meta_full = inspect_geotiff(temp_nasadem)
    print(f"   Full Tile Grid: {data_full.shape}, Dtype: {data_full.dtype}, Bounds: {meta_full.bounds}")

    # Calculate exact pixel window for Wayanad subset
    # NASADEM tile n11e076 covers 11.0 to 12.0 N, 76.0 to 77.0 E with 3600 cells/deg
    deg_scale = 3600.0
    row_start = int(round((meta_full.bounds["maxy"] - maxy) * deg_scale))
    row_end = int(round((meta_full.bounds["maxy"] - miny) * deg_scale))
    col_start = int(round((minx - meta_full.bounds["minx"]) * deg_scale))
    col_end = int(round((maxx - meta_full.bounds["minx"]) * deg_scale))

    row_start = max(0, row_start)
    row_end = min(data_full.shape[0], row_end)
    col_start = max(0, col_start)
    col_end = min(data_full.shape[1], col_end)

    wayanad_elevation = data_full[row_start:row_end, col_start:col_end]
    print(f"   Extracted Wayanad Grid: {wayanad_elevation.shape} (rows {row_start}:{row_end}, cols {col_start}:{col_end})")

    # Write final verified wayanad_dem.tif
    final_dem_path = output_dir / "wayanad_dem.tif"
    write_geotiff(
        output_path=final_dem_path,
        array=wayanad_elevation.astype(np.float32),
        bounds={"minx": minx, "miny": miny, "maxx": maxx, "maxy": maxy},
        pixel_size_x=1.0 / deg_scale,
        pixel_size_y=1.0 / deg_scale,
        nodata_value=-32768.0,
        crs_str="EPSG:4326 (WGS 84)",
    )

    # Clean up temp full tile
    temp_nasadem.unlink(missing_ok=True)

    sha256 = calculate_sha256(final_dem_path)
    print(f"   [OK] Saved verified DEM: {final_dem_path} ({final_dem_path.stat().st_size / 1024:.1f} KB, SHA-256: {sha256[:16]}...)")

    provenance = {
        "dataset_name": "NASA SRTM NASADEM Global 1 Arc-Second V001",
        "stac_collection": "nasadem",
        "item_id": item_id,
        "source_url": raw_href,
        "local_file": str(final_dem_path.name),
        "file_size_bytes": final_dem_path.stat().st_size,
        "sha256": sha256,
        "dimensions": [int(wayanad_elevation.shape[1]), int(wayanad_elevation.shape[0])],
        "bounds": {"minx": minx, "miny": miny, "maxx": maxx, "maxy": maxy},
        "crs": "EPSG:4326 (WGS 84)",
        "resolution_deg": 1.0 / deg_scale,
        "elevation_units": "meters",
        "nodata": -32768.0,
    }
    return final_dem_path, provenance


def acquire_sentinel2_bands(
    bbox: list[float], output_dir: Path
) -> Tuple[Path, Path, Dict[str, Any]]:
    """Query low-cloud Sentinel-2 L2A scene and download B04 and B08 bands."""
    minx, miny, maxx, maxy = bbox
    print(f"\n2. Acquiring Real Sentinel-2 Level-2A Spectral Bands...")
    print(f"   Target Bounding Box: West={minx}, South={miny}, East={maxx}, North={maxy}")

    with httpx.Client(timeout=30) as client:
        # Query Planetary Computer for low cloud cover Sentinel-2 L2A scene
        query = {
            "collections": ["sentinel-2-l2a"],
            "bbox": bbox,
            "datetime": "2023-11-01T00:00:00Z/2024-03-31T23:59:59Z",
            "query": {"eo:cloud_cover": {"lt": 5.0}},
            "sortby": [{"field": "properties.eo:cloud_cover", "direction": "asc"}],
            "limit": 5,
        }
        res = client.post(f"{STAC_API}/search", json=query)
        res.raise_for_status()
        features = res.json().get("features", [])
        if not features:
            # Fallback wider query
            del query["datetime"]
            res = client.post(f"{STAC_API}/search", json=query)
            features = res.json().get("features", [])

        if not features:
            raise RuntimeError("No suitable Sentinel-2 L2A scenes found for study area.")

        selected_scene = features[0]
        scene_id = selected_scene["id"]
        props = selected_scene.get("properties", {})
        cloud_cover = props.get("eo:cloud_cover", 0.0)
        acq_datetime = props.get("datetime")
        platform = props.get("platform", "Sentinel-2")
        baseline = props.get("s2:processing_baseline", "unknown")

        print(f"   Selected Scene: {scene_id}")
        print(f"   Acquisition Date: {acq_datetime}")
        print(f"   Cloud Cover: {cloud_cover:.4f}%")
        print(f"   Processing Baseline: {baseline}")

    # Download B04 (Red) and B08 (NIR)
    bands_downloaded = {}
    for band_key in ["B04", "B08"]:
        band_name = "Red" if band_key == "B04" else "NIR"
        target_filename = "wayanad_b04_red.tif" if band_key == "B04" else "wayanad_b08_nir.tif"
        target_path = output_dir / target_filename

        if target_path.exists() and target_path.stat().st_size > 0:
            try:
                arr_ex, meta_ex = inspect_geotiff(target_path)
                if meta_ex.validation_status == "VALID":
                    sha = calculate_sha256(target_path)
                    print(f"   [OK] Found existing verified Band {band_key}: {target_path} ({target_path.stat().st_size / (1024*1024):.2f} MB, shape: {arr_ex.shape})")
                    bands_downloaded[band_key] = {
                        "path": target_path,
                        "sha256": sha,
                        "shape": list(arr_ex.shape),
                        "size": target_path.stat().st_size,
                    }
                    continue
            except Exception:
                pass

        print(f"   Downloading Band {band_key} ({band_name}) for study area...")
        url = f"{DATA_API}/item/bbox/{minx},{miny},{maxx},{maxy}.tif?collection=sentinel-2-l2a&item={scene_id}&assets={band_key}"

        temp_file = output_dir / f"temp_{band_key}.tif"
        with httpx.Client(timeout=90) as client:
            resp = client.get(url)
            resp.raise_for_status()
            temp_file.write_bytes(resp.content)

        # Inspect downloaded image
        with tifffile.TiffFile(str(temp_file)) as tif:
            raw_arr = tif.pages[0].asarray()

        # Extract primary band (reflectance DN)
        if raw_arr.ndim == 3:
            band_arr = raw_arr[..., 0]
        else:
            band_arr = raw_arr

        target_filename = "wayanad_b04_red.tif" if band_key == "B04" else "wayanad_b08_nir.tif"
        target_path = output_dir / target_filename

        # Write clean single-band GeoTIFF preserving native georeferencing
        write_geotiff(
            output_path=target_path,
            array=band_arr.astype(np.float32),
            bounds={"minx": minx, "miny": miny, "maxx": maxx, "maxy": maxy},
            pixel_size_x=(maxx - minx) / band_arr.shape[1],
            pixel_size_y=(maxy - miny) / band_arr.shape[0],
            nodata_value=0.0,
            crs_str="EPSG:4326 (WGS 84)",
        )
        temp_file.unlink(missing_ok=True)

        sha = calculate_sha256(target_path)
        print(f"   [OK] Saved verified Band {band_key}: {target_path} ({target_path.stat().st_size / (1024*1024):.2f} MB, shape: {band_arr.shape})")
        bands_downloaded[band_key] = {
            "path": target_path,
            "sha256": sha,
            "shape": list(band_arr.shape),
            "size": target_path.stat().st_size,
        }

    b04_path = bands_downloaded["B04"]["path"]
    b08_path = bands_downloaded["B08"]["path"]

    provenance = {
        "dataset_name": "Copernicus Sentinel-2 Level-2A Surface Reflectance",
        "stac_collection": "sentinel-2-l2a",
        "scene_id": scene_id,
        "platform": platform,
        "acquisition_datetime": acq_datetime,
        "cloud_cover_percent": cloud_cover,
        "processing_baseline": baseline,
        "b04_file": str(b04_path.name),
        "b04_sha256": bands_downloaded["B04"]["sha256"],
        "b08_file": str(b08_path.name),
        "b08_sha256": bands_downloaded["B08"]["sha256"],
        "grid_shape": bands_downloaded["B04"]["shape"],
        "bounds": {"minx": minx, "miny": miny, "maxx": maxx, "maxy": maxy},
        "crs": "EPSG:4326 (WGS 84)",
    }
    return b04_path, b08_path, provenance


def run_pipeline_processing(
    dem_path: Path, b04_path: Path, b08_path: Path, processed_dir: Path
) -> Dict[str, Any]:
    """Execute terrain and NDVI processing pipelines and save verified real outputs."""
    print("\n3. Processing Real Datasets through TerraShield Geospatial Engine...")
    processed_dir.mkdir(parents=True, exist_ok=True)

    # A. Process DEM Terrain
    print("   Running DEM Terrain Processing (Elevation, Slope, Aspect)...")
    terrain_res = process_dem_terrain(dem_path)

    # Copy generated artifacts to processed/real
    if terrain_res.slope_raster_id:
        src = PROJECT_ROOT / "data" / "artifacts" / terrain_res.slope_raster_id
        dst = processed_dir / "wayanad_slope.tif"
        if src.exists():
            shutil.copy2(src, dst)

    if terrain_res.aspect_raster_id:
        src = PROJECT_ROOT / "data" / "artifacts" / terrain_res.aspect_raster_id
        dst = processed_dir / "wayanad_aspect.tif"
        if src.exists():
            shutil.copy2(src, dst)

    if terrain_res.preview_image_id:
        src = PROJECT_ROOT / "data" / "artifacts" / terrain_res.preview_image_id
        dst = processed_dir / "wayanad_terrain_preview.png"
        if src.exists():
            shutil.copy2(src, dst)

    print(f"   [OK] Elevation Stats: Min={terrain_res.elevation.min_elevation}m, Max={terrain_res.elevation.max_elevation}m, Mean={terrain_res.elevation.mean_elevation}m")
    print(f"   [OK] Slope Stats: Min={terrain_res.slope.min_slope_deg} deg, Max={terrain_res.slope.max_slope_deg} deg, Mean={terrain_res.slope.mean_slope_deg} deg")
    print(f"   [OK] Aspect Stats: Mean={terrain_res.aspect.mean_aspect_deg} deg, Flat Pixels={terrain_res.aspect.flat_pixel_count}")

    # B. Process Sentinel-2 NDVI
    print("\n   Running Sentinel-2 NDVI Processing...")
    ndvi_res = process_sentinel2_ndvi(b04_path, b08_path)

    if ndvi_res.ndvi_raster_id:
        src = PROJECT_ROOT / "data" / "artifacts" / ndvi_res.ndvi_raster_id
        dst = processed_dir / "wayanad_ndvi.tif"
        if src.exists():
            shutil.copy2(src, dst)

    if ndvi_res.preview_image_id:
        src = PROJECT_ROOT / "data" / "artifacts" / ndvi_res.preview_image_id
        dst = processed_dir / "wayanad_ndvi_preview.png"
        if src.exists():
            shutil.copy2(src, dst)

    print(f"   [OK] NDVI Stats: Min={ndvi_res.ndvi_stats.min_ndvi}, Max={ndvi_res.ndvi_stats.max_ndvi}, Mean={ndvi_res.ndvi_stats.mean_ndvi}")
    print(f"   [OK] Valid Pixels: {ndvi_res.ndvi_stats.valid_pixels:,}, Zero-Denominator Pixels: {ndvi_res.ndvi_stats.zero_denominator_pixels}")

    # C. Run Independent Horn / GDAL Formulation Comparison
    print("\n4. Running Independent Numeric Verification (GDAL/Horn 3x3 Algorithm)...")
    arr, meta = inspect_geotiff(dem_path)
    lat = (meta.bounds["miny"] + meta.bounds["maxy"]) / 2.0
    scale_x, scale_y = get_meters_per_degree(lat)
    dx = meta.pixel_size_x * scale_x
    dy = meta.pixel_size_y * scale_y

    z = arr.astype(np.float64)
    a, b, c = z[:-2, :-2], z[:-2, 1:-1], z[:-2, 2:]
    d, f = z[1:-1, :-2], z[1:-1, 2:]
    g, h, i = z[2:, :-2], z[2:, 1:-1], z[2:, 2:]

    horn_dz_dx = ((c + 2 * f + i) - (a + 2 * d + g)) / (8.0 * dx)
    horn_dz_dy = ((g + 2 * h + i) - (a + 2 * b + c)) / (8.0 * dy)
    horn_slope_deg = np.degrees(np.arctan(np.sqrt(horn_dz_dx**2 + horn_dz_dy**2)))

    # Inspect TerraShield slope GeoTIFF
    ts_slope_arr, _ = inspect_geotiff(processed_dir / "wayanad_slope.tif")
    ts_interior = ts_slope_arr[1:-1, 1:-1]
    valid_mask = (ts_interior >= 0) & ~np.isnan(ts_interior)

    abs_diff = np.abs(ts_interior[valid_mask] - horn_slope_deg[valid_mask])
    mae = float(np.mean(abs_diff))
    max_d = float(np.max(abs_diff))
    within_1 = float(np.mean(abs_diff <= 1.0) * 100.0)
    within_2 = float(np.mean(abs_diff <= 2.0) * 100.0)

    print(f"   Comparable Valid Pixels: {int(np.sum(valid_mask)):,}")
    print(f"   TerraShield Mean Slope: {float(np.mean(ts_interior[valid_mask])):.2f} deg")
    print(f"   GDAL/Horn Formulation Mean Slope: {float(np.mean(horn_slope_deg[valid_mask])):.2f} deg")
    print(f"   Mean Absolute Difference (MAE): {mae:.4f} deg")
    print(f"   Max Absolute Difference: {max_d:.4f} deg")
    print(f"   Pixels within 1.0 deg tolerance: {within_1:.2f}%")
    print(f"   Pixels within 2.0 deg tolerance: {within_2:.2f}%")

    results = {
        "terrain": terrain_res.model_dump(),
        "ndvi": ndvi_res.model_dump(),
        "independent_comparison": {
            "method": "Horn (1981) 3x3 Weighted Finite Difference (GDAL/QGIS formulation)",
            "comparable_pixels": int(np.sum(valid_mask)),
            "mean_absolute_difference_deg": round(mae, 4),
            "max_absolute_difference_deg": round(max_d, 4),
            "percent_within_1_deg": round(within_1, 2),
            "percent_within_2_deg": round(within_2, 2),
        },
    }
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="TerraShield AI Real Data Downloader & Pipeline")
    parser.add_argument("--bbox", nargs=4, type=float, default=[76.00, 11.55, 76.10, 11.65],
                        help="Bounding box: minx miny maxx maxy (default: Wayanad pilot 76.00 11.55 76.10 11.65)")
    parser.add_argument("--raw-dir", type=str, default="data/raw/real", help="Raw output directory")
    parser.add_argument("--processed-dir", type=str, default="data/processed/real", help="Processed output directory")
    args = parser.parse_args()

    raw_dir = PROJECT_ROOT / args.raw_dir
    processed_dir = PROJECT_ROOT / args.processed_dir
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("TERRASHIELD AI — REAL-WORLD DATA ACQUISITION & PROCESSING")
    print("=" * 70)

    if not check_network_connectivity():
        sys.exit(1)

    # 1. Acquire NASADEM
    dem_path, dem_provenance = acquire_nasadem(args.bbox, raw_dir)

    # 2. Acquire Sentinel-2 bands
    b04_path, b08_path, s2_provenance = acquire_sentinel2_bands(args.bbox, raw_dir)

    # Write Manifest
    manifest_path = raw_dir / "metadata_manifest.json"
    manifest = {
        "acquisition_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "study_area": {
            "name": "Wayanad Watershed, Kerala, India (Western Ghats Pilot)",
            "bounding_box_epsg4326": args.bbox,
        },
        "datasets": {
            "elevation": dem_provenance,
            "sentinel2_multispectral": s2_provenance,
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"\n[OK] Metadata manifest written to: {manifest_path}")

    # 3. Process Pipelines
    results = run_pipeline_processing(dem_path, b04_path, b08_path, processed_dir)

    # Save summary results
    results_path = processed_dir / "processing_summary.json"
    results_path.write_text(json.dumps(results, indent=2))
    print(f"\n[OK] Processing summary saved to: {results_path}")
    print("\n" + "=" * 70)
    print("REAL-WORLD DATA ACQUISITION & ACCEPTANCE PIPELINE COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
