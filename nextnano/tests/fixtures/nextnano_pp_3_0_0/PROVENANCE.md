# Real nextnano++ 3.0.0 output kept as test fixtures

Every file under this directory is **genuine solver output**, not synthesised
data. It exists so the repository's parsers and physical analysis can be tested
at home against the exact file names, header text, column order, and numerical
conventions of the installed solver version — the things a hand-written fake
gets subtly wrong.

## How it was produced

- Solver: **nextnano++ 3.0.0 Free edition**, `2026_07_03` package, home laptop.
- Date: 2026-07-30.
- Database: `database_free.nnp`.

The Free edition executes only *small* simulations: at most 100 grid points,
300 K only, and only the Γ and HH bands — no strain and no k·p. The fixtures are
therefore deliberately coarse (1 nm grid, few states). They are adequate for
testing **plumbing and analysis logic** and are useless as physics: no number in
them should ever be quoted as a converged result.

Every deck here was rendered by the demo's own template and Python geometry
code, so the fixture is also a check that the generated input is one the solver
actually accepts.

## What is *not* covered

The Free edition refuses strain and every k·p model, so Demos 7 and 8 have no
real-output fixture and their parser patterns are marked `confirmed: false` in
`nextnano/config/parsers/nextnano_pp_3_0_0.yaml`. It also refuses 2D execution,
so Demo 10 has none either. Those must be confirmed on the licensed laptop.

## Directories

| directory | deck | what it exercises |
|---|---|---|
| `demo04_symmetric_dqw/` | symmetric GaAs/AlGaAs double well, one-band Γ | band edges, energy spectrum, envelopes, probabilities |
| `demo05_field_cqw/` | asymmetric coupled well with an imposed field | `potential.dat`, `electric_field.dat`, field unit and sign |
| `demo06_doped_scf/` | doped coupled well, `run{ quantum_poisson{} }` | iteration history, densities, occupations, non-convergence warning |
| `demo09_dipole/` | coupled well with dipole matrix elements | `dipole_moment_matrix_elements_*.txt`, oscillator strengths |

Each directory keeps the deck that produced it as `deck.in`, plus `summary.log`
and `job_done.txt` so completion detection can be tested too.
