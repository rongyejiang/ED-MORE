# BCI: a local ED2–ED-MORE interception comparison

In these tested configurations, replacing tower rainfall with ERA5-Land rainfall scaled to the
same five-year total increases the ET response to enabling canopy water in both ED2 and ED-MORE.
The amplitudes differ. This supports the occurrence of the response in this ED2 configuration;
it does not establish a common cause, a universal model property, or a need for a new module.

This is a completed theoretical sensitivity experiment, not a calibrated intercomparison or field
validation. No parameters were refitted. No claim is made that either model is a reference truth.

## Runs and meaning of the comparison

Both models cover 2012-08-01 through 2017-07-31 (UTC; 1,826 days), with a 900 s main step.
The soil uses ED2 scheme-0 Campbell curves derived from PF01 6–16 cm texture, uniformly imposed
through a seven-layer, 2 m column. The 50 m atmospheric boundary is idealized: the meteorological
values were retained without physical vertical extrapolation. Shared inputs constrain soil water,
mean soil temperature, census source and CO2; they do not make vegetation or thermal states identical.

- **ED-MORE:** [f49d50c](https://github.com/EDmodel/ED-MORE/tree/f49d50c89f01e5747eee2950a9cbe1d8e08371a5),
  gfortran dev, supplied calibrated Example04 PFT parameters, native `canopy_water_on` switch.
- **ED2:** [125f814d](https://github.com/EDmodel/ED2/tree/125f814dbbd7c258cf623254ca9554a7e59807fd),
  gfortran with local output-table, solver-success-copy and terminal forcing-prefetch corrections;
  a local OFF variant disables rainfall interception, leaf/wood surface-water vapour exchange and
  associated enthalpy fluxes. It is not an unmodified ED2.2 release or an identical native switch.
- Both retain native physiology and vegetation reconstruction; both enable growth, mortality and
  recruitment. In particular, this ED2 run has `PLANT_HYDRO_SCHEME=0`, `H2O_PLANT_LIM=2`,
  `IPHYSIOL=2`, `IBRANCH_THERMO=1`, `ICANTURB=2`, `IALLOM=3`. MORE retains its dynamic plant-water
  network and native trait dynamics. See [settings and provenance](SETTINGS.md).

The documentation branch is based on a later upstream beta; it does **not** mean that these runs
used that later engine or its newly added diagnostics.

## Results

All table entries are mm yr⁻¹, obtained from five-year ET totals divided by five.

| Forcing | Model | ET ON | ET OFF | ON − OFF |
|---|---|---:|---:|---:|
| Tower | ED2 | 997.94 | 924.85 | 73.10 |
| Tower | MORE | 861.46 | 720.59 | 140.87 |
| Tower + total-matched ERA5-Land rain | ED2 | 1293.01 | 968.83 | 324.18 |
| Tower + total-matched ERA5-Land rain | MORE | 1332.35 | 739.14 | 593.21 |
| Full ERA5-Land | ED2 | 1379.62 | 1035.98 | 343.64 |
| Full ERA5-Land | MORE | 1440.54 | 786.04 | 654.50 |


Let I = ET_ON − ET_OFF. The rain-replacement interaction is J = I_rain − I_tower:
**ED2 251.08** and
**ED-MORE 452.34 mm yr⁻¹**.
I is a coupled ecosystem response, not canopy evaporation alone. Holding the five-year rainfall
total fixed does not hold monthly totals, intensity, timing or covariation with other weather fixed.
Full ERA5-Land also changes rainfall amount and other meteorology, so it is a broader sensitivity.

MORE's complete 450 s runs retain J =
447.06 mm yr⁻¹.
ED2 has matched-state wet/dry 14-day 900/450 s checks, not a full five-year 450 s matrix.
Small effects and GPP are less robust. Read [numerical qualifications](VALIDATION.md) with the table.

## Evidence and limits

- [Exact summary numbers](results.json): all absolute, switch and interaction metrics, including
  GPP, H, Rnet, drainage, surface runoff and soil-water storage, plus MORE at 450 s.
- [Original versus modified MORE](EXAMPLE04_COMPARISON.md): the original reproduction and the
  subsequent changes use explicitly separated statistical masks.
- [Settings](SETTINGS.md) and [provenance hashes](provenance.json): versions, common constraints,
  retained differences, source summaries and config hashes.
- [Validation](VALIDATION.md): coverage, restarts, water accounting and retained warnings.

These small derived tables are documentation of measured results. Native output, meteorological
and census downloads, executables and machine-specific run directories are not committed.
This is a reviewable evidence summary, not a self-contained full-run reproduction package.
The archived full local review bundle is identified by hash in provenance.json.

AI assistance: Codex assisted with setup, execution, source inspection, numerical analysis,
evidence checks and writing. The repository owner authorized this evidence branch; the proposed
community comment remains a separate, unpublished draft for human review.
