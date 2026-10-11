# TerraShield AI — Geotechnical Intelligence Engine: Mathematical Formulation & Model Specification

**Phase 3 of 5: Geotechnical Intelligence Engine**  
**Document Revision:** 1.0 (Phase 3 Core Implementation)  
**Author:** TerraShield AI Geotechnical Engineering & Numerical Methods Team  

---

## 1. Executive Summary & Purpose

The **Geotechnical Intelligence Engine** (Phase 3) extends the TerraShield AI spatial decision-support system from physical terrain descriptors (elevation, slope gradient, aspect) into mechanistically grounded limit-equilibrium slope stability modeling. 

This engine implements:
1. **Classical Infinite Slope Limit Equilibrium Formulation** for shallow translational planar failures.
2. **Wu-Waldron Vegetative Root Reinforcement Formulation** for calculating additional shear strength ($\Delta C$) contributed by root systems.
3. **Target Factor of Safety Solver** determining the analytical root cohesion required to attain a specified stability benchmark ($FS_{target} = 1.3$).
4. **Calibrated Tree-Density Linear Estimator** translating required root area ratio into stem planting density strictly when supported by empirical field calibration.
5. **Deterministic Parameter Sensitivity Analysis** evaluating stability response across parameter bounds.
6. **Real-Terrain Raster Processing Pipeline** executing per-pixel stability evaluations across the verified Wayanad, Kerala terrain slope product (`data/processed/real/wayanad_slope.tif`).

---

## 2. Governing Equations

### 2.1 Baseline Infinite Slope Formulation ($FS_0$)

For a planar, translational failure surface parallel to the ground surface at depth $z$, the baseline Factor of Safety ($FS_0$) is defined by the ratio of available resisting shear strength ($\tau_f$) to downslope driving shear stress ($\tau$):

$$FS_0 = \frac{\tau_f}{\tau} = \frac{c' + (\sigma_n - u) \tan(\phi')}{\tau}$$

Expressed explicitly in terms of slope geometry and soil bulk properties:

$$FS_0 = \frac{c' + \left(\gamma \cdot z \cdot \cos^2(\beta) - u\right) \tan(\phi')}{\gamma \cdot z \cdot \sin(\beta) \cos(\beta)}$$

Where:
- $\beta$: Hillslope angle with respect to the horizontal plane [$\text{rad}$ internally, $^\circ$ externally].
- $z$: Vertical depth to the assumed planar failure surface [$\text{m}$].
- $\gamma$: Total soil unit weight [$\text{kN/m}^3$].
- $c'$: Effective soil cohesion [$\text{kPa} = \text{kN/m}^2$].
- $\phi'$: Effective internal friction angle [$\text{rad}$ internally, $^\circ$ externally].
- $u$: Pore-water pressure acting along the failure plane [$\text{kPa}$].
- $\sigma_n$: Total normal stress acting perpendicular to the failure plane: $\sigma_n = \gamma \cdot z \cdot \cos^2(\beta)$ [$\text{kPa}$].
- $\sigma'_n$: Effective normal stress: $\sigma'_n = \sigma_n - u$ [$\text{kPa}$].
- $\tau$: Gravitational driving shear stress: $\tau = \gamma \cdot z \cdot \sin(\beta) \cos(\beta)$ [$\text{kPa}$].

#### Limiting Dry Cohesionless Case
When cohesion is zero ($c' = 0$) and pore pressure is negligible ($u = 0$):
$$FS_0 = \frac{\gamma \cdot z \cdot \cos^2(\beta) \tan(\phi')}{\gamma \cdot z \cdot \sin(\beta) \cos(\beta)} = \frac{\cos(\beta) \tan(\phi')}{\sin(\beta)} = \frac{\tan(\phi')}{\tan(\beta)}$$
This canonical limiting case is verified in automated unit test `test_2_dry_cohesionless_limiting_case`.

---

### 2.2 Wu-Waldron Vegetative Root Reinforcement Formulation ($\Delta C$)

Vegetative root systems crossing the potential planar slip surface provide supplemental tensile resistance, modeled as an apparent root cohesion $\Delta C$ according to the simplified Wu-Waldron formulation (Wu et al. 1979; Waldron 1977):

$$\Delta C = K \cdot T_r \cdot RAR$$

Where:
- $\Delta C$: Modeled additional root cohesion [$\text{kPa}$].
- $K$: Empirical root reinforcement coefficient (default $1.2$), representing average root orientation and tensile mobilization.
- $T_r$: Average tensile strength/stress of the root fibers [$\text{kPa}$]. If input in $\text{MPa}$, the engine automatically applies $1\text{ MPa} = 1,000\text{ kPa}$.
- $RAR$: Root Area Ratio, the dimensionless fraction of root cross-sectional area to total soil shear plane area ($A_r / A$).

#### Total Modeled Cohesion
$$c_{total} = c' + \Delta C$$

---

### 2.3 Factor of Safety with Vegetative Root Reinforcement ($FS_{root}$)

Substituting total cohesion into the infinite slope formulation:

$$FS_{root} = \frac{c' + \Delta C + \left(\gamma \cdot z \cdot \cos^2(\beta) - u\right) \tan(\phi')}{\gamma \cdot z \cdot \sin(\beta) \cos(\beta)}$$

The modeled stability increment is:
$$\Delta FS = FS_{root} - FS_0$$

> **Critical Scientific Caveat:** $\Delta FS$ represents an increase in the mechanistic limit-equilibrium margin of safety. It is **NOT** a percentage reduction in landslide probability.

---

### 2.4 Analytical Target Cohesion Solver

To determine the minimum additional root cohesion required to attain a target Factor of Safety benchmark ($FS_{target}$, default $1.3$):

$$\Delta C_{required} = \max\left(0, \; FS_{target} \cdot \tau - c' - \sigma'_n \tan(\phi')\right)$$

Where:
- $\tau = \gamma \cdot z \cdot \sin(\beta) \cos(\beta)$
- $\sigma'_n = \gamma \cdot z \cdot \cos^2(\beta) - u$

If $FS_0 \ge FS_{target}$, $\Delta C_{required} = 0.0$ (no additional root cohesion needed).

#### Re-Substitution Verification
For every analytical solution where $\Delta C_{required} > 0$, the engine substitutes $(c' + \Delta C_{required})$ back into the infinite slope equation:
$$FS_{verified} = \frac{c' + \Delta C_{required} + \sigma'_n \tan(\phi')}{\tau}$$
The solution is accepted only if $|FS_{verified} - FS_{target}| \le 10^{-4}$.

---

### 2.5 Calibrated Tree-Density Linear Estimator

The Root Area Ratio required to achieve $\Delta C_{required}$ is:
$$RAR_{required} = \frac{\Delta C_{required}}{K \cdot T_r}$$

Converting $RAR_{required}$ into stem planting density (stems/hectare) requires explicit field calibration. When empirical reference data are provided ($stems_{ref}$ and $RAR_{ref}$):

$$stems\_per\_ha_{required} = stems_{ref} \cdot \left(\frac{RAR_{required}}{RAR_{ref}}\right)$$

#### Strict Estimator Constraints:
1. **Calibration Required:** If reference parameters are missing, the engine reports $RAR_{required}$ and marks stem density as unavailable.
2. **Biological Feasibility:** If $stems\_per\_ha_{required} > max\_stems\_per\_ha$, the engine flags the scenario as biologically infeasible rather than extrapolating beyond carrying capacity.
3. **No Automatic Prescriptions:** The engine does not prescribe tree species or planting patterns without verified site-specific silvicultural studies.

---

## 3. Parameter Units & Conventions

| Parameter | Symbol | Unit (Interface) | Unit (Internal) | Physical Bounds |
|---|---|---|---|---|
| Slope Angle | $\beta$ | Degrees ($^\circ$) | Radians ($\text{rad}$) | $0.0^\circ \le \beta < 90.0^\circ$ |
| Soil Effective Cohesion | $c'$ | $\text{kPa}$ | $\text{kPa}$ | $c' \ge 0.0$ |
| Soil Unit Weight | $\gamma$ | $\text{kN/m}^3$ | $\text{kN/m}^3$ | $5.0 \le \gamma \le 30.0$ |
| Depth to Slip Plane | $z$ | $\text{m}$ | $\text{m}$ | $0.2 \le z \le 20.0$ |
| Friction Angle | $\phi'$ | Degrees ($^\circ$) | Radians ($\text{rad}$) | $0.0^\circ \le \phi' < 90.0^\circ$ |
| Pore-Water Pressure | $u$ | $\text{kPa}$ | $\text{kPa}$ | $u \ge 0.0$ |
| Root Tensile Strength | $T_r$ | $\text{MPa}$ or $\text{kPa}$ | $\text{kPa}$ | $T_r > 0.0$ |
| Root Area Ratio | $RAR$ | Fraction | Dimensionless | $0.0 \le RAR \le 1.0$ |
| Reinforcement Factor | $K$ | Dimensionless | Dimensionless | $K > 0.0$ (Default 1.2) |
| Target Factor of Safety | $FS_{target}$| Dimensionless | Dimensionless | $> 0.0$ (Benchmark 1.3) |

### 3.1 Spatial Coordinate Reference System & Resolution
- **Spatial CRS:** `EPSG:4326 (WGS 84)` (Geographic Longitude / Latitude).
- **Spatial Bounds:** Longitude `76.00° E – 76.10° E`, Latitude `11.55° N – 11.65° N` (Wayanad, Kerala).
- **Pixel Scale:** $0.0002778^\circ \approx 30.29\text{ m}$ (East-West $\Delta x$) and $30.79\text{ m}$ (North-South $\Delta y$) at latitude $11.60^\circ\text{N}$.
- **Ellipsoidal Metric Gradients:** The pure-Python gradient solver evaluates spatial increments dynamically on the WGS 84 reference ellipsoid ($R_a = 6,378,137\text{ m}$, $f = 1/298.257223563$) without raster distortion or synthetic reprojection.
- **Projected System Distinction:** `EPSG:32643` (UTM Zone 43N) is designated as the recommended projected CRS for parcel boundary vectors in the pilot corridor, but all continuous raster products remain in native geographic EPSG:4326.

---

## 4. Numerical Edge Cases & Model Handling

1. **Flat Terrain ($\beta < 0.1^\circ$):**
   - The denominator $\tau = \gamma \cdot z \cdot \sin(\beta) \cos(\beta)$ approaches zero.
   - Returning an enormous arbitrary number (e.g., $FS = 9999$) is physically misleading.
   - The engine explicitly marks the cell as undefined: `status="FLAT_TERRAIN"` with NoData fill ($-9999.0$).

2. **Excess Pore Pressure ($\sigma'_n = \sigma_n - u \le 0$):**
   - Occurs during severe positive pore-water pressurization or artesian conditions.
   - Effective frictional shear strength cannot mobilize: $\tau_{frictional} = 0$.
   - The engine caps available frictional strength at zero, evaluates residual cohesive capacity ($c'$ or $c' + \Delta C$), and issues warning: `NON_POSITIVE_EFFECTIVE_STRESS`.

3. **NoData / Invalid Raster Cells:**
   - Pre-existing NoData pixels in the slope GeoTIFF are strictly preserved across all output rasters with value $-9999.0$.

---

## 5. Model Assumptions and Limitations

- **Translational Planar Slip Assumption:** The infinite slope model assumes failure occurs along a planar surface of infinite length and width parallel to the slope. It does not account for rotational slip arcs, three-dimensional toe support, or lateral boundary shear resistance.
- **Homogeneity Assumption:** Soil unit weight, cohesion, and friction angle are modeled as uniform across depth $z$.
- **Wu-Waldron Upper Bound:** The Wu-Waldron formulation assumes simultaneous tensile failure of all roots perpendicular to the shear plane. In field conditions, progressive pullout, variable root orientation, and root decay typically reduce mobilized resistance below this theoretical maximum.
- **Factor of Safety vs. Probability:** Factor of Safety is a deterministic ratio of resisting to driving forces. It must never be presented as an empirical percentage probability of landslide failure.

---

## 6. Authoritative Scientific References

1. **US Army Corps of Engineers (USACE)** (2003). *Slope Stability*, Engineer Manual EM 1110-2-1902.  
   Official URL: [https://www.publications.usace.army.mil/Portals/76/Publications/EngineerManuals/EM_1110-2-1902.pdf](https://www.publications.usace.army.mil/Portals/76/Publications/EngineerManuals/EM_1110-2-1902.pdf)  
   *Relevance:* Authoritative guidance on limit-equilibrium slope stability formulations, unit weight conventions, effective stress definitions, and target factors of safety for engineered hillslopes.

2. **Wu, T.H., McKinnell, W.P., and Swanston, D.N.** (1979). *Strength of tree roots and landslides on Prince of Wales Island, Alaska.* Canadian Geotechnical Journal, 16(1), 19–33.  
   DOI: [10.1139/t79-003](https://doi.org/10.1139/t79-003)  
   *Relevance:* Foundational formulation of vegetative root tensile reinforcement $\Delta C = K \cdot T_r \cdot RAR$ and root area ratio quantification.

3. **Waldron, L.J.** (1977). *The shear resistance of root-permeated homogeneous and stratified soil.* Soil Science Society of America Journal, 41(5), 843–849.  
   DOI: [10.2136/sssaj1977.03615995004100050005x](https://doi.org/10.2136/sssaj1977.03615995004100050005x)  
   *Relevance:* Mechanical model deriving shear resistance enhancement from tensile root fibers crossing a direct shear plane in cohesive soils.
