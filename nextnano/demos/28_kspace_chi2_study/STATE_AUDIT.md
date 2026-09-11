# 28I state-character and model-validity audit

The historical calculation is **not demonstrably a two-heavy-hole eight-band calculation**. Its fixed solver-state pairs are electron `(11,12)`, electron `(13,14)`, valence `(5,6)`, valence `(3,4)`. The last pair is already predominantly **light-hole**, not heavy-hole, at k=0. These labels are preserved to reproduce the historical spectrum, not silently corrected to match the paper's stated truncation.

## Evidence and outputs

Run `python scripts/run_state_audit.py`. The primary results are in `outputs/28I_state_character/`. Repeat with `--input nextnano/raw_extended --output outputs/28I_state_character/extended` for the cached 0.125 pi/a data.

- `state_character.csv`: component probabilities aggregated into CB/HH/LH/SO for each selected doublet at every **actually available** k index.
- `raw_solver_energies.csv`: every raw dispersion column at every solved k.
- `selected_pair_energies.csv`: selected raw doublet averages. These are unaligned nextnano energies, not the single-band-reanchored Eq2 inputs.
- `localization.csv`: normalized pair probability in the geometric wells, mean growth coordinate, and probability in the outer 1 nm at each edge of the finite quantum domain.
- `adjacent_pair_subspace_fidelity.csv`: mean squared principal overlap of adjacent fixed doublet subspaces when both wavefunctions exist. This handles phase changes and rotations within a degenerate pair. It does not search or relabel competing branches.
- `metadata.json`: explicit available k indices, coverage and limitations.
- `plots/28I_k0_character.png`: direct evidence of the LH-like historical h2.
- `plots/28I_electron_energies.png` and `28I_valence_energies.png`: raw selected dispersion, **not proof of adiabatic branch continuity**.

## What cannot be certified

The baseline and extended caches contain 301 dispersion samples but only k=0 composition/envelopes. Thus composition coverage is **1/301**, and there are **zero adjacent-k overlap comparisons**. No finite-k HH/LH character, physical branch tracking, or high-k localization is inferred from smooth energies. Bound versus unbound character is unresolved: finite-box eigenstates and a large well probability are not a continuum-threshold analysis.

The archived deck requests finite-k outputs, but the available archive does not contain them. It is unclear whether those outputs were not produced in this solver mode or were omitted when archiving. Work-machine output retention must be verified.

The state audit therefore marks **all high-k validity as UNRESOLVED**, not green/approved. The two-state truncation, frozen k=0 matrices, fixed solver columns and isotropic radial reduction are separate limitations. Extending a mathematically finite integral cannot repair these assumptions. Replacing the LH-like branch or adding extra states is a physics change and belongs in a separately labeled future study, not in the baseline.

## Extended dataset discovery

Actual Professional raw data was found at `demo_results/demo23/raw/kmax_y_n301_k0125` and copied into `nextnano/raw_extended/kp8`. Source provenance is recorded in `config/extended_k.json`; hashes are in each study's `raw_manifest.json`. A successful-completion marker is present. A token-level regression test confirms its deck is identical to the baseline deck except for the k endpoint. The full range is 0.69464304904 nm^-1, 0.125 pi/a, still with 301 points. Its coarser spacing than the baseline must not be mistaken for a pure physical-cutoff effect when comparing separate datasets.

No data beyond 0.125 pi/a was found in accessible repository raw results. The search did encounter inaccessible temporary Python dependency/cache folders, which are not identified raw Professional result locations. A modest 0.15 pi/a / 901-point plan is prepared, not executed; see `WORK_LAPTOP_RUN.md`.
