# Validation scope and retained numerical qualifications

The study is accepted for the limited ET-direction statement in the README. It is not accepted
as a demonstration of numerical convergence, field accuracy or a common causal mechanism.

## Completed checks

- The common 900 s matrix comprises six ON/OFF pairs, three forcing scenarios in each model.
  Every accepted run covers the full 1,826-day target window. All three MORE scenarios also have
  complete five-year 450 s pairs. Coverage, finite active states, input/initial-state contracts,
  completion logs and units were checked before aggregation.
- The primary table is reconstructed from accepted daily/monthly summaries. The annual rates
  are five-year integrals divided by five. H and Rnet are time means; soil water is a time-weighted
  column storage, not a flux. NEE and diagnostic ED2 LE are excluded from the shared metric set
  because the output definitions do not support the same comparison.
- MORE diagnostic replays of all twelve original trajectories preserved every compared native
  output data array bitwise. Independent water-ledger reconstruction checked boundary terms,
  inventory changes and numerical adjustments. This verifies bookkeeping for those trajectories;
  it neither validates the physical parameterization nor establishes full energy closure.
- ED2's new HISTORY protocol passed twelve 900 s continuations with exact daily-output identity
  to the original continuous trajectories. Each paired 450 s run began from the same corresponding
  state. The twenty-four 14-day runs cover wet and dry windows, all three forcings and both switch
  states. They are not twenty-four independent ecological replicates.
- The retained full-ERA ED2 600 s pair gives I = 343.06 mm yr⁻¹, versus 343.64 at 900 s.
  This is one additional scenario, not a complete finer-step ED2 matrix.

## What remains sensitive

| ET response, mm yr⁻¹ | MORE 900 s | MORE 450 s |
|---|---:|---:|
| Tower I | 140.87 | 140.47 |
| Matched-rain I | 593.21 | 587.53 |
| Full ERA5-Land I | 654.50 | 643.97 |
| Matched-rain J | 452.34 | 447.06 |

Here I = ET_ON − ET_OFF and J = I_rain − I_tower. Their positive directions persist in the
tested runs and the selected ED2 short windows. One very small ED2 dry-window J changes from
0.06623 to 0.03075 mm per 14 days: a roughly 54% relative change despite a small absolute change.
It must not be described as a stable magnitude just because it passes an absolute screening floor.

MORE's full-ERA GPP switch effect changes sign, from +0.01049 at 900 s to −0.00734 at 450 s
(kg C m⁻² yr⁻¹). No general GPP direction is inferred. Root uptake is not relabelled transpiration,
and ET_ON − ET_OFF is not relabelled direct interception evaporation.

MORE's water solver retains nonzero failure diagnostics and forced acceptance of some steps;
local error-limit exceedances are also documented. Independent water-ledger closure can coexist
with such numerical sensitivity. The rain interaction in net film-water adjustment (floor additions
minus capacity-limit removals) is 32.31 at 900 s and 13.17 mm yr⁻¹ at 450 s. These adjustments are
not an estimate of ET bias and cannot be subtracted from ET. Their influence on the coupled state
and flux partition has not been causally isolated.

ED2 has small external water-accounting remainders (roughly 0.4–0.5 mm yr⁻¹ in the retained audit)
and unexported adjustment integrals. They are reported, not assigned wholly to numerical error.
Rnet − H − LE is not a complete energy residual: storage, advected enthalpy and boundaries matter.

Rain replacement changes intensity, temporal and seasonal allocation and covariation with the
other tower variables. It is not a frequency-only intervention. Full ERA5-Land also changes total
rain and the other meteorology. This matrix does not reproduce or test the author's quantitative
attribution of the excess to rainfall timing alone.

All original failed/interrupted checks remain in the local archive. Later acceptance refers to
specific successful corrected protocols; it does not erase those failures. The public files are
compact evidence summaries, not the complete private run archive or an automated rerun protocol.

## Checks for this evidence branch

Only documentation and derived summary numbers are added. The model, input files, original
results and four long-term local research documents remain unchanged. Packaging checks recompute
I and J from absolute results, verify source hashes and common-window coverage, and scan the
tracked addition for machine paths. Repository lint and its tests are run separately before push.
No engine build, simulation, refitting or field-score calculation is part of this branch.
