# Demo 29 — solver-temperature effects in coupled quantum wells

| Section | Meaning | Current status |
|---|---|---|
| 29A1 | Original 300 K finite-k full-8-band pilot | Complete; preserved |
| 29A2 | 300 K state/matrix and optical-operator analysis | Complete for five target-path points; optical mapping unresolved |
| 29A3 | Denser 300 K validation | Prepared but **paused**; do not run now |
| 29A4 | Final 300 K full-8-band χ² | Blocked by optical/spin and sampling gates |
| **29B** | **100/300/500 K full-8-band electronic structure** | **Current acquisition priority** |
| 29C | Historical mixed-model χ² temperature control | Complete; separate model |

**Next action:** follow [WORK_COMMANDS.md](WORK_COMMANDS.md) to run only 100 K
and 500 K with the exact successful [300 K pilot deck](nextnano/inputs/29B_300K_reference_kp8.in)
apart from its temperature line. The 300 K reference run ID is
`pilotfk_20260924T194157969113Z_33224`; its executed deck SHA-256 is
`854354bb01452521279d52557c2e1ef6663cf90fa422d350b5476724981cd4c6`.
On HOME, this was checked against the original raw solver directory and metadata.
The [frozen reference record](config/29b_reference.json) also records the
solver/database and integration-grid hashes. `--check-29b` produces a
machine-readable temperature-only deck comparison on either laptop.

29B holds **electronic-structure data, not χ² spectra**. The new acquisitions
use 301 Γ→+y dispersion points through `0.10·π/a = 0.555714439232 nm⁻¹`,
6 electron and 8 hole states, and the original finite-k integration settings:
`relative_size = 0.03`, `num_points = 5`, `num_subpoints = 1`,
`symmetry = none`, `force_k0_subspace = no`. The original run produced five
complete target-path frames; the actual returned k points must again be read
from `k_points.txt`. Geometry, mesh, material, output-state, dipole/momentum,
threads, and monitoring settings are unchanged. Only solver temperature is
intended to vary. A different executable, database, deck, or k-grid fails the
29B validation and requires review.

## Output roles

| Path | Role |
|---|---|
| `nextnano_raw/demo29_300K_target_pilot_raw/pilot_target_300K_trial2/` | Original 300 K raw reference on HOME; outside Git |
| `nextnano/work_runs/29B_100K_full8/` | New original WORK solver output; retain |
| `nextnano/work_runs/29B_500K_full8/` | New original WORK solver output; retain |
| `outputs/29B_full8band_temperature/{100K,300K_reference,500K}/` | HOME state tracking and complex matrices |
| `outputs/29B_full8band_temperature/comparison/` | HOME tables and figures for 100/300/500 K |
| `outputs/29A_full8band_300K/29A2_physics_debug/` | Earlier 300 K diagnostic; preserved |
| `outputs/29C_mixed_control/` and `outputs/comparison/mixed/` | Historical mixed-model χ² control only |

The HOME comparison reports e1/e2/hh1/hh2 and transition energies, CB/HH/LH/SO
character, localization, adjacent-k and cross-temperature doublet overlaps,
position blocks, and nextnano's exported dipole/momentum tables. Weak tracking
or state reordering is **flagged**, not hidden. These finite-k envelope tables
do not supply the unresolved phase-preserving interband optical operator.
See [OPTICAL_MAPPING.md](OPTICAL_MAPPING.md). In particular, do not label the
historical LH-dominated `(3,4)` pair as hh2 in 29B.

The comparison studies the effect of **nextnano solver temperature on the
electronic structure**. It introduces no explicit thermal carrier occupation
factors. No full-8-band χ² temperature result is claimed. The historical 29C
curves still use 8-band dispersion with single-band k=0 matrices and
`M(k)=M(0)`; see [RESULTS.md](RESULTS.md).

Raw solver output, transfer ZIPs, logs, and generated plots remain outside Git.
