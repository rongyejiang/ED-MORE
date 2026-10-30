# Five-year numerical comparison with Example04

## Reproducing the published example

The unchanged local default and supplied-calibrated five-year runs reproduce the five published
mean values at their printed precision. For the calibrated run: GPP 8.75426 versus 8.75 μmol m⁻² s⁻¹;
LE 66.87044 versus 66.9 W m⁻²; NEE −2.99950 versus −3.00 μmol m⁻² s⁻¹; Rnet 139.25924 versus
139.3 W m⁻². Daytime H is 174.82057 versus 174.8 W m⁻², using the provisional SWdown > 10 W m⁻²
mask; the exact published daytime mask was not available. Solver warnings remain documented.
This checks rounded means, not every trajectory, calibration score or observation.

Reference: [the frozen Example04 README](https://github.com/EDmodel/ED-MORE/blob/f49d50c89f01e5747eee2950a9cbe1d8e08371a5/examples/example04_column_biophysics/README.md).
The exact local values and measured-hour counts are in results.json.

## Changes after modifying the boundary conditions

The following table uses all days of the same five-year tower-forcing window, with canopy water ON.
Annual rates are integral / 5; H, Rnet and soil water are time means. These are not the measured-hour
means used above. In particular, LE 66.9 must not be converted into an annual ET baseline.

| Metric | Unit | Original Example04, local | PF01, 41 m | Current PF01, 50 m | Current vs original |
|---|---|---:|---:|---:|---:|
| ET | mm yr-1 | 896.008 | 857.941 | 861.456 | -3.86% |
| GPP | kg C m-2 yr-1 | 3.208 | 3.112 | 3.095 | -3.52% |
| H | W m-2 | 74.846 | 77.280 | 76.491 | +2.20% |
| Rnet | W m-2 | 137.281 | 137.163 | 136.646 | -0.46% |
| surface_runoff | mm yr-1 | 61.104 | 309.553 | 309.266 | +406.13% |
| drainage | mm yr-1 | 1052.567 | 870.110 | 867.289 | -17.60% |
| soil_water | mm | 879.080 | 774.258 | 774.135 | -11.94% |


The PF01 41 m column is the earlier controlled soil-scenario comparison. The current 50 m column
also changes the idealized reference height, forcing endpoint recycling and execution settings;
the original-to-current difference cannot be attributed exclusively to soil. Neither comparison
refits photosynthesis, stomata or aerodynamic parameters. The original supplied calibration is
retained; the current modified run has not been newly validated against tower observations.

ET and GPP change by a few percent, while surface runoff and drainage change much more. Agreement
in total ET alone therefore does not establish agreement in water partitioning or ecological validity.
