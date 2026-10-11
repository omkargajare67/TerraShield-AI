"""Geotechnical raster processing pipeline integrating slope rasters with infinite slope stability models."""

import json
from pathlib import Path
import shutil
from typing import Any, Dict, List, Optional, Tuple
import uuid

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from backend.app.core.config import settings
from backend.app.core.geospatial.raster_loader import inspect_geotiff, write_geotiff
from backend.app.core.geotechnical.infinite_slope import calculate_infinite_slope_array
from backend.app.core.geotechnical.models import (
    RootParameters,
    SoilParameters,
    TreeDensityCalibration,
)
from backend.app.core.geotechnical.parameter_validation import (
    validate_root_parameters,
    validate_soil_parameters,
    validate_tree_density_calibration,
)
from backend.app.core.geotechnical.required_cohesion import calculate_required_cohesion_array
from backend.app.core.geotechnical.root_cohesion import (
    calculate_reinforced_slope_array,
    calculate_root_cohesion,
)

GEOTECHNICAL_DIR = settings.PROCESSED_DIR / "geotechnical"


def generate_geotechnical_preview(
    slope_deg: np.ndarray,
    fs_baseline: np.ndarray,
    fs_reinforced: np.ndarray,
    req_cohesion: np.ndarray,
    valid_mask: np.ndarray,
    output_png_path: Path,
    title_suffix: str = "Wayanad Slope Scenario",
) -> Path:
    """Generate a high-quality 4-panel visual summary of geotechnical stability analysis."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 11), dpi=150)
    fig.patch.set_facecolor("#0f172a")

    for row in axes:
        for ax in row:
            ax.set_facecolor("#1e293b")
            ax.tick_params(colors="#94a3b8", labelsize=8)
            for spine in ax.spines.values():
                spine.set_color("#334155")

    # Panel 1: Slope
    slope_masked = np.ma.masked_where(~valid_mask | (slope_deg < 0), slope_deg)
    im0 = axes[0, 0].imshow(slope_masked, cmap="viridis", interpolation="nearest")
    axes[0, 0].set_title("Input Slope Angle (°)", color="#f8fafc", fontsize=11, fontweight="bold")
    cb0 = fig.colorbar(im0, ax=axes[0, 0], fraction=0.046, pad=0.04)
    cb0.ax.tick_params(colors="#94a3b8", labelsize=8)
    cb0.set_label("Degrees (°)", color="#94a3b8", fontsize=9)

    # Panel 2: Baseline Factor of Safety
    # Mask flat (<0.1) or invalid
    fs_base_valid = (fs_baseline > 0.0) & valid_mask
    fs_base_masked = np.ma.masked_where(~fs_base_valid, fs_baseline)
    # Clip FS display at 3.0 for visual dynamic range
    im1 = axes[0, 1].imshow(
        np.clip(fs_base_masked, 0.0, 3.0),
        cmap="RdYlGn",
        vmin=0.8,
        vmax=2.0,
        interpolation="nearest",
    )
    axes[0, 1].set_title(
        "Baseline Factor of Safety (FS₀)", color="#f8fafc", fontsize=11, fontweight="bold"
    )
    cb1 = fig.colorbar(im1, ax=axes[0, 1], fraction=0.046, pad=0.04)
    cb1.ax.tick_params(colors="#94a3b8", labelsize=8)
    cb1.set_label("FS (Capped at 2.0)", color="#94a3b8", fontsize=9)

    # Panel 3: Root-Reinforced Factor of Safety
    fs_reinf_valid = (fs_reinforced > 0.0) & valid_mask
    fs_reinf_masked = np.ma.masked_where(~fs_reinf_valid, fs_reinforced)
    im2 = axes[1, 0].imshow(
        np.clip(fs_reinf_masked, 0.0, 3.0),
        cmap="RdYlGn",
        vmin=0.8,
        vmax=2.0,
        interpolation="nearest",
    )
    axes[1, 0].set_title(
        "Root-Reinforced Factor of Safety (FS_root)",
        color="#f8fafc",
        fontsize=11,
        fontweight="bold",
    )
    cb2 = fig.colorbar(im2, ax=axes[1, 0], fraction=0.046, pad=0.04)
    cb2.ax.tick_params(colors="#94a3b8", labelsize=8)
    cb2.set_label("FS (Capped at 2.0)", color="#94a3b8", fontsize=9)

    # Panel 4: Required Root Cohesion
    req_c_valid = (req_cohesion >= 0.0) & valid_mask
    req_c_masked = np.ma.masked_where(~req_c_valid, req_cohesion)
    im3 = axes[1, 1].imshow(req_c_masked, cmap="plasma", interpolation="nearest")
    axes[1, 1].set_title(
        "Required Cohesion ΔC (kPa) for FS ≥ 1.3",
        color="#f8fafc",
        fontsize=11,
        fontweight="bold",
    )
    cb3 = fig.colorbar(im3, ax=axes[1, 1], fraction=0.046, pad=0.04)
    cb3.ax.tick_params(colors="#94a3b8", labelsize=8)
    cb3.set_label("ΔC Required (kPa)", color="#94a3b8", fontsize=9)

    fig.suptitle(
        f"TerraShield AI — Geotechnical Stability Modeling ({title_suffix} - Illustrative Scenario)",
        color="#f8fafc",
        fontsize=13,
        fontweight="bold",
        y=0.98,
    )

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    output_png_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(str(output_png_path), bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return output_png_path


def process_geotechnical_raster(
    slope_path: Path,
    soil: SoilParameters,
    root: RootParameters,
    fs_target: float = 1.3,
    calibration: Optional[TreeDensityCalibration] = None,
) -> Dict[str, Any]:
    """Execute geotechnical infinite slope stability model across a real terrain slope raster.

    Args:
        slope_path: Path to validated slope GeoTIFF.
        soil: Validated soil parameters (uniform scenario).
        root: Validated root parameters (uniform scenario).
        fs_target: Target Factor of Safety benchmark (default 1.3).
        calibration: Optional tree density empirical calibration.

    Returns:
        Structured JSON analysis summary with statistics, warnings, and artifact paths.
    """
    if not slope_path.exists():
        raise FileNotFoundError(f"Slope raster not found at: {slope_path}")

    # 1. Validate parameter models
    is_soil_valid, soil_errs = validate_soil_parameters(soil)
    if not is_soil_valid:
        raise ValueError(f"Invalid soil parameters: {'; '.join(soil_errs)}")

    is_root_valid, root_errs = validate_root_parameters(root)
    if not is_root_valid:
        raise ValueError(f"Invalid root parameters: {'; '.join(root_errs)}")

    # 2. Inspect Slope GeoTIFF
    slope_arr, metadata = inspect_geotiff(slope_path)

    # 3. Build validity mask (exclude NoData, NaN, and negative values)
    if metadata.nodata_value is not None:
        if np.isnan(metadata.nodata_value):
            nodata_mask = np.isnan(slope_arr)
        else:
            nodata_mask = np.isclose(slope_arr.astype(np.float64), metadata.nodata_value) | np.isnan(slope_arr)
    else:
        nodata_mask = np.isnan(slope_arr)

    valid_mask = ~nodata_mask & (slope_arr >= 0.0)
    total_pixels = int(slope_arr.size)
    valid_pixels = int(np.sum(valid_mask))

    if valid_pixels == 0:
        raise ValueError("Slope raster contains zero valid data pixels.")

    # 4. Compute Wu-Waldron root cohesion scalar
    root_res = calculate_root_cohesion(root, base_soil_cohesion_kpa=soil.c_prime_kpa)
    delta_c_kpa = root_res.delta_c_kpa

    # 5. Compute raster arrays
    # A. Baseline FS
    fs_baseline_arr, _ = calculate_infinite_slope_array(
        slope_deg_arr=slope_arr,
        soil=soil,
        valid_mask=valid_mask,
    )

    # B. Root-reinforced FS
    fs_reinf_arr = calculate_reinforced_slope_array(
        slope_deg_arr=slope_arr,
        soil=soil,
        delta_c_kpa=delta_c_kpa,
        valid_mask=valid_mask,
    )

    # C. Delta FS
    delta_fs_arr = np.full_like(slope_arr, -9999.0, dtype=np.float32)
    calc_mask = valid_mask & (slope_arr >= 0.1) & (slope_arr < 90.0)
    delta_fs_arr[calc_mask] = (fs_reinf_arr[calc_mask] - fs_baseline_arr[calc_mask]).astype(np.float32)

    # D. Required additional root cohesion
    req_cohesion_arr = calculate_required_cohesion_array(
        slope_deg_arr=slope_arr,
        soil=soil,
        fs_target=fs_target,
        valid_mask=valid_mask,
    )

    # E. Required RAR
    req_rar_arr = np.full_like(slope_arr, -9999.0, dtype=np.float32)
    tr_kpa = root.tensile_stress_kpa
    k = root.k_factor
    if tr_kpa > 0.0 and k > 0.0:
        req_rar_arr[calc_mask] = (req_cohesion_arr[calc_mask] / (k * tr_kpa)).astype(np.float32)

    # F. Required tree density (only if valid calibration is provided)
    req_density_arr: Optional[np.ndarray] = None
    cal_applied = False
    if calibration is not None:
        is_cal_valid, cal_msgs = validate_tree_density_calibration(calibration)
        if is_cal_valid:
            cal_applied = True
            req_density_arr = np.full_like(slope_arr, -9999.0, dtype=np.float32)
            dens_vals = calibration.reference_stems_per_ha * (
                req_rar_arr[calc_mask] / calibration.rar_at_reference_density
            )
            req_density_arr[calc_mask] = dens_vals.astype(np.float32)

    # 6. Save output rasters to GEOTECHNICAL_DIR and ARTIFACTS_DIR
    GEOTECHNICAL_DIR.mkdir(parents=True, exist_ok=True)
    settings.ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    run_id = uuid.uuid4().hex[:8]
    raster_filenames = {
        "fs_baseline": f"geotech_fs_baseline_{run_id}.tif",
        "fs_reinforced": f"geotech_fs_reinforced_{run_id}.tif",
        "fs_delta": f"geotech_fs_delta_{run_id}.tif",
        "required_cohesion": f"geotech_req_cohesion_{run_id}.tif",
        "required_rar": f"geotech_req_rar_{run_id}.tif",
    }
    if cal_applied:
        raster_filenames["required_tree_density"] = f"geotech_req_density_{run_id}.tif"

    # Write each GeoTIFF
    layers_to_write = [
        ("fs_baseline", fs_baseline_arr),
        ("fs_reinforced", fs_reinf_arr),
        ("fs_delta", delta_fs_arr),
        ("required_cohesion", req_cohesion_arr),
        ("required_rar", req_rar_arr),
    ]
    if cal_applied and req_density_arr is not None:
        layers_to_write.append(("required_tree_density", req_density_arr))

    written_paths = {}
    for key, arr in layers_to_write:
        art_path = settings.ARTIFACTS_DIR / raster_filenames[key]
        write_geotiff(
            output_path=art_path,
            array=arr,
            bounds=metadata.bounds,
            pixel_size_x=metadata.pixel_size_x,
            pixel_size_y=metadata.pixel_size_y,
            nodata_value=-9999.0,
            crs_str=metadata.crs or "EPSG:4326 (WGS 84)",
        )
        # Copy canonical copy to processed/geotechnical
        canonical_path = GEOTECHNICAL_DIR / f"wayanad_{key}.tif"
        shutil.copy2(art_path, canonical_path)
        written_paths[key] = {
            "artifact_filename": raster_filenames[key],
            "canonical_path": str(canonical_path),
        }

    # 7. Generate Preview Image
    preview_filename = f"geotech_preview_{run_id}.png"
    art_preview = settings.ARTIFACTS_DIR / preview_filename
    generate_geotechnical_preview(
        slope_deg=slope_arr,
        fs_baseline=fs_baseline_arr,
        fs_reinforced=fs_reinf_arr,
        req_cohesion=req_cohesion_arr,
        valid_mask=valid_mask,
        output_png_path=art_preview,
        title_suffix=f"Wayanad {metadata.width}x{metadata.height}",
    )
    canonical_preview = GEOTECHNICAL_DIR / "wayanad_geotechnical_preview.png"
    shutil.copy2(art_preview, canonical_preview)

    # 8. Compute Summary Statistics on valid calculated slope pixels
    base_vals = fs_baseline_arr[calc_mask]
    reinf_vals = fs_reinf_arr[calc_mask]
    delta_vals = delta_fs_arr[calc_mask]
    req_c_vals = req_cohesion_arr[calc_mask]

    calc_count = int(np.sum(calc_mask))
    flat_count = int(np.sum(valid_mask & (slope_arr < 0.1)))

    # Attainment counts
    unstable_base_count = int(np.sum(base_vals < 1.0))
    subtarget_base_count = int(np.sum(base_vals < fs_target))
    target_reached_count = int(np.sum(reinf_vals >= fs_target))
    reinf_pct = round(100.0 * target_reached_count / max(1, calc_count), 2)

    density_stats = None
    if cal_applied and req_density_arr is not None:
        dens_vals = req_density_arr[calc_mask]
        density_stats = {
            "min_stems_per_ha": round(float(np.min(dens_vals)), 1),
            "max_stems_per_ha": round(float(np.max(dens_vals)), 1),
            "mean_stems_per_ha": round(float(np.mean(dens_vals)), 1),
            "median_stems_per_ha": round(float(np.median(dens_vals)), 1),
            "is_calibrated": True,
            "assumed_relationship": calibration.assumed_relationship if calibration else None,
        }

    summary = {
        "run_id": run_id,
        "source_raster": slope_path.name,
        "crs": metadata.crs,
        "bounds": metadata.bounds,
        "pixel_resolution_x": metadata.pixel_size_x,
        "pixel_resolution_y": metadata.pixel_size_y,
        "total_pixels": total_pixels,
        "valid_pixels": valid_pixels,
        "calculated_slope_pixels": calc_count,
        "flat_terrain_pixels": flat_count,
        "scenario_assumptions": {
            "is_illustrative_scenario": True,
            "scenario_type": "ILLUSTRATIVE_EXPLORATORY_BENCHMARK",
            "spatial_uniformity_disclosure": (
                "Spatially uniform parameter scenario applied across the study area. "
                "These values represent user-supplied exploratory geotechnical scenario inputs, "
                "NOT spatially interpolated borehole measurements, field observations, or local soil surveys."
            ),
            "calibration_disclosure": (
                "Tree density estimates assume an unvalidated linear scaling benchmark (RAR ~ density). "
                "They are illustrative decision-support indicators, NOT certified planting prescriptions."
            ),
            "coordinate_reference_system": metadata.crs or "EPSG:4326 (WGS 84)",
            "soil": {
                "c_prime_kpa": soil.c_prime_kpa,
                "gamma_kn_m3": soil.gamma_kn_m3,
                "z_m": soil.z_m,
                "phi_prime_deg": soil.phi_prime_deg,
                "u_kpa": soil.u_kpa,
                "pore_water_assumption": soil.pore_water_assumption,
            },
            "root": {
                "tensile_stress_input": root.tensile_stress_input,
                "tensile_stress_unit": root.tensile_stress_unit.value,
                "tensile_stress_kpa": root.tensile_stress_kpa,
                "root_area_ratio": root.root_area_ratio,
                "k_factor": root.k_factor,
                "species_label": root.species_label,
                "modeled_delta_c_kpa": delta_c_kpa,
            },
            "target": {
                "fs_target": fs_target,
                "benchmark_note": "Target 1.3 is an exploratory project benchmark, not a universal engineering criterion.",
            },
        },
        "statistics": {
            "slope_degrees": {
                "min": round(float(np.min(slope_arr[valid_mask])), 2) if valid_pixels > 0 else 0.0,
                "max": round(float(np.max(slope_arr[valid_mask])), 2) if valid_pixels > 0 else 0.0,
                "mean": round(float(np.mean(slope_arr[valid_mask])), 2) if valid_pixels > 0 else 0.0,
                "median": round(float(np.median(slope_arr[valid_mask])), 2) if valid_pixels > 0 else 0.0,
                "mean_calculated_slope": round(float(np.mean(slope_arr[calc_mask])), 2) if calc_count > 0 else 0.0,
                "flat_pixels_below_0_1_deg": flat_count,
            },
            "baseline_fs": {
                "min": round(float(np.min(base_vals)), 3) if calc_count > 0 else 0.0,
                "max": round(float(np.max(base_vals)), 3) if calc_count > 0 else 0.0,
                "mean": round(float(np.mean(base_vals)), 3) if calc_count > 0 else 0.0,
                "median": round(float(np.median(base_vals)), 3) if calc_count > 0 else 0.0,
                "unstable_pixels_below_1": unstable_base_count,
                "subtarget_pixels_below_target": subtarget_base_count,
            },
            "reinforced_fs": {
                "min": round(float(np.min(reinf_vals)), 3) if calc_count > 0 else 0.0,
                "max": round(float(np.max(reinf_vals)), 3) if calc_count > 0 else 0.0,
                "mean": round(float(np.mean(reinf_vals)), 3) if calc_count > 0 else 0.0,
                "median": round(float(np.median(reinf_vals)), 3) if calc_count > 0 else 0.0,
                "pixels_reaching_target": target_reached_count,
                "percentage_reaching_target": reinf_pct,
            },
            "delta_fs": {
                "min": round(float(np.min(delta_vals)), 3) if calc_count > 0 else 0.0,
                "max": round(float(np.max(delta_vals)), 3) if calc_count > 0 else 0.0,
                "mean": round(float(np.mean(delta_vals)), 3) if calc_count > 0 else 0.0,
            },
            "required_cohesion_kpa": {
                "min": round(float(np.min(req_c_vals)), 3) if calc_count > 0 else 0.0,
                "max": round(float(np.max(req_c_vals)), 3) if calc_count > 0 else 0.0,
                "mean": round(float(np.mean(req_c_vals)), 3) if calc_count > 0 else 0.0,
                "pixels_needing_reinforcement": int(np.sum(req_c_vals > 0.0)),
            },
            "tree_density": density_stats,
        },
        "artifacts": {
            "preview_image": preview_filename,
            "rasters": {k: v["artifact_filename"] for k, v in written_paths.items()},
        },
        "warnings": [
            "Factor of Safety is a mechanistic limit-equilibrium index, NOT an empirical landslide probability.",
            "Do not infer root tensile strength or RAR from NDVI.",
            "Infinite-slope formulation assumes shallow translational planar shear without lateral boundary resistance.",
            "Results are exploratory decision-support indicators and do not replace certified on-site geotechnical engineering.",
        ],
    }

    # Save summary JSON
    summary_filename = f"geotech_summary_{run_id}.json"
    summary_path = settings.ARTIFACTS_DIR / summary_filename
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    canonical_summary = GEOTECHNICAL_DIR / "wayanad_geotechnical_summary.json"
    shutil.copy2(summary_path, canonical_summary)
    summary["artifacts"]["summary_json"] = summary_filename

    return summary
