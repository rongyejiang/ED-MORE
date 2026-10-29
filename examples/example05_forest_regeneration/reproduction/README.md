# BCI Example 05 reproduction evidence

This folder documents one completed BCI regeneration run and the small adapter used to prepare its forcing. It is shared on a fork for inspection, not as a proposed model fix. The cause of the differences from the example's README remains unresolved.

- **Model:** ED-MORE v0.4.1, `f49d50c89f01e5747eee2950a9cbe1d8e08371a5`.
- **Run:** 1600–2020, bare-ground initialization, shipped configuration and PFT parameters, no refitting; gfortran 15.2.0, dev build, 8 threads.
- **Weather:** ECMWF ERA5-Land ARCO, 2003–2022, the 9.2°N / 79.8°W cell. The original 20-year recycling configuration was retained.
- **2010:** total AGB 127.198459588 MgC/ha (README 126.9); stems ≥10 cm 310.209200535/ha (README 326).

## Where to look

| File | Purpose |
|---|---|
| [arco_adapter.py](arco_adapter.py) | Portable form of the adapter: native float32 conversion, clipping, bounds and NetCDF quantization |
| [HISTORICAL_ADAPTER.md](HISTORICAL_ADAPTER.md) | The actual historical adapter and static preparation, with local paths replaced by placeholders |
| [extract_arco_point.py](extract_arco_point.py) | Re-extract the selected point from retained, hash-verified Zarr chunks; no download |
| [arco_sources.json](arco_sources.json) | Exact public URLs and SHA-256 hashes for the 128 retained ARCO objects |
| [provenance.json](provenance.json) | Static-cell sources, native helper hashes, original input/output hashes and portability changes |
| [RESULTS.md](RESULTS.md) | Completed-run checks, limitations, and all 63 comparisons at the README's displayed precision |
| [compare_results.py](compare_results.py) | Recompute that table from a completed annual output using the native plotting reader |
| [test_arco_adapter.py](test_arco_adapter.py) | Tests for flux semantics and input rejection |

No downloaded data, model NetCDF output, build products or credentials are committed. The results below are a documented summary of retained local output; the hashes identify those files.

## Data and conversion

The full hourly series came from [ECMWF's ERA5-Land ARCO archive](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land-timeseries), not from a complete GDEX download. [ECMWF documents](https://confluence.ecmwf.int/pages/viewpage.action?pageId=536218894) that ARCO precipitation and radiation have already been de-accumulated. The adapter therefore does **not** difference them a second time.

The eight fields are `t2m`, `d2m`, `sp`, `u10`, `v10`, `tp`, `ssrd` and `strd`. The 175,320 UTC end stamps run from 2003-01-01 01:00 through 2023-01-01 00:00. The repository's `ARCHIVE_VARIABLES` defines the conversions and precision: precipitation to kg m⁻² s⁻¹, radiation to W m⁻², and negative precipitation/shortwave clipping. The native `check_band`, `create_output`, `finish_output` and `publish` functions are used. `CHUNK=1` accommodates the one-cell archive. The native `write_bands` de-accumulation path is intentionally bypassed.

The static geopotential and land fraction came from [NCAR GDEX d633008](https://gdex.ucar.edu/datasets/d633008/), January 2026 invariant files. Exact subset URLs and hashes are in `provenance.json`. The nearest cell is 7.17884 km from the configured BCI location (9.1568°N, 79.8486°W). Its elevation is 72.97435 m; the configured site elevation was not changed. Elevation lapse correction is disabled in the shipped run configuration.

Independently decoded ARCO source chunks matched all 1,402,560 retained raw variable values. Selected GDEX samples matched ARCO exactly before clipping: 94,560 unique variable-hours, roughly 6.7% per variable. This is a sampled cross-check, not a comparison against the author's actual forcing file or every GDEX hour. There were 477 tiny negative raw precipitation hours; native clipping set these to zero. No additional data correction or gap filling was applied.

## Reproduce the preparation from retained inputs

The portable scripts are specifically for this recorded BCI case. They take paths as arguments, refuse existing output directories and do not launch a simulation. The source checkout must have the helper bytes recorded in `provenance.json`.

Use an environment with Python, NumPy, netCDF4, Zarr 2 and the dependencies of the native ERA5 preparation scripts. The package was verified with Python 3.12.14, NumPy 2.5.3, netCDF4 1.7.4 and Zarr 2.18.7. See the repository's [ERA5 preparation guide](../../../scripts/prepare_input/era5/README.md) for its environment.

In the commands below, `SOURCE` is a separate v0.4.1 checkout, `EVIDENCE` is this folder, `CACHE` contains the retained objects at the relative paths in `arco_sources.json`, and `WORK` is a new scratch directory outside the repository. These scripts do not fetch the objects; their public URLs and checksums are supplied so retrieval can be reviewed separately. If only the four existing point NPZ files are available, begin at the adapter command with their parent as `--raw-root`.

```bash
python "$EVIDENCE/extract_arco_point.py" --cache "$CACHE" --output "$WORK/points"
python "$EVIDENCE/arco_adapter.py" --source "$SOURCE" --raw-root "$WORK/points" --output "$WORK/archive"
python "$SOURCE/scripts/prepare_input/era5/make_forcing_file.py" \
  --data-path "$WORK/archive" --start 2003-01-01 --end 2022-12-31 \
  --lat 9.1568 --lon -79.8486 --out "$WORK/bci_era5land_2003-2022.nc"
python "$EVIDENCE/compare_results.py" --source "$SOURCE" --annual "$COMPLETED_ANNUAL_OUTPUT"
python -m pytest -q "$EVIDENCE/test_arco_adapter.py"
```

The last comparison only reads an existing `regen-Y.nc`; it does not run the model. For the historical simulation, the forcing was placed at Example 05's `data/bci_era5land_2003-2022.nc`, `EDMORE_LIB` selected the gfortran dev library, and the unchanged `run_example.py` ran with `--threads 8`. The run took 7,225.27 seconds including plotting. Do not run it in a source checkout containing results you need to preserve: the native script writes configurations, output and a figure in the example directory.

## What was verified for this public copy

Using the retained source chunks, the portable extractor and adapter recreated all 1,920 variable-month files plus the static file. Every variable and mask matched the historical archive. The unchanged native `make_forcing_file.py` then produced identical values and masks for all 13 variables, including time, coordinates, elevation and derived wind. File bytes differ because history/provenance attributes contain new timestamps and text; no byte-identical NetCDF claim is made.

The portable comparison script reproduced all 63 saved result values exactly. These checks verify that the shared preparation code preserves the recorded workflow; they do not establish why that simulation differs from the author's reference run. No new model run, compiler comparison or calibration was performed while preparing this folder.

Prepared with help from Codex; the original scripts, inputs, outputs and verification logs are retained locally.
