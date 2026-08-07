# Demo 16 — ACQW renderer stress validation (scoped, NOT built)

Demo 16 answers one question: *when Python specifies an ACQW geometry and grading
profile, does nextnano++ construct and solve the structure we intended?*

It exists because three failure classes got through Demo 14's 900-test suite and
into a licensed run. This file records the design so the next session starts from
decisions rather than rediscovery. **None of it is implemented.**

## The four failure classes it must prevent

| # | Failure | How it escaped | Demo 16 level that catches it |
|---|---|---|---|
| 1 | Multiple materials in one `region{}` | nothing ever ran a rendered deck through `--parse` | Level 1 |
| 2 | GaAs background, no outer barriers — wells unconfined | deck was syntactically valid; only the composition reveals it | Level 2 |
| 3 | 7.1 / 2.9 nm well widths reported as *grading* widths | crossing search window spanned a whole well | Level 2 + dedicated tests |
| 4 | Nonzero solver exit not checked, masked by a later Python error | wrapper only raised on timeout | Level 1/3 wrapper assertions |

All four are now fixed in Demo 14; Demo 16 is what keeps them fixed.

## Three levels

**Level 1 — syntax.** All 20 cases rendered by the *production* Demo 14 renderer
and run through `nextnano++ --parse`. No licence needed; the free build validates
the full input grammar. This is fully runnable on the home laptop.

**Level 2 — structure.** `--structure` plus `output_alloy_composition{}`, then
compare nextnano++'s realized `x_Al(x)` against the authoritative Python profile
on a common grid. **Needs the licensed build**: the free one caps at 100 grid
points and a production deck is ~1000. Invariants: both outer barriers present,
both wells present and GaAs, central barrier present, all four interfaces
represented, composition within `[0, x_max]`, no reliance on quantum-region
Dirichlet walls for confinement.

**Level 3 — physics.** ~8 representative cases through the real solver and
analysis. Explicitly requested, never the default. No BO, no optimum claimed.

## The 20 fixed cases

12 deliberate + 8 seeded-random (seed **1616**), resolved values stored in
`validation_cases.yaml` and never regenerated per run.

| # | Case | Key parameters | Profile |
|---|---|---|---|
| 01 | paper reference | 7.1 / 1.8 / 2.9 nm → s = 0.42 | linear |
| 02 | minimum barrier | barrier 0.85 | linear |
| 03 | maximum barrier | barrier 2.50 | linear |
| 04 | minimum left grade | left 0.40 | linear |
| 05 | maximum left grade | left 1.40 | linear |
| 06 | minimum right grade | right 0.40 | linear |
| 07 | maximum right grade | right 1.40 | linear |
| 08 | both grades minimum | 0.40 / 0.40 | linear |
| 09 | **max overlap** | 1.40 / 1.40, barrier 0.85 | linear |
| 10 | low asymmetry | s = 0.30 | linear |
| 11 | high asymmetry | s = 0.55 | linear |
| 12 | asymmetric grades | 0.40 / 1.40 | linear |
| 13–20 | seeded interior, seed 1616, all of fermi/erf/cosine represented, at least one thin-barrier + wide-grade overlap | | mixed |

Case 09 is the most important: it must **not** fabricate a flat Al=0.55 plateau.
With the current renderer it triggers the linear→import fallback, because a
`linear → constant → linear` region template would let one ramp override the
other. Case 09 should assert the fallback fired *and* that the realized
composition matches the intended profile.

## Reuse, not reimplementation

Demo 16 imports Demo 14's `grading14`, `demo14.geometry_for`,
`demo14.build_grading`, `demo14.render_deck`, `solver14`, `adapter14` and
`runlog14` directly. A preflight check should assert no second renderer exists —
the entire point is to stress the production path, and a parallel implementation
would validate the wrong code.

## The 7.1 / 2.9 regression guard

`grading14.measure_structure` now measures between the two **well floors**, not
across the active region, so a crossing search cannot walk from the central
interface out to an outer one. Demo 16 must assert directly that a 7.1 nm well
never yields a 7.1 nm grading width, and likewise 2.9 nm — those exact numbers,
because those are what the bug produced.

## Tolerances

Not chosen up front. Characterize the numerical floor first on a known-good
non-overlapping linear case (where Python and nextnano++ should agree to
interpolation error), then set the tolerance a small multiple above that floor.
Picking a loose tolerance so the tests pass would defeat the demo.

## Commands

```
run_demo16.py --preflight    # solver-free self-test
run_demo16.py --syntax       # Level 1, all 20, --parse only
run_demo16.py --structure    # Level 2, licensed
run_demo16.py --validate     # Levels 1 + 2
run_demo16.py --physics      # Level 3, explicit, ~8 cases
run_demo16.py --analyze DIR  # re-analyse without solving
```

Default must never launch a licensed solve.

## Output root

`nextnano/results/demo_runs/16_acqw_renderer_stress_validation/<run_id>/` —
reached via `machine.results_root` **without** appending `demo_runs`, which is
what produced the `demo_runs/demo_runs` duplication. A regression test already
guards this pattern for Demo 14 and should be extended to Demo 16.
