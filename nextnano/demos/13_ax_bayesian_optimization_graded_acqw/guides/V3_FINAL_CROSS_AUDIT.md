# v3 final cross-audit

| Phase | Agent 1 | Agent 2 |
|---|---|---|
| 1 — baseline | commit 15ca61a, clean tree, hashes match the transferred bundle | **PASS** — counts re-derived: 23/7/16/6/10/3 |
| 2 — testing | full suite green; reanalysis with 0 solver calls and 4/4 hashes identical | **PASS** |
| 3 — stale code | 5 real items found and fixed | **PASS** |
| 4 — plots/tables | placeholders made machine-readable; 32 populated + 15 placeholders = 47 | **PASS WITH WARNINGS** |
| 5 — guides | 7 generated guides | **PASS** |
| 6 — guide/code sync | catalogue validated against code; 25 tests | **PASS** |
| 7 — bundle + Stage 5 isolation | helper implemented; isolation enforced | **PASS** |
| **8 — final physics** | — | **FAIL** |

**Overall: FAIL.** Work stopped at Phase 8 as instructed.

## What the FAIL is about

It is **not** about the plumbing. The accounting, immutability, reporting,
guides and work-laptop handoff all pass, and were re-derived independently.

It is about the **physics reporting**. The previous physics audit claimed no
physically wrong statement survived. An independent reviewer falsified that, and
I re-verified the critical findings directly against the v3 trial records:

1. **the optical sign convention was inverted on all 16 trials** — every peak is
   blue of 1550 nm and every record said `red_of_target`;
2. **the heavy-hole anticrossing gap reported the largest spacing, not the
   smallest** — hiding hole spacings of 4–7 meV against a 5 meV broadening;
3. **"thin barrier ⇒ near-degenerate doublet" is backwards** — t0021 at the
   thinnest barrier has one of the *largest* splittings (95.1 meV);
4. **`maximum_boundary_probability` is not constant** — it spans 107× and
   *caught a genuine violation at t0006 (1.91e-3)*. The earlier recommendation
   to stop modelling it would have removed a working constraint.

(1) and (2) are fixed with tests. (3) and (4) are corrected in the reports and
the earlier recommendation is withdrawn. A third code defect — the state tracker
being fed fabricated hole energies — is identified and **not fixed**.

## The contradiction that matters most

The earlier audit and the new one disagree about `maximum_boundary_probability`.
I checked: the new one is right. That metric spans 1.78e-5 → 1.91e-3 and
produced one real constraint violation. My earlier "nearly constant, NaN Sobol
indices" was drawn from the v2 campaign and carried into v3 without recomputing.
**Resolution: the recommendation is withdrawn; the constraint stays modelled.**

## The failure mode this exposes

Both surviving classes of defect are the same shape: **a claim that was true of
v2, restated for v3 without recomputation.** The stale-code audit catches stale
*strings*; nothing was catching stale *numbers*. The sign errors are different —
they had never been checked at all, because no one had compared a computed label
against the quantity it describes.

## Carried forward, in priority order

| # | Item | Blocks |
|---|---|---|
| 1 | Confirm or refute P13 (inherited 58 nm window error vs the 15 nm constraint) | every ordering in v3, including t0021 > t0022 |
| 2 | Re-track with true hole energies (P3) | any state-identity claim |
| 3 | Reorder Stage 5: state-count convergence **before** the mesh gate | Stage 5 launch |
| 4 | Rewrite Stage 5 §E — it targets a risk that does not exist (P4) | Stage 5 launch |
| 5 | Confirm P11 (grading confounded by geometry) and P10 (1 nm peak quantization) | the grading conclusion; the ranking |
| 6 | Alloy-profile verification | any realized-grading claim |

## Standing judgement

The reporting path counts, describes and plots the campaign correctly, and the
guides are generated from the code so they cannot drift silently. What is **not**
established is that any physical ordering in v3 survives its own systematic
error. Until items 1–2 are settled, t0021 should be described as *the best
design found under the current threshold*, and not compared with t0022 at all.
