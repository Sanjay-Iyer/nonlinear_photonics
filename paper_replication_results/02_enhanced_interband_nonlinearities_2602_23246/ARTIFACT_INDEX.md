# Artifact Index

This directory summarizes how the repo currently represents arXiv:2602.23246v1,
"Enhanced Interband Optical Nonlinearities from Coupled Quantum Wells."

## Source paper

- `../../2602.23246v1.pdf`

## Existing repo artifacts

| Artifact | Purpose |
| --- | --- |
| `../../replication/qw_metasurface/REPORT.md` | Uses this paper as Ref38/companion evidence for the x = 0.55 ACQW stack, E11/E22 anchors, and graded-interface chi^(2) context. |
| `../../replication/qw_metasurface/config/paper_params.yaml` | Records x = 0.55, the 18.2/7.1/1.8/2.9 nm stack, and documentary anchors from this paper. |
| `../../replication/qw_metasurface/phase2_aestimo/` | Aestimo electronic-structure results for the shared ACQW stack. |
| `../../replication/qw_metasurface/phase3_kdotpy/` | kdotpy energy cross-check for the same stack. |
| `../../replication/qw_metasurface/phase4_chi2/` | chi^(2) spectra and cancellation discrepancy for the shared stack. |
| `../../git/aestimo/paper/reference_data/acqw_solver_consensus_v1/` | Older three-solver consensus snapshot for the same nominal ACQW structure. |

## Missing artifact class

No standalone implementation directory dedicated only to `2602.23246v1` was found.
Current results are embedded in the metasurface replication and the older ACQW
solver-consensus work.

## Documentation in this clean layer

- `SUMMARY.md`
