# Demo 16 — ACQW renderer stress validation

Demo 16 is **not** an optimization. It answers one question:

> When Python specifies a particular ACQW geometry and grading profile, does
> nextnano++ actually construct and solve the exact physical heterostructure we
> intended?

It exists because four failure classes reached a licensed Demo 14 gate run:

| # | Failure | Why it escaped | Caught by |
|---|---|---|---|
| 1 | several materials in one `region{}` | no rendered deck had ever been parsed | Level 1 |
| 2 | GaAs background, no outer barriers — wells unconfined | the deck was syntactically valid | structural invariants |
| 3 | 7.1 / 2.9 nm **well** widths reported as grading widths | the crossing search spanned a whole well | clamped interface windows |
| 4 | nonzero solver exit not checked, masked by a later Python error | the wrapper only raised on timeout | `solver14` fatal markers |

## Commands

```bash
python nextnano/demos/16_acqw_renderer_stress_validation/run_demo16.py --preflight
```
```bash
python nextnano/demos/16_acqw_renderer_stress_validation/run_demo16.py --syntax
```

`--structure` (Level 2) and `--physics` (Level 3) need the licensed build.
`--analyze DIR` re-reads an existing run. No default launches a licensed solve.

`--parse` runs no physics and consumes no licensed computation, so `--syntax`
works on the free build too.

## The three levels

**Level 1 — syntax.** All 20 cases rendered by Demo 14's *production* renderer
and run through `nextnano++ --parse`, plus the structural invariants evaluated on
the authoritative Python `x_Al(x)`. Runs anywhere nextnano++ is installed.

**Level 2 — structure.** `--structure` plus `output_alloy_composition{}`, then
nextnano++'s realized composition compared against the Python profile on a common
grid. **Licensed only**: the free build caps at 100 grid points and a production
deck is ~1000, and it cannot execute imported profiles at all.

**Level 3 — physics.** Eight selected cases through the real solver and analysis.
Explicitly requested. No BO, no optimum claimed.

## The 20 fixed cases

A **regression fixture, not a sample**: generated once into
`validation_cases.yaml` with explicit numbers, and read from there afterwards.
Preflight fails if the generator and the file disagree, so changing the fixture
is a deliberate act (`--write-cases`).

12 deliberate boundary/corner cases, 8 seeded interior cases (**seed 1616**),
each seeded draw rejected and retried if it falls within 0.25 normalised units of
an existing case — random points that merely repeat the corners add cost, not
coverage.

## Level 1 result (home laptop, free nextnano++ 3.0.0)

**20/20 cases pass.** Six cases genuinely overlap; every linear one among them
switched to an imported profile automatically.

| Case | Profile | Render | peak x_Al | Overlap |
|---|---|---|---|---|
| 01 paper_reference | linear | `ternary_linear` | 0.5500 | no |
| 02 minimum_barrier | linear | `ternary_import` | 0.4156 | **yes** |
| 03 maximum_barrier | linear | `ternary_linear` | 0.5500 | no |
| 09 maximum_overlap_linear | linear | `ternary_import` | **0.2671** | **yes** |
| 13 seeded_01 | fermi | `ternary_import` | 0.5272 | **yes** |
| 14 seeded_02 | erf | `ternary_import` | 0.4959 | **yes** |
| 16 seeded_04 | linear | `ternary_import` | 0.3233 | **yes** |
| 17 seeded_05 | fermi | `ternary_import` | 0.5161 | **yes** |

Case 09 is the important one: two 1.4 nm grades across a 0.85 nm barrier reach
only **27% Al**, less than half nominal. No flat Al = 0.55 plateau is fabricated,
and the overlap oracle records the peak, its position, plateau non-existence and
the local Al dose.

## Why interface windows are clamped

Each interface is measured in a window of `±1.6 × requested width`, **clamped at
the midpoint to each neighbouring interface**. Without the clamp, a 1.4 nm grade
across a 0.85 nm barrier opens a window that swallows the next interface and part
of a well — which is exactly how a 7.1 nm well width was once reported as a
grading width. Isolation is therefore guaranteed by construction, and
`window_isolated_from_other_interfaces` is recorded per interface rather than
assumed.

Where two grades overlap, a single monotone transition does not exist and the
local 10–90 width is legitimately `null`. The overlap oracle describes the
barrier instead. A null is a physical statement; a window touching a neighbour
never is.

## Reuse, not reimplementation

Demo 16 imports `grading14`, `demo14.geometry_for`, `demo14.build_grading`,
`demo14.render_deck`, `solver14` and `runlog14` directly, and has no `demo.yaml`
of its own — it reads Demo 14's. A preflight check greps `demo16.py` for renderer
constructs and fails if any appear: a parallel implementation would validate the
wrong code, and the entire point is to stress the path a campaign uses.

## Deliberately-bad structures

The suite also builds structures that *must* fail: GaAs background with no outer
barriers, missing central barrier, Al fraction above the allowed maximum,
non-finite composition, and nextnano++'s real "Too many instances of
'ternary_linear'" output. A validator that accepts everything valid is not
thereby able to reject anything invalid.
