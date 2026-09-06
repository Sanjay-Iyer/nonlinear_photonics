# Demo 27 reuse audit

What Demo 27 takes from Demos 23-26 instead of recomputing it, and whether
those artifacts are still byte-identical to when Demo 27 first read them.

Demo 27 reads these and never writes to them.

| artifact | exists | integrity | entries | bytes | reusable_for | provides |
|---|---|---|---|---|---|---|
| demo23_config | True | BASELINED | 1 | 2779 | ALL | the frozen structure, mesh, BZ convention and chi2 settings |
| demo23_production_raw | True | BASELINED | 738 | 16298436 | 27D 27C 27F 27G 27H 27I 27J | kp8 dispersion over 301 k points and k=0 state/matrix output |
| demo23_kmax_sensitivity_raw | True | BASELINED | 5166 | 113883421 | 27F 27G | kmax cases at 0.05, 0.075, 0.10, 0.125 pi/a and grids at 101/201/301 |
| demo24_reachability | True | BASELINED | 1 | 54449 | 27C 27G 27K | the reachability finding and the k-truncation artifact identification |
| demo24_feature_sensitivity | True | BASELINED | 1 | 4569 | 27D 27E 27G 27J | measured dLambda/dE per spectral feature |
| demo25_pilot_decks | True | BASELINED | 19 | 186716 | 27A 27B | the finite-k output pilot, its gate, and the production sizing model |
| demo26_root_cause_ranking | True | BASELINED | 1 | 2280 | ALL | the ranked list of remaining hypotheses with confidence and Pro-needed flags |
| demo26_feature_diagnosis | True | BASELINED | 1 | 1285 | 27D 27E 27G 27J | per-feature (P1 Z1 P2 P3 Z2 P4) paper-vs-model wavelengths and verdicts |
| paper_curve | True | BASELINED | 1 | 457 | 27D 27E 27G 27J 27L | the digitized Ramesh Fig. 2d simulated curve |

## Reuse rules

| artifact | reuse_rule |
|---|---|
| demo23_config | inherited verbatim; a sub-demo may override only fields it declares |
| demo23_production_raw | valid as the same-structure control wherever geometry, mesh, temperature and solver model are unchanged - this IS 27D's graded arm, 27F's numerical control, 27G's 0.1 pi/a arm, 27H's [010] arm, 27I's kp8 arm and 27J's 300 K arm. NOT valid as 27E's flat-band control: 27E must regenerate that arm so both of its arms move together if 27D changes the geometry decision |
| demo23_kmax_sensitivity_raw | 27G's 0.1 pi/a and 0.125 pi/a arms already exist; only the 0.2 pi/a (Gamma-X) arm is new solver work |
| demo24_reachability | conclusions only; re-deriving them is explicitly out of scope |
| demo24_feature_sensitivity | converts any energy shift a sub-demo produces into a predicted wavelength shift without rerunning the chi2 engine |
| demo25_pilot_decks | 27A and 27B DELEGATE to this demo rather than reimplementing it; Demo 27 must not fork the pilot |
| demo26_root_cause_ranking | sets the campaign priority order; re-ranking is 27's job only after new data |
| demo26_feature_diagnosis | the acceptance target every geometry/convention sub-demo is scored against |
| paper_curve | diagnostic only. Demo 23's PAPER_DATA_PROVENANCE.md states these are eye-digitized and are not acceptance gates |
