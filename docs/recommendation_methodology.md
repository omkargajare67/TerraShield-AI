# TerraShield AI — Phase 4 Spatial Recommendation Methodology

## 1. Overview and Core Philosophy

Phase 4 of TerraShield AI implements an explainable **Spatial Recommendation & Prioritization Engine** designed to evaluate, filter, and rank candidate planting parcels across the Western Ghats pilot corridor.

Rather than treating prioritization as a black-box machine-learning prediction, the engine uses a transparent, rule-based multi-criteria spatial decision-support model. It integrates:
1. **Measured Topography:** High-resolution elevation, slope, and aspect derived from NASA SRTM NASADEM Global 1 Arc-Second V001 (`NASADEM_HGT_n11e076`, 30m resolution).
2. **Satellite Vegetation Index:** 10m Sentinel-2 BOA NDVI reflectance.
3. **Geotechnical Limit-Equilibrium Stability:** Baseline Factor of Safety ($FS_{\text{base}}$), root-reinforced Factor of Safety ($FS_{\text{reinf}}$), and modeled stability improvement ($\Delta FS$) from Phase 3.
4. **Statutory & Environmental Constraints:** Strict physical and cadastral exclusion rules.

---

## 2. Coordinate System Handling & Candidate Parcel Generation

### 2.1 Spatial Reference & Ellipsoidal Curvature
The native input rasters are georeferenced in **EPSG:4326 (WGS 84)**. To prevent distortion when operating on metric grid scales (e.g., 300-meter candidate cells), spatial increments are converted using local WGS 84 ellipsoidal radii of curvature:

$$M(\phi) = \frac{a(1 - e^2)}{(1 - e^2 \sin^2 \phi)^{3/2}} \quad \text{(Meridian radius / North-South)}$$
$$N(\phi) = \frac{a}{\sqrt{1 - e^2 \sin^2 \phi}} \quad \text{(Prime vertical radius / East-West)}$$

Where:
- $a = 6,378,137.0\text{ m}$ (WGS 84 semi-major axis)
- $f = 1 / 298.257223563$ (flattening)
- $e^2 = 2f - f^2 \approx 0.00669438$ (first eccentricity squared)
- $\phi$ is the latitude in radians.

Angular increments for a ground metric resolution $d_{\text{meters}}$ are computed as:
$$\Delta \lambda = \frac{d_{\text{meters}}}{N(\phi) \cos \phi} \cdot \frac{180^\circ}{\pi}, \quad \Delta \phi = \frac{d_{\text{meters}}}{M(\phi)} \cdot \frac{180^\circ}{\pi}$$

### 2.2 Geodesic Area Calculation
Parcel area is **never computed by multiplying degree differences as meters**. Instead, polygon rings are projected to a localized ellipsoidal Cartesian metric space centered on the polygon centroid $(\lambda_0, \phi_0)$:
$$x_i = (\lambda_i - \lambda_0) \cdot \frac{\pi}{180} \cdot N(\phi_0) \cos \phi_0$$
$$y_i = (\phi_i - \phi_0) \cdot \frac{\pi}{180} \cdot M(\phi_0)$$

The metric polygon surface area is then obtained via the Shoelace formula and converted to hectares ($1\text{ ha} = 10,000\text{ m}^2$):
$$A_{\text{ha}} = \frac{1}{20000} \left| \sum_{i=1}^{n-1} (x_i y_{i+1} - x_{i+1} y_i) \right|$$

---

## 3. Zonal Statistics Methodology

Because input rasters possess distinct native spatial resolutions:
- **DEM, Slope, Aspect, Geotechnical outputs:** $360 \times 360$ pixels ($\sim 30.8\text{ m}$ resolution)
- **Sentinel-2 NDVI:** $1099 \times 1099$ pixels ($\sim 10.1\text{ m}$ resolution)

The engine avoids lossy raster resampling. Instead, each candidate parcel boundary $[ \lambda_{\min}, \phi_{\min}, \lambda_{\max}, \phi_{\max} ]$ queries each raster independently via native array slicing.

### Computed Parcel Metrics:
1. **Topography:** Mean slope ($\bar{\theta}$), median slope, max slope, steep-slope fraction ($>25^\circ$), mean elevation ($\bar{z}$).
2. **Geotechnical (Phase 3 inputs):**
   - Mean baseline Factor of Safety ($\overline{FS}_{\text{base}}$)
   - Fraction of parcel failing project benchmark ($FS < 1.3$)
   - Fraction acutely unstable ($FS < 1.0$)
   - Mean modeled Factor of Safety improvement ($\overline{\Delta FS}$)
   - Mean required root cohesion ($\bar{c}_{r,\text{req}}$ in kPa)
   - Calibrated required stem density ($\bar{\rho}_{\text{stems}}$ in stems/ha)
3. **Vegetation:**
   - Sentinel-2 mean NDVI ($\overline{NDVI}$)
   - Dense canopy proxy fraction ($NDVI > 0.65$)
4. **Data Coverage:**
   - Terrain data coverage percentage
   - NDVI coverage percentage

---

## 4. Eligibility Engine & Exclusion Hierarchy

Each parcel is evaluated through strict deterministic criteria:

| Status Code | Trigger Condition | Consequence |
|---|---|---|
| `INSUFFICIENT_DATA` | Terrain valid coverage $< 80\%$ | Disqualified from ranking; area set to 0.0 ha |
| `EXCLUDED` | Hillslope gradient $> 45^\circ$ or cliffs | Disqualified (too steep for safe bio-reinforcement) |
| `EXCLUDED` | Spatial intersection with statutory reserve | Disqualified (protected ecological zone) |
| `EXCLUDED` | Spatial intersection with user exclusion zone | Disqualified |
| `EXCLUDED` | Dense canopy proxy leaves $< 0.25\text{ ha}$ | Disqualified (already densely vegetated) |
| `ELIGIBLE_UNDER_AVAILABLE_CONSTRAINTS` | Satisfies all active constraints | Qualified for multi-criteria ranking |

> **Administrative Disclosure:** If no official legal reserve boundary is loaded, the engine tags the clearance note as `UNVERIFIED: Official cadastral reserve dataset unavailable`. It never claims confirmed planting clearance merely because no exclusion polygon was present.

---

## 5. Explainable Multi-Criteria Priority Scoring

Only eligible parcels receive priority scores and ordinal ranks. Disqualified parcels (`EXCLUDED` or `INSUFFICIENT_DATA`) are strictly prevented from entering the ranking.

### 5.1 Component Normalization (0.0 to 1.0)
Scoring normalization is governed by `NormalizationConfig`:
- `fs_target`: Target Factor of Safety benchmark (default $1.3$).
- `critical_fs`: Critical limit-equilibrium failure FS threshold (default $0.7$).
- `max_delta_fs_ref`: Configurable normalization reference divisor for modeled stability improvement (default $15.0$). **This is a mathematical normalization scale reference, NOT a validated civil or geotechnical engineering threshold.**
- `max_area_ref_ha`: Plantable parcel area divisor (default $15.0\text{ ha}$).

1. **Geotechnical Need Score ($S_{\text{need}}$):**
   $$S_{\text{need}} = 0.5 \cdot \max\left(0, \min\left(1, \frac{FS_{\text{target}} - \overline{FS}_{\text{base}}}{FS_{\text{target}} - FS_{\text{critical}}}\right)\right) + 0.5 \cdot \text{Fraction}_{FS < FS_{\text{target}}}$$
   Parcels with acute baseline instability receive the highest score. If geotechnical layers are absent, evaluated according to the active `MissingDataPolicy`.
2. **Stability Improvement Score ($S_{\text{gain}}$):**
   $$S_{\text{gain}} = \min\left(1.0, \frac{\overline{\Delta FS}}{\text{max\_delta\_fs\_ref}}\right)$$
   Reflects modeled gain in shear resistance from root cohesion relative to the configured run-wide normalization reference.
3. **Plantable Acreage Capacity ($S_{\text{area}}$):**
   $$S_{\text{area}} = \min\left(1.0, \frac{A_{\text{plantable}}}{\text{max\_area\_ref\_ha}}\right)$$
4. **Input Data Completeness ($S_{\text{conf}}$):**
   Evaluates completeness across expected observational raster inputs (50% terrain from DEM, 50% vegetation from Sentinel-2 NDVI):
   - **Both present:** $S_{\text{conf}} = 0.5 \cdot \frac{\text{cov}_{\text{terrain}}}{100} + 0.5 \cdot \frac{\text{cov}_{\text{ndvi}}}{100}$, with `input_coverage_complete = True`.
   - **NDVI missing:** $S_{\text{conf}} = 0.5 \cdot \frac{\text{cov}_{\text{terrain}}}{100}$ (at 100% terrain coverage, $S_{\text{conf}} = 0.50$, NOT 1.0), with `input_coverage_complete = False` and `"ndvi_coverage"` flagged in `missing_components`.
   - **NDVI calculated 0.0%:** If the NDVI raster is present and sampled with 0.0% valid pixels, $S_{\text{conf}} = 0.50$, but `input_coverage_complete = True` and `"ndvi_coverage"` is NOT flagged as missing, preserving the critical distinction between calculated zero coverage and missing data.

### 5.2 Empirical Audit of the 15.0 Divisor ($S_{\text{gain}}$)
An empirical audit across the Wayanad corridor pilot study area established:
- **Raw $\Delta FS$ Raster (128,879 valid pixels):**
  - Minimum: $1.333$
  - 25th percentile: $3.050$
  - Median: $4.485$
  - 75th percentile: $7.651$
  - 95th percentile: $20.218$
  - Maximum: $40.981$
  - Pixels exceeding $15.0$: $8.24\%$
- **Candidate 300m Parcels ($N = 1,369$):**
  - Minimum mean $\Delta FS$: $1.537$
  - 25th percentile: $4.650$
  - Median mean $\Delta FS$: $6.145$
  - 75th percentile: $8.375$
  - Maximum mean $\Delta FS$: $24.877$
  - Mean: $6.886$
  - Parcels exceeding $15.0$: $42$ ($3.07\%$)

**Audit Finding:** The reference divisor of $15.0$ maps the median parcel to $S_{\text{gain}} \approx 0.410$ and provides linear discriminative resolution across $96.93\%$ of the parcel population without artificial clustering, while safely clamping extreme high-gradient cliff outliers ($>15.0$). It prevents stability gain from overwhelming other criteria while ensuring meaningful contribution. Through `NormalizationConfig`, this divisor is configurable per analysis run to ensure deterministic, run-wide consistency without per-parcel bias.

### 5.3 Missing Data Policy Handling
When environmental or geotechnical layers are unavailable across a run, the system strictly forbids silent zero-defaulting. The active policy is governed by `MissingDataPolicy`:
1. `RENORMALIZE_AVAILABLE` (Default): Component scores for missing layers are marked `None` (not $0.0$). The active weights for available components ($w_{\text{active}}$) are dynamically re-normalized to sum to $1.0$. Missing components are explicitly itemized in API responses and export manifests.
2. `ZERO_FILL`: Unavailable metrics are assigned a real component score of $0.0$, penalizing parcels for incomplete data while preserving configured weight proportions.
3. `BLOCK_UNAVAILABLE`: Any parcel lacking full geotechnical or vegetation layers is marked unrankable (`INSUFFICIENT_DATA`), preventing inclusion in the eligible ranking.

### 5.4 Composite Priority Score Index
With user-configured or re-normalized weights summing to $1.0$:
$$\text{Priority Index} = 100 \times \sum_{i \in \text{available}} w_{i,\text{active}} S_i$$

### 5.5 Discriminative Ranking & Non-Discriminative Suppression
Parcels are evaluated for component discriminability across the run:
- **Differentiating Drivers:** Active components with non-zero variance across candidate parcels ($S_{\text{gain}}$ and $S_{\text{need}}$ in standard runs) drive the ordinal rankings and are reported in parcel explanation summaries.
- **Baseline Aggregate Contributors:** Uniform components ($S_{\text{area}} = 0.600$ across regular 9.0 ha cells, $S_{\text{conf}} = 1.000$ across complete data) contribute baseline points to the composite score index but do not differentiate candidate parcels.
- **Non-Discriminative Suppression:** If active components provide zero variance across candidate parcels (e.g. missing geotechnical data under `RENORMALIZE_AVAILABLE` where area and confidence are identical for all parcels), the engine **suppresses arbitrary tie-broken ranking**. It flags the run as `is_discriminative = False`, sets `rank = None` for all candidate parcels, and returns an explicit warning (`differentiation_warning`), preventing false precision from being presented to decision-makers.
Parcels are sorted strictly by:
1. `priority_score_index` (Descending)
2. `stability_gain_score` (Descending)
3. `plantable_area_ha` (Descending)
4. `parcel_id` (Ascending string comparison)

---

## 6. Leverage Metric Scientific Safeguard

The original TerraShield AI concept defines leverage as:
$$L = \frac{\Delta R}{N}$$
Where $\Delta R$ is empirical landslide risk reduction and $N$ is tree count.

### Mandatory Scientific Safeguards:
1. **$\Delta FS \neq \Delta R$:** Modeled change in Factor of Safety is a mechanistic limit-equilibrium index, not an empirical hazard probability curve. The engine **never substitutes $\Delta FS$ for $\Delta R$**.
2. **Modeled Stability Gain per Stem:** When calibrated stem density exists from Phase 3, the engine computes:
   $$\text{Stability Gain per Stem} = \frac{\overline{\Delta FS}}{N_{\text{stems}}}$$
   This is explicitly labelled as a **modeled mechanical index per stem**, not disaster risk reduction.
3. **Uncalibrated Status:** When stem density calibration is absent, the metric is marked `UNAVAILABLE: Calibrated root-density or stem-density benchmark not available`.

---

## 7. Native Species Interface Integrity

The botanical recommendation interface (`SpeciesDatabase`) enforces strict scientific standards:
- It **refuses to fabricate species recommendations** or invent root tensile parameters.
- When unpopulated, it returns status `PENDING_CURATED_BOTANICAL_DATA`.
- When supplied with peer-reviewed regional botanical records (e.g. KFRI/BSI profiles), it filters candidates strictly by elevation suitability, slope tolerance, and root architecture.
