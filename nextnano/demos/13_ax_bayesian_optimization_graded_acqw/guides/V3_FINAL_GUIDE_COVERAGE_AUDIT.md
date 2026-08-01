# v3 guide coverage audit

**Verdict: PASS.**

## Coverage

| Artifact class | Count | Documented |
|---|---:|---|
| Figures (`plots13.PLOT_SET`) | 47 | 47 |
| Tables (`tables13.TABLE_CATALOGUE`) | 28 | 28 |
| Result metrics | 24 | 24 |
| Input parameters | 27 | 27 |

Bijection in both directions: no rendered plot lacks an entry, and no entry
describes a plot that is not rendered.

## The anti-drift mechanism

Guides are **generated** from `catalog13`, whose entries are validated against
the code that produces the artifacts. Units come from `tables13.unit_for` and are
never restated; parameter paths are resolved against real `demo.yaml` keys; CSV
links are derived from figure filenames.

`test_guides_on_disk_match_the_generator` compares every file byte-for-byte
against what the generator produces now, so a hand-edited or stale guide is a
test failure rather than a discovery.

## Terminology checks enforced by tests

- no guide names the v2 winner, the v2 experiment, or the old schema
- `pm/V` may appear only within 120 characters of a denial
- "iteration" may not appear without distinguishing MBM iterations from proposal
  attempts
- every guide mentioning the result must say t0021 is not a validated optimum
- every numbered work-laptop step must be marked SAFE or SPENDS SOLVER TIME
- no runnable Stage 5 launch command may appear

## Warning

The audit *reports* in `guides/` are deliberately excluded from the
stale-terminology scan: they must be able to name the v2 winner and quote a pm/V
label in the course of recording them as superseded or denied. Only the seven
generated beginner guides are scanned. That exclusion is itself a small risk --
an audit report could go stale without failing a test.
