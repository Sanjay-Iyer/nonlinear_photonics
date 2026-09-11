# Work-laptop continuation: extended k and missing state evidence

28C already runs real cached Professional data up to **0.125 pi/a = 0.69464304904 nm^-1**. No licensed solve was performed on the home laptop. This extends the historical numerical model, not its physical validity: its second valence pair is LH dominated and the shipped finite-k spinors are missing.

## One exact work command

From the Demo 28 directory, with `NEXTNANO_EXE`, `NEXTNANO_DATABASE`, and `NEXTNANO_LICENSE` already configured to valid Professional installation paths:

```powershell
python scripts/run_nextnano.py --run --config outputs/28C_extended_k/work_laptop/runner.json --jobs all --output nextnano/extended_work_results
```

The runner refuses to overwrite an existing result folder. Choose a fresh output directory for each actual solve. The command runs the eight-band deck and the local single-band anchor deck; it does not import prior demos. Executable/license paths are machine-specific and are intentionally not embedded here.

## What is prepared and why

- Config: `outputs/28C_extended_k/work_laptop/runner.json`.
- Human-inspectable eight-band deck: `outputs/28C_extended_k/work_laptop/kp8_extended.in`.
- Static preflight: `outputs/28C_extended_k/work_laptop/preflight/preflight_manifest.json`.
- Candidate endpoint: **0.15 pi/a**, approximately **0.833571658848 nm^-1**, 901 native points. This modest next increment is provisional, not a claim that eight-band k.p remains valid there. It is denser than either historical 301-point run.
- Geometry, material, grading, state counts and boundary conditions are unchanged. Full finite-k spinors, composition, dipoles and momenta are requested by the existing deck generator.
- Home preflight uses `--no-parse`: static checks PASS; parser grammar and licensed execution are **not** claimed verified. Actual work-machine grammar checks run before the licensed solve when a parser is available.

Regenerate the plan after editing `future_candidate_max_pi_over_a` or `future_candidate_k_points` in `config/extended_k.json`:

```powershell
python studies/28C_extended_k/prepare_work_laptop.py
```

## Before interpreting any new high-k susceptibility

1. Check completion/logs and the deck actually used. Inspect whether finite-k spinor and envelope files were retained, not only the k=0 files. The old deck already requested `all_k_points=yes`, but the available archive contains only k=0 wavefunctions: a request in the input is not evidence of saved output.
2. Run the state audit first:

   ```powershell
   python scripts/run_state_audit.py --input nextnano/extended_work_results --output outputs/28I_state_character/work_extended
   ```

3. Inspect composition coverage, fixed-doublet subspace overlaps, energies and localization. The overlap test checks the selected doublet subspace; it is NOT automatic branch tracking against every competing state. Strong mixing/poor overlap requires a separate state-selection decision. Do not silently replace the historical LH-like pair with a HH pair.
4. Only after a scientific review, add cutoffs within the solved endpoint to `config/extended_k.json`, and run:

   ```powershell
   python studies/28C_extended_k/run.py --input nextnano/extended_work_results --output outputs/28C_extended_k/work_extended
   ```

The downstream numerical diagnostic accepts the new raw root without redesign. It remains explicitly labeled a fixed-column historical model; there is no automatic physical-validity approval. Compare nested cutoffs on the same native grid; compare different grid densities separately in 28H.

## Geometry convention

Runtime/storage cannot be reliably estimated from the retained archives. The901nodes are three times the old301count, but performance and full-k envelope retention can change scaling substantially. No invented duration or disk-size estimate is provided; verify available resources on the work machine.

`fraction` means `kmax/(pi/a)` with `a=0.565325 nm`. The raw solve is one crystallographic Gamma-to-y path. Python treats that path as representative of all in-plane angles and applies `g_s*k*dk/(2*pi)`, equivalent to an isotropic radial-disk integral. It is not a solved two-dimensional square or the whole Brillouin zone. The paper's use of “0.1 BZ” does not, by itself, establish this geometry or conversion.
