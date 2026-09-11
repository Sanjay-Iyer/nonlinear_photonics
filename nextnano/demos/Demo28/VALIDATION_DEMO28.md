# Demo 28 execution record

Demo 28 copies the current Demo26_Condensed implementation and frozen data,
adds a short user guide and package-specific tests, and updates the launcher
metadata/environment names to Demo 28. Historical calculation mode names are
preserved so the scientific provenance remains identifiable.

Executed in the Demo28 directory on the home laptop:

```text
python 01_run_nextnano.py --preflight --no-parse
python 02_calculate_chi2.py --input cached_raw --check-reference
python -m pytest tests -q -p no:cacheprovider --basetemp output/demo28_pytest
```

- Launcher static checks and cached parser self-test passed. Executable grammar
  checking was explicitly skipped. No licensed solver was launched.
- Cached numerical validation: **55 PASS, 0 FAIL, 0 NOT APPLICABLE**.
  These include 30 reference, 22 consistency and 3 independent-rederivation checks.
  Detailed results: output/analysis/VALIDATION.md and validation.json.
- Demo 28 automated tests: **12 passed**. Includes historical complex-spectrum
  agreement, units, integration, phase invariance, retained imaginary component,
  deck equivalence, no-launch preflight, raw parsing and runtime path checks.
- The historical cutoff observable comparison and signed Re/Im figure were
  opened and visually inspected after regeneration.
- Independent read-only review found no substantive copy-specific import,
  portability or metadata issue. It requested this execution record be included;
  VALIDATION_DEMO28.md is included in the delivered package.

| Mode | nRMSE abs(real) | nRMSE magnitude | Re zeros nm |
|---|---:|---:|---|
| kp8 | 0.2654 | 0.3218 | 690.603, 1388.562 |
| demo26-baseline | 0.2379 | 0.2624 | 714.028, 1437.479 |
| demo26-cutoff | 0.0658 | 0.2374 | 617.343, 1326.516 |

The cutoff mode's close shape match survives the packaging change. It remains a
historical extrapolation diagnostic with an explicitly supplied abrupt-matrix
checkpoint in the cached fixture. It does not establish a full physical paper
reproduction. The newer kp8 mode has no historical full-spectrum reference;
its checks concern raw-state data, matrix comparisons and numerical invariants.

The original source package's archived test-count claims are not the Demo 28
test record. Only the tests and checks listed above were run for this copy.
