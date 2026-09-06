# Demo 27 — Professional physics campaign

**Demo 27 is not one simulation.** It is a staged campaign of fifteen small,
independent sub-demos, each answering one physics question about the remaining
disagreement between this project's Equation 2 spectrum and Ramesh et al.
Figure 2d.

The governing rule:

> **COLLECT BROADLY. ANALYZE NARROWLY. RUN ONE PHYSICS QUESTION AT A TIME.**

Never answer five scientific questions with one uncontrolled simulation. Each
sub-demo has **one question, one controlled change, one clear conclusion**. But
when the expensive solver is already running, save rich raw output, so that later
analyses need no second Professional run.

You must select which sub-demo to run. There is no command that launches every
tier, and `--all-physics` is refused by name before argument parsing.

---

## Start here

```bash
python nextnano/demos/27_physics/run_demo27.py --list
```

That prints every sub-demo, its tier, its estimated runtime, its prerequisites
and whether it is runnable now. Then run one sub-demo's preflight, read its cost
statement, and only then decide whether to spend the solver time.

## Commands

| Command | Solver? | What it does |
|---|---|---|
| `--list` | no | every sub-demo, tier, cost, status, prerequisites, what is runnable |
| `--status` | no | regenerate and print `MASTER_STATUS.md` |
| `--reuse-audit` | no | what Demo 27 takes from Demos 23-26, and whether it still matches |
| `--demo X --preflight` | `--parse` only | resolve config, generate decks, validate grammar, state the cost |
| `--demo X --physics --yes` | **yes** | run that sub-demo's Professional calculation |
| `--demo X --analyze` | no | post-process that sub-demo; refuses if the data is not there |
| `--demo X --record PASS --conclusion "..."` | no | record the outcome in the status file |
| `--tests` | no | the Demo 27 test suite |

One stage per run. `--preflight --physics` together is refused: the two have
different costs and different failure modes.

`--physics` prints the cost statement and stops unless you add `--yes`. That is
deliberate — the cheapest sub-demo is twenty minutes and the most expensive is a
day.

## What each stage guarantees

**Preflight** is the only stage that touches nextnano++ without being a physics
run, and it does so with `--parse`, which validates grammar and exits. It works
on a Free build and on any machine. It writes, per sub-demo:

- `outputs/RESOLVED_CONFIG.json` — the fully resolved configuration
- `outputs/DECK_MANIFEST.csv` — every generated deck and what it changed
- `outputs/CONTROLLED_CHANGE_DIFF.md` — the line-by-line diff against the baseline
- `outputs/DECK_SYNTAX_VALIDATION.csv` — the `--parse` result per deck
- `outputs/COST_STATEMENT.md` — tier, decks, k points, states, runtime, volume

**Physics** runs the solver and writes `outputs/PROFESSIONAL_RUN_MANIFEST.json`:
the deck's SHA-256, the argv, the machine, the harvest requested, the controlled
changes, the wall time and the files that actually appeared. A physics stage that
runs the solver and leaves no manifest is a bug, and a test enforces it.

**Analyze** never launches a solver, and never fabricates raw physics. If the
Professional output is not on disk, it says so and stops. There is no code path
that substitutes a placeholder, an extrapolation or a k=0 value for missing
finite-k data.

## The one controlled change, enforced

Every sub-demo deck is built by applying its declared overrides to one frozen
baseline: the Demo 23 production structure, loaded through Demo 23's own config
loader so geometry, mesh and the Brillouin-zone convention cannot drift between
the two demos.

`framework/registry.resolve` then refuses to build a deck that changes a physics
field the sub-demo did not declare in `controlled_change.fields`, and refuses a
deck that changes more fields than `controlled_change.max_fields_per_deck`
allows. So the campaign rule is not a convention in a document — it fails the
run.

Where several fields are physically inseparable, the limit is set above one and
the config says why. Raising the number of states written requires raising the
number solved. Widening the k cutoff at fixed spacing requires more k points, and
holding the count fixed instead would confound a cutoff effect with a sampling
effect.

## The data-harvest rule

Whenever the Professional solver is already solving a deck, Demo 27 requests the
broad harvest defined once in `demo27_config.yaml`: all eigenenergies, envelopes,
kp8 spinors, CB/HH/LH/SO character, probabilities, transition energies, dipole
and momentum matrix elements, oscillator strengths, band edges, alloy
composition, k vectors, dispersions and masses — plus the electrostatic potential
and strain **only where the deck already computes them**.

The rule has a second half that matters as much as the first: **no expensive new
physics is enabled merely because an output would be interesting.** The harvest
costs disk, not solver time.

27M is what the rule buys. It was planned as a Tier 4 sub-demo needing its own
decks; because 27B's harvest already contains the full spinors and the
polarization-resolved matrix elements at every k, its first pass is Tier 0
post-processing with no solver time at all.

## Reuse before recompute

Demo 27 reads Demos 23-26 and never writes to them. `--reuse-audit` fingerprints
every artifact it depends on and reports `UNCHANGED` / `CHANGED` / `MISSING`, so
a comparison against an older result cannot silently be made against a different
older result.

Two consequences are already in the configs:

- **27A and 27B do not implement anything.** Demo 25 is the finite-k output pilot
  and the finite-k production run, deck for deck, with a filesystem-based gate
  that refuses production until the pilot passes. 27A and 27B *delegate* to it
  and record exactly what they ran. Forking it would create a second answer to
  the same question.
- **Six sub-demos reuse Demo 23's production run as their control arm.** 27D's
  graded arm, 27F's numerical control, 27G's 0.1 π/a arm, 27H's [010] arm, 27I's
  kp8 arm and 27J's 300 K arm are all `demo_results/demo23/raw/production_y_n301_k0100`,
  which is that exact structure and solver configuration. 27E is the deliberate
  exception: it regenerates its own flat-band arm so both of its arms move
  together if 27D changes the geometry decision.

## Tiers

| Tier | Meaning | Sub-demos |
|---:|---|---|
| 0 | capture / post-processing only | 27M, 27N |
| 1 | short pilot — minutes to ~1 hour | 27A, 27I |
| 2 | medium targeted Professional run — ~1-4 h | 27C, 27D, 27F, 27G, 27H, 27J, and 27B |
| 3 | large — hours to ~a day | 27E, 27K |
| 4 | very large — potentially day-scale | 27L |
| 5 | advanced / external physics | 27O |

Tiers are assigned by **measured burden**, not by plan. Where the burden landed
in a different tier than originally planned, the config records both
(`tier_planned`) and says why in `tier_note`. Three did: 27H and 27I came down
because their control arms already exist, and 27M came down to Tier 0 because
27B's harvest covers it.

## Where things live

```
27_physics/
├── README.md                     this file
├── PHYSICS_ROADMAP.md            what each sub-demo is for, and the evidence behind the order
├── DEMO27_DEPENDENCY_GRAPH.md    the prerequisite graph and why each edge exists
├── MASTER_STATUS.md              generated from MASTER_STATUS.json; never hand-edited
├── REUSE_AUDIT.md                generated by --reuse-audit
├── demo27_config.yaml            shared: inheritance, tiers, harvest, execution policy
├── run_demo27.py                 the only entry point
├── framework/                    shared machinery; no physics questions live here
└── 27A.../ ... 27O.../           one directory per sub-demo: config.yaml, README.md,
                                  inputs/ (generated decks), outputs/ (reports)
```

Raw solver output goes to `demo_results/demo27/<sub-demo>/raw/`, outside the
repository tree, like every other demo here.

## Tests

```bash
python nextnano/demos/27_physics/run_demo27.py --tests
```

They validate the machinery and the fail-loud contracts, not physics
conclusions — the Professional data that would settle those does not exist yet.
Specifically: that no "run all physics" path exists, that sub-demos are
independent, that prerequisites are enforced, that raw outputs are never
fabricated, that a missing Professional executable fails loudly, that state
output is only counted when it can be tied to a k value, that Demos 23/24/26 are
untouched, that analysis stages never invoke nextnano, that every Professional
invocation writes a manifest, that every sub-demo has a resolvable config, and
that the status file round-trips.

## Machine

Physics stages need nextnano++ **Professional** (the work laptop). The home
laptop's Free 3.0.0 build caps at 100 grid points and cannot run these decks; the
runner detects that by executable and license name and refuses before queuing
anything. Preflight, analysis, status and the reuse audit all work anywhere.

Per-machine paths live only in gitignored `nextnano/config/paths.local.yaml`.

Raw output is gitignored (`demo_results/demo27/**/raw/`), because 27B alone is
budgeted at 10-15 GB. The curated hand-off files stay tracked, exactly as they do
for the earlier demos.

## Related documents

- `PHYSICS_ROADMAP.md` — what each sub-demo is for and why the order is what it is
- `DEMO27_DEPENDENCY_GRAPH.md` — every prerequisite edge and its justification
- `docs/equation_2_from_paper/Nextnano_Professional_Physics_Roadmap.md` — the
  category-by-category physics survey this campaign implements
- `docs/equation_2_from_paper/Nextnano_Pro_Physics_Capture_Reference.md` — what is
  worth saving while a Professional run is already happening; the `harvest:` block
  is its implementation
