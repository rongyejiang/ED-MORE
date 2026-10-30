# BCI Example 05: ifx follow-up

The completed ifx production run remains close to, but does not reproduce, every value in the Example 05 README. This is a record of a build comparison, not a proposed fix or a confirmed compiler bug. The model and scientific inputs were held at v0.4.1 (`f49d50c89f01e5747eee2950a9cbe1d8e08371a5`). No parameters were refitted.

For the 2010 annual mean:

| Metric | README | gfortran dev | ifx production | ifx minus README |
|---|---:|---:|---:|---:|
| Total AGB (MgC/ha) | 126.9 | 127.19846 | 126.11302 | -0.6202% |
| Stems/ha, DBH >=10 cm | 326 | 310.20920 | 321.14823 | -1.4883% |

The ifx result is closer in stem density and farther in total AGB. Relative to the local gfortran run, ifx changes these two metrics by -0.8533% and +3.5263%, respectively. Neither the scientific importance of these differences nor their full cause has been established.

## Settings and checks

- GNU Fortran 15.2.0: dev, generic CPU, IPO off, 8 threads.
- ifx 2026.1.0 (20260617): production, `ED_CPU_TARGET=host`, IPO on, 8 threads. This is **host**, not the preset's default `cascadelake` target. The author's full CPU/build settings have not been confirmed; the README timing used 20 threads. The repository requires thread-count invariance, but no additional 8-versus-20 experiment was done here.
- Both long runs used 1600-01-01 through 2021-01-01, original bare-ground initialization, PFT parameters, CO2 and configuration. The native script's default is 8 threads; the ifx command also set `--threads 8` explicitly. There was no calibration or restart.
- The same ARCO-derived 2003-2022 forcing file was used throughout. Sources, the adapter, native conversion rules and sampled GDEX checks are described in [README.md](README.md) and [provenance.json](provenance.json). The author's actual forcing file has not been compared. No new forcing was generated for the ifx run.
- A fresh audit matched all 432 tracked source files in each of four source copies to the pinned Git blobs. Execution scripts were unchanged. For all five long/pilot runs, the native config writer regenerated the actual runtime configuration, after normalizing execution paths. Exported effective parameters also matched within the two long runs and within the three pilots. Library hashes and explicit library loading were checked.
- Both long runs exited successfully and have 421 annual records and 5,052 monthly records. All 1,173,157 valid numeric values in each annual/monthly pair are finite. Final patch areas sum to 1. The final ifx state contains 25 patches and 992 cohorts; gfortran has 25 and 1,004.
- Both long runs retain a nonzero `mean_work_water_nfail_py` diagnostic in July 1921: 2.4662905218172886e-5 (GNU) and 2.4792912766750084e-5 (ifx). This is unconverged water substeps per fast step, not an integer failure count. RK45 rescue and stage-clamp monthly diagnostics are zero. Successful completion is not a claim that this diagnostic is resolved.
- Independent dev builds previously passed all 95 registered CTest tests with each compiler. Production tests were disabled by its preset; production CTest and an independent full coupled carbon/water/energy closure have not been run. This evidence update does not change model code and did not rebuild or rerun it.

Wall time including native plotting was 7,225.27 s for gfortran dev and 6,685.29 s for ifx production. These are historical single runs, not a controlled speed benchmark.

The relevant production build command, with machine paths replaced by variables, was:

```bash
FC=ifx cmake --preset production -B "$BUILD" \
  -DCMAKE_PREFIX_PATH="$PREFIX" -DPython3_EXECUTABLE="$PYTHON" \
  -DED_CPU_TARGET=host -DED_OPENMP=ON -DED_BUILD_TESTS=OFF -DED_TEST_LONG=OFF
cmake --build "$BUILD" -j 2
```

The unchanged `run_example.py --threads 8` ran from the example directory in a separate execution copy, with `EDMORE_LIB` explicitly set to that production library. The existing [compare_results.py](compare_results.py) reads completed output using the pinned native plotting reader:

```bash
python "$EVIDENCE/compare_results.py" --source "$PINNED_SOURCE" --annual "$COMPLETED_ANNUAL_OUTPUT"
```

The audit also checked 2010 AGB directly from `mean_agb_py` and independently summed the PFT AGB; both agree within floating-point summation precision. AGB uses kgC/m2 times 10; stems use individuals/m2 times 10,000, summing the native size classes starting at 10 cm. These are annual means, not the end-of-year checkpoint.

## Ten-year check

A separate ifx dev run used the same inputs and the same 1600-1609 window as the two existing pilots. Only the run end time was shortened, using the native configuration API.

| Build | 1609 AGB (MgC/ha) | 1609 LAI | Cohorts at 1610-01-01 |
|---|---:|---:|---:|
| gfortran dev | 18.436445856984 | 6.980107313720 | 94 |
| ifx dev | 18.428289224721 | 6.981466204439 | 92 |
| ifx production | 18.428286609825 | 6.981468119064 | 92 |

All three pilots have 10 annual/120 monthly records, finite valid values and zero values for the three solver diagnostics above. ifx dev differs from ifx production by +0.00001419% in 1609 total AGB, and from gfortran dev by -0.04424189%. This suggests the early difference is not caused solely by production optimization. It does not isolate a particular compiler operation, prove bitwise identity, or establish what a full ifx dev run would do. Even the two ifx final cohort ID sets are not identical.

## Full reference comparison

These are the seven years and nine metrics in the pinned README. GNU matches 34/63 entries and ifx 27/63 at the README's displayed precision. This rounding comparison is not an accuracy score or a scientific pass/fail criterion. AGB columns use MgC/ha; basal area m2/ha; LAI m2/m2; stem density stems/ha; GPP and NPP MgC/ha/year. Exact values, binary/input/output hashes and checks are in [ifx_results.json](ifx_results.json).

| Year | Metric | README | gfortran dev | ifx production | Precision match (GNU / ifx) |
|---|---|---:|---:|---:|:---:|
| 1650 | agb_total | 50.0 | 49.9925676100 | 49.9846448811 | yes / yes |
| 1650 | agb_early | 35.0 | 34.9793541551 | 34.9581988659 | yes / yes |
| 1650 | agb_mid | 14.3 | 14.3415100480 | 14.3557518247 | yes / no |
| 1650 | agb_late | 0.7 | 0.6717034069 | 0.6706941905 | yes / yes |
| 1650 | basal_area | 23.0 | 23.0373145143 | 23.0315469366 | yes / yes |
| 1650 | lai | 5.8 | 5.7839030131 | 5.7839083537 | yes / yes |
| 1650 | stems10 | 384 | 383.5063807341 | 385.8395146993 | yes / no |
| 1650 | gpp | 25.8 | 25.7893330077 | 25.7698325176 | yes / yes |
| 1650 | npp | 12.8 | 12.8028753872 | 12.7976946430 | yes / yes |
| 1700 | agb_total | 66.6 | 66.5580893866 | 66.6221170448 | yes / yes |
| 1700 | agb_early | 23.6 | 23.6189362801 | 23.5205154444 | yes / no |
| 1700 | agb_mid | 41.1 | 41.1051972275 | 41.2479635168 | yes / no |
| 1700 | agb_late | 1.8 | 1.8339558790 | 1.8536380836 | yes / no |
| 1700 | basal_area | 24.5 | 24.4958217354 | 24.4933066228 | yes / yes |
| 1700 | lai | 5.7 | 5.7137214532 | 5.7149151433 | yes / yes |
| 1700 | stems10 | 413 | 412.7424504796 | 402.0195523720 | yes / no |
| 1700 | gpp | 25.6 | 25.6069910833 | 25.5965098071 | yes / yes |
| 1700 | npp | 12.0 | 12.0220015491 | 12.0164114106 | yes / yes |
| 1800 | agb_total | 81.8 | 81.6034050739 | 81.8375258004 | no / yes |
| 1800 | agb_early | 7.5 | 7.6528154999 | 7.1249355292 | no / no |
| 1800 | agb_mid | 72.1 | 71.7213927276 | 72.3439860068 | no / no |
| 1800 | agb_late | 2.2 | 2.2291968464 | 2.3686042644 | yes / no |
| 1800 | basal_area | 25.9 | 25.9225338486 | 25.9598944289 | yes / no |
| 1800 | lai | 5.8 | 5.8401726505 | 5.8432893540 | yes / yes |
| 1800 | stems10 | 350 | 370.2470195463 | 359.3879111014 | no / no |
| 1800 | gpp | 26.1 | 26.1021581522 | 26.0557660436 | yes / yes |
| 1800 | npp | 12.0 | 12.0151280048 | 11.9962973457 | yes / yes |
| 1900 | agb_total | 91.9 | 92.1954460382 | 92.0181538517 | no / no |
| 1900 | agb_early | 4.3 | 4.0186983890 | 3.8343698746 | no / no |
| 1900 | agb_mid | 84.2 | 84.6399206468 | 84.7290889934 | no / no |
| 1900 | agb_late | 3.3 | 3.5368270024 | 3.4546949837 | no / no |
| 1900 | basal_area | 27.3 | 27.4032376479 | 27.2953832980 | no / yes |
| 1900 | lai | 5.9 | 5.9018448500 | 5.8879226425 | yes / yes |
| 1900 | stems10 | 355 | 367.7324322709 | 345.5866596580 | no / no |
| 1900 | gpp | 27.1 | 27.0634461264 | 27.0225472061 | yes / no |
| 1900 | npp | 12.6 | 12.5709723178 | 12.5568951985 | yes / yes |
| 1950 | agb_total | 102.8 | 103.3584962163 | 102.5348592041 | no / no |
| 1950 | agb_early | 5.7 | 4.9821957403 | 7.1983222097 | no / no |
| 1950 | agb_mid | 94.3 | 94.8598482698 | 92.1635788921 | no / no |
| 1950 | agb_late | 2.8 | 3.5164522061 | 3.1729581023 | no / no |
| 1950 | basal_area | 29.5 | 29.4585642115 | 29.4732277574 | yes / yes |
| 1950 | lai | 6.1 | 6.0532121360 | 6.0750556363 | yes / yes |
| 1950 | stems10 | 353 | 345.4072651191 | 342.9964146524 | no / no |
| 1950 | gpp | 28.3 | 28.2227691367 | 28.2109752097 | no / no |
| 1950 | npp | 13.3 | 13.2595696804 | 13.2488652642 | yes / no |
| 2010 | agb_total | 126.9 | 127.1984595882 | 126.1130242278 | no / no |
| 2010 | agb_early | 16.7 | 15.3919603404 | 18.3417082219 | no / no |
| 2010 | agb_mid | 107.4 | 109.0532182707 | 105.1720394401 | no / no |
| 2010 | agb_late | 2.7 | 2.7532809771 | 2.5992765657 | no / no |
| 2010 | basal_area | 34.0 | 33.9609553651 | 33.9359433301 | yes / no |
| 2010 | lai | 6.3 | 6.3399267185 | 6.3183133899 | yes / yes |
| 2010 | stems10 | 326 | 310.2092005349 | 321.1482306818 | no / no |
| 2010 | gpp | 32.6 | 32.4917713133 | 32.4850386802 | no / no |
| 2010 | npp | 16.2 | 16.1570351985 | 16.1655400612 | yes / yes |
| 2020 | agb_total | 130.9 | 131.6010361103 | 130.6866705051 | no / no |
| 2020 | agb_early | 24.3 | 21.7642334225 | 24.9660414838 | no / no |
| 2020 | agb_mid | 103.9 | 107.2525571259 | 103.2574964768 | no / no |
| 2020 | agb_late | 2.7 | 2.5842455618 | 2.4631325444 | no / no |
| 2020 | basal_area | 34.8 | 34.7868521535 | 34.7929910948 | yes / yes |
| 2020 | lai | 6.3 | 6.3199291400 | 6.3039712696 | yes / yes |
| 2020 | stems10 | 302 | 308.4360652695 | 303.5139824763 | no / no |
| 2020 | gpp | 34.0 | 33.9444164705 | 33.9705963048 | no / yes |
| 2020 | npp | 17.2 | 17.1494827691 | 17.1589967645 | no / yes |

Prepared with help from Codex; numbers were checked against retained inputs, outputs and native scripts. Raw model output and downloaded data are not committed.
