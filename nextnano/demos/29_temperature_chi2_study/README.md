# Demo 29 — solver temperature and second-order susceptibility

| Section | Purpose | Status |
|---|---|---|
| **29A1** | Initial finite-k 300 K pilot | Complete diagnostic; preserved |
| **29A2** | 300 K state, matrix, sampling and optical physics analysis | Complete for existing five points; optical gate unresolved |
| **29A3** | Denser 300 K finite-k validation | **Next WORK run; not yet executed** |
| **29A4** | Final 300 K full-8-band χ² baseline | Blocked by optical/spin and sampling gates |
| **29B** | Full-8-band 100/300/500 K study | Waiting for 29A4; no 100/500 K solve requested |
| **29C** | Historical mixed-model 100/300/500 K control | Complete; separate from full-8-band model |

**Next action:** follow [WORK_COMMANDS.md](WORK_COMMANDS.md) for the 29A3
300 K run and two separate ZIPs. The [results](RESULTS.md) and
[optical mapping](OPTICAL_MAPPING.md) explain the measured limits of the
existing data. No full-8-band χ² spectrum has been produced or claimed.

## Fixed physics and numerical settings

The 8-band dispersion remains Γ→+y, 301 points through
`0.10·π/a = 0.555714439232 nm⁻¹` for `a = 0.565325 nm`. The same graded
GaAs/AlGaAs geometry, mesh, 6-electron/8-hole candidate pool, 5 meV
broadening and historical Equation 2 engine remain in place. 29A3 changes
only **state-export sampling**, using `k_integration{ relative_size = 0.036,
num_points = 11, num_subpoints = 1, symmetry = none,
force_k0_subspace = no }` rather than 29A1's `0.03, 5` settings. The actual
state-frame count and k coordinates must be read from `k_points.txt`; 11 is
not a promise of 11 on-path frames or an invented completion percentage.

29A3 was chosen because the five-point hh1–hh2 matrix is strongly
nonmonotonic, its leave-one-out interpolation error exceeds 100%, and the
first hh2 tracking step has overlap 0.410. It is a **validation solve**,
not a production χ² result. If its actual grid does not cover at least 90%
of the target interval with eight complete on-path frames, the runner and
packer warn/refuse and the debug ZIP is the handoff.

## Output and input roles

| Path | Contents | Role |
|---|---|---|
| `outputs/29A_full8band_baseline/target_pilot_trial2/` | Preserved earlier five-point matrix analysis | 29A1 diagnostic; existing path retained |
| `outputs/29A_full8band_300K/29A2_physics_debug/` | Tracking CSV, complex matrix blocks, interpolation report | 29A2 diagnostic |
| `outputs/29A_full8band_300K/29A3_dense_validation/` | Future returned-run analysis | 29A3 diagnostic |
| `outputs/29A_full8band_300K/29A4_final_baseline/` | Future full-8-band χ² and provenance | Empty until every gate passes |
| `outputs/29B_full8band_temperature/` | Future 100/300/500 K primary comparison | Inactive |
| `outputs/29C_mixed_control/{100K,300K,500K}/` | Completed historical same-temperature mixed spectra | Reference control; original paths preserved |
| `outputs/comparison/mixed/` | Existing 29C plots and table | Reference control; original path preserved |
| `nextnano_raw/demo29_300K_target_pilot_raw/` | Local 29A1 Professional raw | Outside Git; never stage |

The historical 29C method uses same-temperature 8-band dispersion and
single-band k=0 anchors/matrices, with `M(k)=M(0)`. Its old `(3,4)` valence
pair is LH dominated. The new 29A states at k=0 are e1 `(11,12)`, e2
`(13,14)`, hh1 `(5,6)`, hh2 `(1,2)`. Do not reinterpret the 29C curves as
full 8-band results.

## Scientific gates

29A4 requires reliable doublet tracking through mixing/crossings, sufficient
k sampling or a validated interpolation, a phase-preserving 8-band interband
optical operator in the saved basis, a resolved spin convention, and a
prefactor that accounts for `r_e,hh = 0.751 nm` exactly once. The nextnano
growth dipole table validates same-band envelope position integrals; its
in-plane envelope momentum and intensity-only optical outputs do not provide
the missing coherent interband operator. `config/optical_operator.json`
therefore remains `UNRESOLVED`, and full-8-band χ² software must fail closed.

The temperature comparison is primarily a study of the effect of the
**nextnano solver temperature on electronic structure and resulting χ²**.
The current Equation 2 engine has no explicit finite-temperature carrier
occupation factors. No temperature-specific shortcut is planned.

## HOME commands (no licensed solve)

Use the HOME `NMIP` Python, from this Demo 29 directory:

```powershell
& 'C:\Users\iyer95\miniconda3\envs\NMIP\python.exe' scripts\run_nextnano.py --check
& 'C:\Users\iyer95\miniconda3\envs\NMIP\python.exe' scripts\analyze_pilot.py --input C:\code\nonlinear_photonics\nextnano_raw\demo29_300K_target_pilot_raw\pilot_target_300K_trial2 --output outputs\29A_full8band_300K\29A2_physics_debug
& 'C:\Users\iyer95\miniconda3\envs\NMIP\python.exe' scripts\analyze_sampling.py --analysis outputs\29A_full8band_300K\29A2_physics_debug --output outputs\29A_full8band_300K\29A2_physics_debug\sampling.json
```

The analysis command refuses to overwrite an existing output; the existing
29A2 result has already been generated on HOME. For the returned 29A3 ZIP,
use the exact unpack and analysis commands in [WORK_COMMANDS.md](WORK_COMMANDS.md).
Raw solver output and transfer archives remain outside Git.
