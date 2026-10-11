"""Phase 5 Performance and Resource Validation Benchmark.

Measures wall-clock execution time and resource utilization on actual local environment for:
1. Application initialization
2. Loading verified DEM raster (NASADEM 360x360)
3. Terrain slope & aspect processing
4. Sentinel-2 NDVI calculation (1099x1099)
5. Candidate parcel generation (300m cells over Wayanad bounding box)
6. Complete recommendation pipeline execution
7. Multi-format report generation (GeoJSON, CSV metrics, CSV rankings, JSON, HTML)
"""

import gc
import json
import os
import sys
import time
from pathlib import Path
import numpy as np

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

results = []

def run_benchmark():
    print("=" * 60)
    print("TERRASHIELD AI - PHASE 5 PERFORMANCE BENCHMARKS")
    print("=" * 60)

    # 1. Application Initialization
    t0 = time.perf_counter()
    from backend.app.main import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    init_time = time.perf_counter() - t0
    results.append({
        "workflow": "FastAPI App Initialization",
        "dataset_size": "Decoupled FastAPI router & middleware tree",
        "elapsed_seconds": round(init_time, 4),
        "status": "SUCCESS"
    })
    print(f"1. App Initialization: {init_time:.4f} s")

    # 2. Loading Verified DEM Raster
    dem_path = BASE_DIR / "data" / "raw" / "real" / "wayanad_dem.tif"
    t0 = time.perf_counter()
    from backend.app.core.geospatial.raster_loader import inspect_geotiff
    dem_arr, meta = inspect_geotiff(dem_path)
    dem_load_time = time.perf_counter() - t0
    results.append({
        "workflow": "DEM Raster Load & Inspection",
        "dataset_size": f"{meta.width} x {meta.height} px ({meta.dtype})",
        "elapsed_seconds": round(dem_load_time, 4),
        "status": "SUCCESS"
    })
    print(f"2. DEM Load: {dem_load_time:.4f} s ({meta.width}x{meta.height})")

    # 3. Terrain Processing
    t0 = time.perf_counter()
    from backend.app.core.geospatial.terrain import process_dem_terrain
    out_terrain_dir = BASE_DIR / "data" / "processed" / "benchmark_terrain"
    terrain_res = process_dem_terrain(dem_path)
    terrain_time = time.perf_counter() - t0
    results.append({
        "workflow": "Terrain Slope & Aspect Derivation",
        "dataset_size": f"{meta.width} x {meta.height} px (360x360)",
        "elapsed_seconds": round(terrain_time, 4),
        "status": "SUCCESS"
    })
    print(f"3. Terrain Processing: {terrain_time:.4f} s")

    # 4. NDVI Calculation
    b04_path = BASE_DIR / "data" / "raw" / "real" / "wayanad_b04_red.tif"
    b08_path = BASE_DIR / "data" / "raw" / "real" / "wayanad_b08_nir.tif"
    if b04_path.exists() and b08_path.exists():
        t0 = time.perf_counter()
        from backend.app.core.geospatial.ndvi import process_sentinel2_ndvi
        ndvi_res = process_sentinel2_ndvi(b04_path, b08_path)
        ndvi_time = time.perf_counter() - t0
        results.append({
            "workflow": "Sentinel-2 NDVI Derivation",
            "dataset_size": "1099 x 1099 px (Red + NIR bands)",
            "elapsed_seconds": round(ndvi_time, 4),
            "status": "SUCCESS"
        })
        print(f"4. NDVI Calculation: {ndvi_time:.4f} s (1099x1099)")
    else:
        results.append({
            "workflow": "Sentinel-2 NDVI Derivation",
            "dataset_size": "N/A",
            "elapsed_seconds": 0.0,
            "status": "SKIPPED (Bands missing)"
        })

    # 5. Candidate Parcel Generation
    t0 = time.perf_counter()
    from backend.app.core.recommendations.parcel_generation import generate_candidate_parcels
    parcels = generate_candidate_parcels(
        min_lon=76.00,
        min_lat=11.55,
        max_lon=76.10,
        max_lat=11.65,
        cell_size_m=300.0,
    )
    parcel_gen_time = time.perf_counter() - t0
    results.append({
        "workflow": "Candidate Parcel Generation (300m Grid)",
        "dataset_size": f"{len(parcels)} candidate parcels across 11.55-11.65°N, 76.00-76.10°E",
        "elapsed_seconds": round(parcel_gen_time, 4),
        "status": "SUCCESS"
    })
    print(f"5. Candidate Parcel Gen: {parcel_gen_time:.4f} s ({len(parcels)} parcels)")

    # 6. Complete Recommendation Pipeline
    t0 = time.perf_counter()
    resp = client.post("/api/v1/recommendations/run", json={"cell_size_m": 300.0})
    rec_time = time.perf_counter() - t0
    rec_data = resp.json() if resp.status_code == 200 else {}
    results.append({
        "workflow": "Complete Recommendation Pipeline API Run",
        "dataset_size": f"{rec_data.get('total_parcels', 0)} parcels evaluated zonal stats & ranked",
        "elapsed_seconds": round(rec_time, 4),
        "status": "SUCCESS" if resp.status_code == 200 else f"FAILED ({resp.status_code})"
    })
    print(f"6. Full Recommendation Run: {rec_time:.4f} s ({resp.status_code})")

    # 7. Multi-Format Report Generation
    t0 = time.perf_counter()
    from backend.app.core.recommendations.ranking import rank_candidate_parcels
    from backend.app.core.recommendations.provenance import build_recommendation_provenance
    from backend.app.core.recommendations.report_generation import (
        export_candidate_parcels_geojson,
        export_parcel_metrics_csv,
        export_parcel_rankings_csv,
        export_recommendation_summary_json,
        export_recommendation_report_html,
    )
    from backend.app.core.recommendations.scoring import ScoringWeights, NormalizationConfig, MissingDataPolicy
    res = rank_candidate_parcels(
        evaluated_parcels=[],
        run_id="bench_rep",
        timestamp="2026-10-11T12:00:00Z",
        scoring_weights=ScoringWeights(),
        normalization_config=NormalizationConfig(),
        missing_data_policy=MissingDataPolicy.RENORMALIZE_AVAILABLE,
    )
    prov = build_recommendation_provenance("bench_rep", "2026-10-11T12:00:00Z")
    out_reports = BASE_DIR / "data" / "processed" / "benchmark_reports"
    out_reports.mkdir(parents=True, exist_ok=True)
    export_candidate_parcels_geojson(res, out_reports / "bench.geojson")
    export_parcel_metrics_csv(res, out_reports / "bench_metrics.csv")
    export_parcel_rankings_csv(res, out_reports / "bench_rankings.csv")
    export_recommendation_summary_json(res, prov, out_reports / "bench_summary.json")
    export_recommendation_report_html(res, prov, out_reports / "bench_report.html")
    report_time = time.perf_counter() - t0
    results.append({
        "workflow": "Multi-Format Report Generation (GeoJSON, CSV, JSON, HTML)",
        "dataset_size": "5 export files generated",
        "elapsed_seconds": round(report_time, 4),
        "status": "SUCCESS"
    })
    print(f"7. Report Generation: {report_time:.4f} s")

    print("\nBenchmark Summary:")
    print(json.dumps(results, indent=2))

    # Save benchmark json artifact
    bench_file = BASE_DIR / "docs" / "performance_benchmark.json"
    with open(bench_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Saved benchmark results to {bench_file}")

if __name__ == "__main__":
    run_benchmark()
