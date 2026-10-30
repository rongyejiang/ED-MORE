# Settings and data provenance

These settings describe the completed runs, not settings chosen for a new benchmark.
Source and configuration hashes are in [provenance.json](provenance.json).

## Common constraints

| Quantity | Setting and source |
|---|---|
| Period | 2012-08-01 00:00 to 2017-08-01 00:00 UTC, right endpoint excluded |
| Tower meteorology | Detto, [BCI eddy covariance data](https://zenodo.org/records/6456527), as prepared by frozen Example04; acknowledge CTFS-ForestGEO |
| ERA5-Land | [ECMWF ARCO time series](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land-timeseries), grid 9.2°N, 79.8°W; de-accumulated precipitation and radiation, no second de-accumulation |
| Rain-only replacement | Tower variables retained, rain replaced by ERA5-Land and scaled to the same five-year total; no monthly or annual matching |
| Input rainfall | Tower 2042.01242 mm yr⁻¹, 709.0 wet hours yr⁻¹; rain-only 2042.01242, 2824.2 wet hours yr⁻¹; wet hour means strictly greater than 0.1 mm |
| Atmospheric boundary | Same values prescribed at 50 m above ground, local wind exposure; an idealization, not observed 50 m data or a physical height extrapolation |
| Census | [Condit et al., Dryad BCI census](https://doi.org/10.15146/5xcp-0d46), 2010 forest; native model reconstruction retained |
| Soil texture | PF01, 6–16 cm: sand 0.07, clay 0.645; [STRI soil survey](https://striresearch.si.edu/bci-soil-map/content/soils-of-bci/), Ava profile analytical table |
| Soil hydraulics | ED2 `SOIL_HYDRO_SCHEME=0`, copied into MORE's Campbell input; one uniform set through 2 m |
| Layer bottom depths | 0.05, 0.15, 0.30, 0.60, 1.00, 1.50, 2.00 m |
| Initial soil water | Prescribed theta 0.42, total 840 mm; a common experimental constraint |
| Initial soil temperature | Area/depth weighted mean target 298.65 K; this does not match the full temperature or enthalpy profile |
| CO2 | Same CMIP7 global annual series; common source checksum in provenance.json |
| Main time step | 900 s; native integrators and internal error control retained |

PF01 is a nearby single profile, not an established tower-footprint average. Its shallow texture
is extrapolated here as a controlled homogeneous scenario. The full 2 m hydraulic profile is not
measured. ED2's pedotransfer estimates are not observed hydraulic curves. No new curve or flux fit
was performed, and using this soil does not establish greater ecological realism than Example04.

The transferred MORE values are `theta_sat=0.4711949825286865`, `theta_res=0`,
`curve_par_a=-0.44983169436454773` m, `curve_par_n=13.205499649047852`, and
`ksat=8.393270718443091e-7` m s⁻¹. They come from the native ED2 scheme-0 calculation at
the fixed ED2 revision, not from tuning the ET response. Static native-curve checks found the
scheme-0 transfer consistent over the tested common operating domain above ED2's conductivity
floor. This does not equate thermal properties, numerical floors, boundaries or root uptake.

## Important retained differences

| Component | ED2 used here | ED-MORE used here |
|---|---|---|
| Engine | `125f814d` plus documented local corrections | `f49d50c`, gfortran dev |
| Physiology | `IPHYSIOL=2`, native parameters | Supplied calibrated Example04 PFT parameters, unchanged |
| Plant water | `PLANT_HYDRO_SCHEME=0`, `H2O_PLANT_LIM=2` | Native dynamic plant-water network |
| Vegetation energy | `IBRANCH_THERMO=1`; native leaf/wood treatment | Native leaf and wood energy states |
| Aerodynamics | `ICANTURB=2`, `ISFCLYRM=3` | Native scheme and supplied calibrated roughness |
| Vegetation | Native allometry (`IALLOM=3`), reconstruction and demographic rules | Native reconstruction, traits and demographic rules |
| Growth, mortality, recruitment | Enabled | Enabled |
| Soil heat | Native material laws, profile and lower boundary | Original Example04 thermal properties and fixed-temperature deep boundary |
| Time integration | Native RK4 (`INTEGRATION_SCHEME=1`) | ESDIRK2 and the native water solver |
| Threads | One per run | Two per primary run |
| Canopy-water OFF | Local diagnostic variant | Native `canopy_water_on=false` |

Equal main steps do not imply equal internal steps or truncation errors. Shared census source
and soil-carbon initialization conventions do not produce identical vegetation carbon pools,
cohorts, patches or thermal states. Native trait plasticity, radiation, interception capacity and
water distribution also differ. The result difference is therefore a configuration difference
containing structure, parameters, initialization and numerical effects; it is not an isolated
estimate of structural uncertainty.

MORE uses `recycle=false` for the main matrix, preserving actual endpoint forcing rather than
wrapping the final interpolation to the beginning of the forcing cycle. Tower and rain-only
forcing use half-hour begin-stamped intervals; full ERA5-Land uses hourly end-stamped intervals.
ED2's bridge accounts for those intervals for rain and shortwave. Equal forcing is established
at the input contract, not as a claim that every internal interpolated sample is identical.

## Local ED2 corrections and switch

Three corrections belong to the primary five-year executable: refreshing the daily output
table after state restructuring; copying the solver-success flag in `copy_solution`; and skipping
the unused meteorological look-ahead at the terminal integration boundary. The local OFF build
also disables interception, leaf/wood surface-water vapour exchange and their enthalpy terms.
The OFF interventions are not term-for-term equivalent between models.

Separate HISTORY corrections were used only for short-window sensitivity: restore the leaf/wood
resolvability flags without triggering a false state transition, and initialize an unused average
output placeholder on nonempty grids. The original five-year binaries and trajectories were not
changed. The failed original HISTORY smoke remains rejected; it was not relabelled successful.

The archive retains source diffs, configurations, build receipts and exact executable hashes.
They are referenced by checksum here, not redistributed as a portable ED2 patch/reproduction kit.
Neither full model simulation nor compilation was repeated to prepare this documentation branch.
