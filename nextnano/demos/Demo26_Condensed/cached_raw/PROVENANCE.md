# cached_raw: shipped nextnano++ Professional output

Byte-for-byte copies of output that nextnano++ Professional produced on the work
laptop for the Demo 26 investigation. Nothing here is synthetic or recomputed.
SHA-256 hashes and repository source paths for every file are in
`fixture_manifest.json` (written by `tools/build_fixtures.py`).

The layout is exactly what `01_run_nextnano.py --run` writes, so
`02_calculate_chi2.py --input cached_raw` exercises the same code path as a fresh run.

| folder | produced by | used by mode |
|---|---|---|
| `kp8/` | 8-band k.p deck (token-identical to `decks/kp8_dispersion.in`): 301-point dispersion to 0.1 pi/a, k=0 spinor envelopes of all 14 states (CbHhLhSo basis), spinor composition, nextnano's own kp8 dipole matrix elements | `kp8` (production); dispersion shape also used by the two historical modes |
| `singleband_case04_graded/` | single-band Gamma{}+HH{} deck `decks/singleband_case04_graded.in` (1 nm grading): k=0 energies and envelopes | `demo26-baseline`, `demo26-cutoff` |
| `supplied/case00_abrupt_matrix_elements.json` | **processed values, not raw output**: overlaps and z of the abrupt single-band case, taken from the historical Demo 19 table because the raw case00 envelopes were not preserved | `demo26-cutoff` only, and only when `singleband_case00_abrupt/` is absent |

Only the files the parser reads are shipped (about 3 MB). A fresh Professional
run writes many more; the parser ignores them.
