# 28H — grid versus cutoff

Run `python scripts/run_numerical_audit.py` after28A/B/C. `config/numerical_audit.json` controls native strides, independent solver grids and probes. Outputs: `outputs/28H_grid_convergence/`. Fixed-endpoint301/241comparison controls the extended dataset's coarser sampling. Cumulative extended-grid curves vary cutoff on one grid; they do not certify infinite-density convergence.
