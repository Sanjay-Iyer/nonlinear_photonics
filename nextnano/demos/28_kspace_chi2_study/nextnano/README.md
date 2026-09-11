# nextnano inputs and actual cached output

`inputs/kp8_dispersion.in` specifies the historical 1D8-band calculation: GaAs substrate, Al0.55Ga0.45As barriers,300K, total30nm, wells [9.1,16.2] and[18,20.9]nm,1nm linear interface grading, quantum interval[7.1,22.9]nm, Dirichlet boundaries, six electron/eight hole solutions. The growth axis is deck x, along[100]. Dispersion runs Gamma-to-y,301nodes,0–0.555714439232nm^-1. `no_density=yes` and `run{quantum{}}` do not request Poisson or dynamical carrier populations.

`inputs/singleband_case04_graded.in` supplies the historical single-band anchors and envelopes used for O,ze,zh. The optical baseline is therefore mixed-model, not pure8-band finite-k matrix physics.

`raw_results/kp8/` and `raw_results/singleband_case04_graded/` retain direct Professional output. Inspect `simulation_info.txt` and archived `.in` files. The main raw pattern matches consumed by `chi2/parse_nextnano.py` are:

- `dispersion_*.dat` plus sibling `kVectors_*.dat`: explicit k values and all14energy columns.
- `kp8/energy_spectrum_k00000.dat`: k=0check against dispersion.
- `spinor_composition_k00000_CbHhLhSo.dat`: state character at k=0.
- `Gamma/energy_spectrum_k00000.dat`, `HH/energy_spectrum_k00000.dat`: single-band anchors.
- `Gamma/envelopes_k00000.dat`, `HH/envelopes_k00000.dat`: single-band wavefunctions.

Full nested file paths and hashes are in study `raw_manifest.json` files. Parser searches are restricted to the explicit dataset root and require uniqueness.

`raw_extended/` contains a separate301node run to0.69464304904nm^-1 (0.125pi/a); its spacing is0.00231547683013nm^-1, versus baseline0.00185238146411nm^-1. It includes full dispersion but only k=0spinor/composition data in this archive. `raw_results/grid_n101/` and `grid_n201/` are independent same-endpoint solver runs for numerical comparisons.

`new_results/` contains optional generated preflight artifacts, not a new successful solve. A work-laptop plan is in `outputs/28C_extended_k/work_laptop/`. No Professional executable/license/database is bundled. No licensed run was executed at home. See `WORK_LAPTOP_RUN.md` before attempting work-machine execution or interpreting larger k.
