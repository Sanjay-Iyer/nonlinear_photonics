# Demo 27 dependency graph

Prerequisites are enforced by `run_demo27.py`, not merely documented: a
`--physics` stage refuses to start unless every prerequisite has reached
`PASS`, `COMPLETE` or `NOT NEEDED`, and `--list` shows an unmet sub-demo as
`BLOCKED` regardless of what the status file records.

`framework/registry._validate_graph` also rejects an unknown prerequisite and
detects a cycle at load time, so the graph cannot become unrunnable by editing a
config.

## The graph

```
                          ┌──────────────────────────────────────┐
   (no prerequisite)      │              27A                     │
   ─────────────────      │   finite-k output pilot   Tier 1     │
                          └───────┬──────────────┬───────────────┘
                                  │              │
                    ┌─────────────▼───┐    ┌─────▼──────────────┐
                    │      27B        │    │       27C          │
                    │ finite-k M(k)   │    │ extended states    │
                    │    Tier 2       │    │    Tier 2          │
                    └───┬─────────┬───┘    └─────┬──────────────┘
                        │         │              │
              ┌─────────▼──┐  ┌───▼────────┐     │
              │    27M     │  │    27O     │     │
              │ multiband  │  │ Bloch r_ehh│     │
              │  Tier 0    │  │   Tier 5   │     │
              └────────────┘  └────────────┘     │
                                                 │
   ─────────────────                             │
   (no prerequisite)                             │
        27D  exact paper geometry   Tier 2       │
          └──► 27E  Schrodinger-Poisson  Tier 3  │
                                                 │
        27F  numerical convergence   Tier 2 ─────┼──► 27K  continuum states  Tier 3
                                                 │        (needs 27C AND 27F)
        27G  kmax / BZ convention    Tier 2      │
                                                 │
        27H  direction anisotropy    Tier 2 ─────┴──► 27L  full 2D k space   Tier 4
                                                          (needs 27A AND 27H)
        27I  model cross-validation  Tier 1
        27J  temperature / linewidth Tier 2
        27N  exciton feasibility     Tier 0
```

## Every edge, and why it exists

| Edge | Reason |
|---|---|
| 27A → 27B | 27B reconstructs O_nm(k), z_e,nl(k) and z_hh,ml(k). Those need state output at finite k. If 27A fails, that data does not exist, and Demo 25's production stage refuses to start rather than substituting M(k) = M(0). |
| 27A → 27C | 27C's state identities (CB/HH/LH/SO fractions, localization) are only meaningful at every k if per-k state output works. The **energies** E_n(k) come from the dispersion path and are available regardless, which is why 27C is a cheap Tier 2 rather than a repeat of 27B. |
| 27D → 27E | 27E compares a flat-band arm against a self-consistent arm. Both must sit on the geometry the campaign has settled on; running the pair on a geometry 27D is about to reject would produce a clean comparison of the wrong structure. |
| 27B → 27M | 27M decomposes 27B's harvested spinors by spin branch and band character. With no 27B harvest there is nothing to decompose. |
| 27B → 27O | 27O's cheap route derives the interband Bloch matrix element from 27B's kp8 momentum matrix elements. Without it, only the expensive external-DFT route remains. |
| 27C + 27F → 27K | 27C says whether states above the current window exist at all. 27F says whether they move with the numerical domain. A "continuum contribution" claimed without both is indistinguishable from a Dirichlet box level. |
| 27A + 27H → 27L | 27L needs finite-k output (27A) and needs a reason to exist (27H). If 27H finds no meaningful anisotropy, 27L must be recorded NOT NEEDED — it is the most expensive calculation in the campaign. |

## Deliberately independent

**27D, 27F, 27G, 27H, 27I, 27J and 27N have no prerequisites.** Each changes one
thing against the frozen Demo 23 baseline, so none of them needs another
sub-demo's answer first. That is the point of the design: a failure in one is
attributable to that one, and a blocked or failed sub-demo never stalls an
unrelated question.

In particular:

- **27D is independent of 27B.** Geometry does not need finite-k matrix elements
  to be tested, and Demo 26 ranks geometry above finite-k M(k).
- **27G is independent of everything.** Widening the cutoff needs only a frozen
  baseline structure, which exists.
- **27J onward does not block the reproduction work.** Temperature, linewidth,
  continuum, 2D, multiband, exciton and Bloch questions are all downstream of the
  main reproduction attempt and none of them gates 27A-27H.

## Evidence gates, distinct from prerequisites

Two sub-demos also carry a `run_only_if` condition in their config. It is a
scientific gate, not a scheduling one, and the runner does not enforce it —
recording the upstream sub-demo's conclusion is what closes it:

- **27K** runs only if 27C reports optically relevant candidates above the current
  window **and** 27F has not already labelled them as Dirichlet artifacts.
- **27L** runs only if 27H reports anisotropy above its stated tolerance.

If either condition fails, record the sub-demo as `NOT NEEDED`:

```bash
python run_demo27.py --demo 27L --record "NOT NEEDED" --conclusion "27H spread below tolerance"
```

`NOT NEEDED` satisfies a prerequisite, so closing a question this way does not
strand anything downstream.
