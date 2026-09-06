# 27A preflight

**No decks of its own.** this sub-demo delegates its solver work to another demo, which owns the decks; see the delegate block in config.yaml

## Delegated preflight

Ran: `C:\code\nonlinear_photonics\nextnano\demos\25_finite_k_matrix_element_validation\run_demo25.py --preflight`

Result: **PASS** (exit 0)

The decks, their syntax validation and their gate belong to `25_finite_k_matrix_element_validation`.
Demo 27 does not fork them.

# 27A cost statement

**Read this before launching the physics stage.** These are planning estimates.

| Item | Value |
|---|---|
| Tier | 1 |
| nextnano++ Professional required | yes |
| Decks | 0 |
| k points per deck | n/a |
| Total k-point solves | 0 |
| States solved/output per deck | n/a |
| Estimated wall time | 5 min - 21 min |
| Estimated output volume | 0.2 - 2 GB |

**Basis for the estimate.** Demo 23 solved 301 dispersion k points for 14 states in 10 min 20 s on the work laptop. The pilot is 6 decks x 4 k points but with 32 states and full envelope output at every k, so it is dominated by output volume, not by the eigenvalue problem. Demo 25's own pilot_audit then measures seconds-per-k and bytes-per-k for real and sizes 27B from the measurement rather than from this estimate.
