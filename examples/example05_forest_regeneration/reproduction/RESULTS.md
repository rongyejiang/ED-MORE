# Recorded BCI regeneration results

These are reproduction comparisons with the frozen v0.4.1 README, not scores against observations. All values were recalculated from closed output files with the native `plot_regeneration.py` reader. The full table preserves more digits than the discussion reply so rounding can be checked.

- The 1600–2020 run and native plot completed with exit code 0 in 7,225.2738 seconds (gfortran 15.2.0 dev, 8 threads).
- Output contains 421 annual and 5,052 monthly records. All 1,173,157 unmasked numeric values were finite. Another 364,517 values were masked; their individual applicability was not exhaustively audited.
- The ten-year pilot matched the first ten years of the long run for all 158 annual and 159 monthly variables, including coordinates and masks.
- The final checkpoint contained 25 patches and 1,004 cohorts, with patch area sum 1.0 and all 407,469 unmasked numeric values finite.
- At the README's displayed precision, 34 of 63 values matched and 29 differed. Both 1650 and 1700 matched all nine values; differences were already present by 1800.
- No warning lines appeared in the run log, but `mean_work_water_nfail_py` was nonzero in July 1921: 2.4662905218172886e-5. Its annual value was 2.094657703461259e-6. This is an area-weighted diagnostic, not an integer count of failed steps. RK45 rescue remained zero. Normal exit does not erase this diagnostic, and the later event alone cannot explain differences already present in 1800.

The original native configuration and PFT values were retained, with paths redirected in an isolated execution copy. The run began from bare ground, not the separately prepared census initialization. The repository's original census summary was retained for plotting. No refitting, five-year census check or Palo Verde run is represented here.

The author's full forcing and output files have not been compared. The README identifies a production run with 20 threads; the precise long-run compiler/build setup remains unconfirmed. Local ifx and production runs, and an independent full coupled carbon/water/energy budget closure, were not performed. Compiler/build differences are a possible explanation to investigate, not an established cause. The public input audit found no mismatch in the tested conversion chain; that is not proof that every source-data assumption equals the reference setup.

## Table

AGB and its PFT components are MgC/ha; basal area is m²/ha; LAI is m²/m²; `stems10` is stems/ha for DBH ≥10 cm; GPP and NPP are MgC/ha/year. A match means equality after formatting the local value to the corresponding README cell's decimal precision.

| Year | Metric | README | Local | Local - README | Matches displayed precision |
|---|---|---:|---:|---:|:---:|
| 1650 | agb_total | 50.0 | 49.99256761 | -0.00743239004303 | yes |
| 1650 | agb_early | 35.0 | 34.9793541551 | -0.0206458449318 | yes |
| 1650 | agb_mid | 14.3 | 14.341510048 | 0.0415100480156 | yes |
| 1650 | agb_late | 0.7 | 0.671703406873 | -0.0282965931268 | yes |
| 1650 | basal_area | 23.0 | 23.0373145143 | 0.0373145142682 | yes |
| 1650 | lai | 5.8 | 5.78390301313 | -0.0160969868715 | yes |
| 1650 | stems10 | 384 | 383.506380734 | -0.493619265872 | yes |
| 1650 | gpp | 25.8 | 25.7893330077 | -0.0106669922517 | yes |
| 1650 | npp | 12.8 | 12.8028753872 | 0.00287538724115 | yes |
| 1700 | agb_total | 66.6 | 66.5580893866 | -0.0419106134327 | yes |
| 1700 | agb_early | 23.6 | 23.6189362801 | 0.0189362801177 | yes |
| 1700 | agb_mid | 41.1 | 41.1051972275 | 0.00519722747392 | yes |
| 1700 | agb_late | 1.8 | 1.83395587898 | 0.0339558789757 | yes |
| 1700 | basal_area | 24.5 | 24.4958217354 | -0.00417826455994 | yes |
| 1700 | lai | 5.7 | 5.71372145322 | 0.0137214532198 | yes |
| 1700 | stems10 | 413 | 412.74245048 | -0.257549520394 | yes |
| 1700 | gpp | 25.6 | 25.6069910833 | 0.00699108328613 | yes |
| 1700 | npp | 12.0 | 12.0220015491 | 0.0220015491175 | yes |
| 1800 | agb_total | 81.8 | 81.6034050739 | -0.196594926134 | no |
| 1800 | agb_early | 7.5 | 7.6528154999 | 0.152815499898 | no |
| 1800 | agb_mid | 72.1 | 71.7213927276 | -0.378607272384 | no |
| 1800 | agb_late | 2.2 | 2.22919684635 | 0.029196846352 | yes |
| 1800 | basal_area | 25.9 | 25.9225338486 | 0.0225338485693 | yes |
| 1800 | lai | 5.8 | 5.84017265052 | 0.0401726505245 | yes |
| 1800 | stems10 | 350 | 370.247019546 | 20.2470195463 | no |
| 1800 | gpp | 26.1 | 26.1021581522 | 0.0021581521846 | yes |
| 1800 | npp | 12.0 | 12.0151280048 | 0.015128004806 | yes |
| 1900 | agb_total | 91.9 | 92.1954460382 | 0.295446038201 | no |
| 1900 | agb_early | 4.3 | 4.01869838902 | -0.281301610981 | no |
| 1900 | agb_mid | 84.2 | 84.6399206468 | 0.439920646754 | no |
| 1900 | agb_late | 3.3 | 3.53682700243 | 0.236827002428 | no |
| 1900 | basal_area | 27.3 | 27.4032376479 | 0.103237647863 | no |
| 1900 | lai | 5.9 | 5.90184484996 | 0.00184484995687 | yes |
| 1900 | stems10 | 355 | 367.732432271 | 12.7324322709 | no |
| 1900 | gpp | 27.1 | 27.0634461264 | -0.0365538735915 | yes |
| 1900 | npp | 12.6 | 12.5709723178 | -0.029027682224 | yes |
| 1950 | agb_total | 102.8 | 103.358496216 | 0.558496216259 | no |
| 1950 | agb_early | 5.7 | 4.98219574032 | -0.717804259681 | no |
| 1950 | agb_mid | 94.3 | 94.8598482698 | 0.55984826983 | no |
| 1950 | agb_late | 2.8 | 3.51645220611 | 0.71645220611 | no |
| 1950 | basal_area | 29.5 | 29.4585642115 | -0.0414357885439 | yes |
| 1950 | lai | 6.1 | 6.053212136 | -0.0467878640011 | yes |
| 1950 | stems10 | 353 | 345.407265119 | -7.5927348809 | no |
| 1950 | gpp | 28.3 | 28.2227691367 | -0.0772308633125 | no |
| 1950 | npp | 13.3 | 13.2595696804 | -0.0404303196153 | yes |
| 2010 | agb_total | 126.9 | 127.198459588 | 0.298459588195 | no |
| 2010 | agb_early | 16.7 | 15.3919603404 | -1.3080396596 | no |
| 2010 | agb_mid | 107.4 | 109.053218271 | 1.65321827069 | no |
| 2010 | agb_late | 2.7 | 2.7532809771 | 0.0532809771038 | no |
| 2010 | basal_area | 34.0 | 33.9609553651 | -0.0390446349062 | yes |
| 2010 | lai | 6.3 | 6.3399267185 | 0.0399267185046 | yes |
| 2010 | stems10 | 326 | 310.209200535 | -15.7907994651 | no |
| 2010 | gpp | 32.6 | 32.4917713133 | -0.108228686667 | no |
| 2010 | npp | 16.2 | 16.1570351985 | -0.0429648014638 | yes |
| 2020 | agb_total | 130.9 | 131.60103611 | 0.701036110265 | no |
| 2020 | agb_early | 24.3 | 21.7642334225 | -2.53576657747 | no |
| 2020 | agb_mid | 103.9 | 107.252557126 | 3.35255712592 | no |
| 2020 | agb_late | 2.7 | 2.58424556182 | -0.115754438181 | no |
| 2020 | basal_area | 34.8 | 34.7868521535 | -0.0131478465122 | yes |
| 2020 | lai | 6.3 | 6.31992913998 | 0.0199291399791 | yes |
| 2020 | stems10 | 302 | 308.43606527 | 6.43606526951 | no |
| 2020 | gpp | 34.0 | 33.9444164705 | -0.0555835295042 | no |
| 2020 | npp | 17.2 | 17.1494827691 | -0.050517230891 | no |
