# Demo 27 master status

Generated from `MASTER_STATUS.json` by `framework/status.py`. Do not hand-edit:
run `python run_demo27.py --status` to regenerate, and let the stages record
their own outcomes.

Last written: 2026-09-06 20:20 UTC

| Demo | Question | Tier | Status | Pro required? | Runtime estimate | Prerequisite | Main conclusion |
|---|---|---:|---|---|---|---|---|
| 27A | Can nextnano++ Professional export usable finite-k state, spinor and matrix data at k != 0? | 1 | READY | Yes | 5 min - 21 min | none | unblocked manually; solver verdict pending analysis |
| 27B | Does the frozen-numerator approximation M(k) = M(0) change any Equation 2 pathway? | 2 | BLOCKED | Yes | 1 h - 3 h | 27A | unblocked manually; solver verdict pending analysis |
| 27C | Are the four states Equation 2 currently uses sufficient, or do other states carry optical weight? | 2 | BLOCKED | Yes | 30 min - 2 h | 27A | unblocked manually; solver verdict pending analysis |
| 27D | Does the paper's abrupt-interface structure reproduce the spectrum better than our 1 nm graded structure? | 2 | READY | Yes | 9 min - 30 min | none |  |
| 27E | Does self-consistent electrostatics materially change the QW states or the chi2 spectrum? | 3 | BLOCKED | Yes | 2 h - 8 h | 27D |  |
| 27F | Could numerical-domain choices be creating or moving the higher states? | 2 | READY | Yes | 2.5 h - 6 h | none | unblocked manually; solver verdict pending analysis |
| 27G | What does the paper's "one tenth of the Brillouin zone" physically correspond to? | 2 | READY | Yes | 1 h - 3 h | none |  |
| 27H | Is the radial (isotropic) in-plane assumption valid for these states and matrix elements? | 2 | READY | Yes | 30 min - 1.5 h | none | unblocked manually; solver verdict pending analysis |
| 27I | Which spectral features come specifically from the 8-band k.p treatment? | 1 | READY | Yes | 6 min - 30 min | none |  |
| 27J | Do temperature-dependent material parameters or improved linewidths explain the remaining peak shifts? | 2 | READY | Yes | 18 min - 1 h | none |  |
| 27K | Do physically meaningful continuum or quasi-bound states contribute to the high-energy features? | 3 | BLOCKED | Yes | 4 h - 12 h | 27C, 27F |  |
| 27L | Does full 2D in-plane physics materially change chi2 compared with radial integration? | 4 | BLOCKED | Yes | 8 h - 24 h | 27A, 27H |  |
| 27M | Do spin-resolved, branch-resolved or strongly mixed HH/LH/SO contributions change the Equation 2 pathways? | 0 | BLOCKED | No | 3 min - 30 min | 27B |  |
| 27N | Could excitonic or many-body effects be large enough to matter for this spectrum? | 0 | NOT RUN | No | 3 min - 18 min | none |  |
| 27O | Is the approximation r_e,hh(k) = constant adequate? | 5 | BLOCKED | No | 1 h - 2 days | 27B |  |

## Status vocabulary

| Status | Meaning |
|---|---|
| NOT RUN | no stage of this sub-demo has been executed |
| READY | preflight passed; the physics stage may be launched |
| RUNNING | a stage is in flight |
| PASS | the sub-demo's stated pass condition was met |
| FAIL | the pass condition was not met; downstream work stays blocked |
| BLOCKED | a prerequisite has not reached PASS/COMPLETE/NOT NEEDED |
| COMPLETE | the question is answered and the conclusion is recorded |
| NOT NEEDED | earlier evidence removed the reason to run this |

`BLOCKED` is derived, not stored: a sub-demo whose prerequisites are unmet
displays as BLOCKED regardless of what is recorded, so the table cannot show
a runnable sub-demo that is not actually runnable.
