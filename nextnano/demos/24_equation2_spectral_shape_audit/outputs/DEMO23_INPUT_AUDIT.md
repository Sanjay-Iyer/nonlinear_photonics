# Demo 23 input audit

| FILE / DATASET | FOUND? | PATH | REQUIRED FOR WHICH DEMO 24 TEST? | QUALITY / LIMITATION |
|---|---|---|---|---|
| all seven Professional case directories | YES | C:\code\nonlinear_photonics\demo_results\demo23\raw | baseline, convergence, isotropy | seven of seven expected cases |
| all seven Demo 23 input decks | YES | C:\code\nonlinear_photonics\nextnano\demos\23_k_resolved_dispersion_validation\inputs | reproducibility | repository copies; run-local copies were not included |
| completion markers | YES | C:\code\nonlinear_photonics\demo_results\demo23\raw | input validity | one marker in every case |
| tracked kp8 E(k) and explicit vectors | YES | C:\code\nonlinear_photonics\demo_results\demo23\raw | 23D, resonance, grid/kmax | complete combined dispersion tables |
| k=0 spinor composition | YES | C:\code\nonlinear_photonics\demo_results\demo23\raw | state assignment | k=0 only; no finite-k tracking score |
| finite-k spinors/envelopes | NO | C:\code\nonlinear_photonics\demo_results\demo23\raw | finite-k M(k), state mixing | REQUIRES_NEW_PROFESSIONAL_DATA |
| A/B/C/D complex spectra | YES | C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra | baseline and comparisons | regenerated from raw; raw tree untouched |
| 16 signed pathways | YES | C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables | pathway audit | full-wavelength terms recomputed by Demo 24 |
| k-resolved integrand | YES | recomputed in memory from E(k) and frozen M(0) | cross-k cancellation | available under the validated M(k)=M(0) assumption |
| convergence outputs | YES | C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables | k-grid/kmax | regenerated from the copied raw cases |
| isotropy output | YES | C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables | radial integration audit | one alternate direction; not a full 2D integral |
| resolved configuration | YES | C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\resolved_configuration.json | frozen physics audit | regenerated |
| solver metadata | YES | C:\code\nonlinear_photonics\demo_results\demo23\raw | provenance | per-case metadata present; top-level invocation JSON absent |
