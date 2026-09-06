# Reading the home audit

Start with `DEMO26_HOME_EXHAUSTIVE_FINAL_REPORT.md`. Its 176 numbered entries correspond one-for-one to `EXHAUSTIVE_HOME_TEST_SUMMARY.csv` and `numbered_tests.json`. Read the independent assessment in `PHYSICS_PROFESSOR_REVIEW_HOME_EXHAUSTIVE.md` before treating the rankings as conclusions.

## Meaning of the counts

- A test row is a prescribed variant or a specific numerical/provenance question. Repeated baseline controls are included and are not independent scientific discoveries.
- `improved=YES` means an error metric decreased under the declared comparison. Tiny decreases and nonphysical diagnostics count. This is not successful paper reproduction.
- `FAIL` on a fit variant means it does not establish the requested physical reproduction. It does not exclude that parameter as a contributing cause.
- `INCONCLUSIVE` usually means inputs, physical equivalence, or interpretation are insufficient, even if a numerical result is available.
- `NOT TESTABLE` means the searched existing outputs cannot answer that exact eigenstate question. Friend-supplied existing files could avoid a new solve.
- Wavelength remappings use shared support and are not ranked against full-domain errors. Paper interpolation tests also use a different reference or sampling measure.
- `peak_count` includes weak extrema. Local prominence and widths must be inspected before calling them major peaks. Null target features are missing genuine extrema, not forced search-window endpoints.

## Reproducible files

Scripts in the parent Demo26 directory:

1. `verify_home_engines.py`: direct executed denominators, pathways, complex gauge tests and original fingerprints.
2. `numerical_home_audit.py`: 116 numerical variants and eight numerical assertions.
3. `close_data_tests.py`: 31 qualified alternative-data diagnostics.
4. `build_home_report.py`: assembles existing evidence, numbered rows, counts, inventories, report and rankings. Does not recompute spectra.
5. `test_home_audit.py`: checks report completeness, evidence, interpolation and preservation.

The original extended evaluator is imported as a library. The production evaluator is called only for comparison, never to invoke a solver. Existing analysis dependencies require the local bundled Python and `PYTHONPATH=C:/code/nonlinear_photonics/tmp/demo26_ext_deps` in this environment. No new solver command is part of this workflow.

## Limitations that remain

The production complex-input conjugation defect is demonstrated but the original source is preserved; the independent engine handles conjugation for the audit. Frozen real production data are unaffected. The original truncated-cutoff helper gives full-grid endpoint weight to an interior stopping point; new truncation tests recompute half endpoint weights without overwriting old outputs. The complete baseline integral is unaffected.

The request's supplied numerical families are covered. A universally exhaustive physical analysis is not claimed: a justified multiband optical reduction, provenance reconciliation, and any new information in the friend's files can lead to further home work.
