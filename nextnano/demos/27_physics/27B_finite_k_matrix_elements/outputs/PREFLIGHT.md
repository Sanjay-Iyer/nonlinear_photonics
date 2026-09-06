# 27B preflight

**No decks of its own.** this sub-demo delegates its solver work to another demo, which owns the decks; see the delegate block in config.yaml

## Delegated preflight

Ran: `C:\code\nonlinear_photonics\nextnano\demos\25_finite_k_matrix_element_validation\run_demo25.py --preflight`

Result: **PASS** (exit 0)

The decks, their syntax validation and their gate belong to `25_finite_k_matrix_element_validation`.
Demo 27 does not fork them.

# 27B cost statement

**Read this before launching the physics stage.** These are planning estimates.

| Item | Value |
|---|---|
| Tier | 2 |
| nextnano++ Professional required | yes |
| Decks | 1 (declared; decks belong to 25_finite_k_matrix_element_validation) |
| k points per deck | 301 |
| Total k-point solves | 301 |
| States solved/output per deck | 32 |
| Estimated wall time | 1 h - 3 h |
| Estimated output volume | 10 - 15 GB |

**Basis for the estimate.** Demo 25's README, calibrated on the Demo 23 work-laptop timing: roughly 10-30 s per k point at 32 states with full per-k envelopes. Disk dominates - Demo 23 wrote 18 MB per case with envelopes at k=0 only. The real number is measured by the 27A pilot, and Demo 25 will recommend a smaller matrix-element grid if 301 points would exceed its 12 h / 60 GB budgets. Matrix elements vary slowly with k while energies set the resonance positions, so a coarser M(k) grid interpolated onto the fine energy grid loses very little.
