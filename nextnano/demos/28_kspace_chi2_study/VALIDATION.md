# Final validation record

## Results

- Demo28: **65 passed,0failed**.
- Relevant historical regressions (Demo22,23,24core): **47 passed,0failed**.
- Total across separate invocations: **112 passed,0failed**. Not every unrelated repository test was run.
- 28A max complex regression error6.9711344e-10pm/V against1e-8tolerance; full28Bcutoff error exactly0.
- Every reduced cutoff excludes higher nodes and recomputes endpoint weights.
- NumeratorIm0; full/real representation discrepancy0; electron/hole reconstruction error3.39e-13pm/V; shell reconstruction2.37e-13pm/V.
- Fixed-endpoint sampling, gauge/origin invariance, unit conversions and analytic KK controls pass.
- Metadata reference-path tests pass after correcting genuine relative-manifest defects. An intermediate run failed on these links; the test was not weakened.
- Isolated runtime dependency audit: PASS; no historical-access attempt or imported old-repository module. Local validation fixtures are explicitly historical references.

## Reproduction commands

From this demo directory:

```powershell
python scripts/calculate_chi2.py
python scripts/run_kspace_sweep.py
python studies/28C_extended_k/run.py
python scripts/run_response_audit.py
python scripts/run_numerical_audit.py
python scripts/run_causality_audit.py
python scripts/run_state_audit.py
python scripts/run_state_audit.py --input nextnano/raw_extended --output outputs/28I_state_character/extended
python studies/28C_extended_k/prepare_work_laptop.py
python -m pytest tests -q -p no:cacheprovider
python -I scripts/audit_dependencies.py
```

Relevant regression command, from repository root:

```powershell
python -m pytest nextnano/demos/22_k_resolved_8band_chi2_validation/tests nextnano/demos/23_k_resolved_dispersion_validation/tests nextnano/demos/24_equation2_spectral_shape_audit/tests/test_demo24.py -q -p no:cacheprovider
```

Actual interpreter: `C:/Users/iyer95/miniconda3/envs/NMIP/python.exe`; Python3.11.15,NumPy2.4.6. JUnit results are saved under `outputs/demo28_tests.xml` and `outputs/repository_regression_tests.xml`.

## Visual QA and numerical correspondence

All **62study PNGs** were inspected: original58 in labeled contact sheets and the added two small-Gamma and two extended cumulative plots individually. All have SVG counterparts. `outputs/plot_qa/inventory.json` lists paths/dimensions; the high-resolution originals remain unchanged.

Checked axes, units, readable legends, separate Re/Im cutoffs, four-case overlays, windowed versus global-maximum interpretation, cancellation, absolute versus normalized scales, and signed-energy KK labels. Figures use computed/saved arrays; algebraic tests independently reconstruct pathway and shell sums. The0.1meV spikes are explicitly unresolved sampling, not smoothed away. The KK symmetry defect is retained and documented rather than hidden behind the passing central overlay.

## Boundaries and reviewer status

No Professional solve was launched. Work preflight is static and skips parser execution; it cannot prove grammar/solver compatibility on the absent licensed installation. No historical demo was edited; unrelated worktree changes were preserved. The new package is untracked, so source SHA256 manifests are more informative than an empty git diff for it.

Specialist agents checked paper/causality, state evidence and response decomposition, but reached usage limits before a final integrated reviewer signoff. Final integration was directly checked here; this is not an external peer-review claim. Physical high-k validity and full real-field response completeness remain unresolved despite numerical tests passing.
