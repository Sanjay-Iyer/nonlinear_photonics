# Demo 20 - Interface Grading with a Configurable $(2\pi)^2$ k-Space Normalization

## What this demo is

Demo 19's controlled interface-grading study, reorganized into numbered pipeline stages, with the in-plane k-space measure exposed as an explicit switchable convention. The structure, the 13 cases, the grading mathematics, the state count, the broadening, $N_z$, $r_{e,hh}$, $k_{max}$ and the wavelength grid are all unchanged from Demo 19.

## The normalization finding

The 1/(2*pi)^2 normalization is ALREADY PRESENT in the original Demo 19 calculation, in its reduced isotropic form 1/(2*pi) with the compensating 2*pi already cancelled by the angular integral. Multiplying by (2*pi)^2 therefore REMOVES an existing denominator rather than restoring a missing factor: it switches the measure from (1/A) sum_k -> int d^2k/(2*pi)^2 to sum_k -> g_s * int d^2k. That is an ALTERNATIVE CONVENTION under test, not a correction.

- Original convention: `(1/A) sum_k -> integral d^2k/(2*pi)^2 = (1/(2*pi)) integral k dk  [Demo 19 original]`
- Explicit $1/(2\pi)^2$ present in Demo 19: **YES** (s06_chi2.k_grid: 1/(2*pi)^2 * (2*pi from the angular integral) = radial_measure = k/(2*pi))
- Scaling factor: $(2\pi)^2$ = 39.47841760436
- Scaling enabled in this run: **YES**

## Results at 1550 nm

| Case | Profile | raw (pm/V) | scaled (pm/V) | reported (pm/V) | ratio | peak raw (nm) | peak scaled (nm) |
|---|---|---:|---:|---:|---:|---:|---:|
| 00 Abrupt reference | abrupt | 31.036 | 1225.3 | 1225.3 | 39.478418 | 1517.0 | 1517.0 |
| 01 Linear 0.2 nm | linear | 29.374 | 1159.6 | 1159.6 | 39.478418 | 1515.0 | 1515.0 |
| 02 Linear 0.4 nm | linear | 26.443 | 1043.9 | 1043.9 | 39.478418 | 1513.0 | 1513.0 |
| 03 Linear 0.7 nm | linear | 21.682 | 855.96 | 855.96 | 39.478418 | 1508.0 | 1508.0 |
| 04 Linear 1.0 nm | linear | 18.048 | 712.49 | 712.49 | 39.478418 | 1502.0 | 1502.0 |
| 05 Linear 1.4 nm | linear | 15.232 | 601.34 | 601.34 | 39.478418 | 1493.0 | 1493.0 |
| 06 Asymmetric inner grading A | linear | 22.746 | 897.99 | 897.99 | 39.478418 | 1512.0 | 1512.0 |
| 07 Asymmetric inner grading B | linear | 31.033 | 1225.1 | 1225.1 | 39.478418 | 1514.0 | 1514.0 |
| 08 Inner interfaces graded only | linear | 24.646 | 972.99 | 972.99 | 39.478418 | 1512.0 | 1512.0 |
| 09 Outer interfaces graded only | linear | 26.15 | 1032.4 | 1032.4 | 39.478418 | 1513.0 | 1513.0 |
| 10 Fermi-like 0.7 nm | fermi | 26.254 | 1036.5 | 1036.5 | 39.478418 | 1513.0 | 1513.0 |
| 11 erf 0.7 nm | erf | 24.492 | 966.91 | 966.91 | 39.478418 | 1511.0 | 1511.0 |
| 12 Cosine 0.7 nm | cosine | 24.282 | 958.62 | 958.62 | 39.478418 | 1511.0 | 1511.0 |

## Comparison with the published target

- Published target: **~2500 pm/V**
- Reference case: 00 Abrupt reference
- Demo 20, Demo 19 convention: 31.036 pm/V (ratio 0.01241, 98.76% from target)
- Demo 20, $(2\pi)^2$-scaled: 1225.3 pm/V (ratio 0.4901, 50.99% from target)
- Residual factor still missing after scaling: **2.04x**

Neither convention reproduces the published target. The (2*pi)^2 convention closes most of the gap but is not a fit and is not evidence that the scaled convention is the paper's. The residual factor is recorded as remaining_factor_after_scaling.

### Residual lead (not a result)

- Remaining factor: 2.04x
- The $N_z$ counting ambiguity is a factor of exactly 2 (`period_density` vs `well_density`)
- $(2\pi)^2$-scaled AND `well_density`: 2450.5 pm/V, ratio 0.9802

The residual is close to the N_z counting ambiguity, which is a factor of exactly 2. This is recorded as a lead only: two independent convention changes that happen to multiply to roughly the published number is not evidence that either is the paper's choice. Confirming it requires the paper's own k-space measure and its own N_z definition, neither of which this checkout can establish.

## Validation status

| Level | Validated | Evidence |
|---|---|---|
| code_validated | yes | tests/test_demo20.py executed locally; includes exact reproduction of Demo 19's chi2 from its own tabulated matrix elements. |
| numerics_validated | yes | k-measure agrees with its closed form, the k grid is converged at the production point count, and the two conventions differ by exactly (2*pi)^2 pointwise. |
| solver_validated | **no** | NO licensed solve ran in this execution; the quantum data was read from a previous licensed run's table. |
| physical_model_validated | **no** | physical_valid is False; the inherited Demo 11/14 physical QC did not pass. The specific failed sub-check needs the raw licensed run and the proprietary material database, neither of which is present in this checkout. |
| paper_reproduction_validated | **no** | no convention reproduces the published target; closest ratio to target is 0.4901. Agreement would in any case require the paper's own k-space measure to be confirmed, which this checkout cannot do. |

## Solver and physical status

- Cases: 13
- solver_pass: 13/13
- physical_valid: 0/13

- Recorded reason: Demo 11/14 physical QC did not pass

Every reported spectrum comes from a solver run that returned successfully but did NOT pass the inherited Demo 11/14 physical QC. Treat the numbers as a controlled comparison between grading cases, not as validated absolute physics.

## Main takeaway

Enabling the $(2\pi)^2$ factor does **not** prove that the scaled convention is physically correct. Demo 19 already contains the $1/(2\pi)^2$ normalization, so the switch removes an existing denominator rather than supplying a missing one. It remains an experimental normalization comparison until the source paper's own $k$-space measure is verified.
