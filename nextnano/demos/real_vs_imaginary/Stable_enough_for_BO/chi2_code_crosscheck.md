# Independent cross-check of `chi2_replication_findings.md`

**Status:** Your §4.3 and §4.4 are corroborated by an independent calculation. Your
§4.1/§4.2 amplitude decomposition is better than anything we had and we adopt it. Your
§4.4 degeneracy note corrects an overclaim of ours. We add one new test that bears
directly on the Methods' saturation claim.

**We hold no code or data from the paper — only the manuscript**, the same position you
describe in your closing paragraph. An earlier draft of this memo claimed otherwise and
its §4 and §6 have been withdrawn; see §8 for what that file actually is and why it is
still worth a look.

Companion material: `nextnano/demos/26_real_chi2_paper_comparison/outputs/CUTOFF_ARTIFACT_FINDING/`.

---

## 1. Summary

We reached your §4.3 and §4.4 conclusions independently — from frozen Demo 19/23 matrix
elements and an analytic evaluation of Eq. 2 with a hard k cutoff, without your scripts
and before reading your memo. Nothing we have contradicts anything in yours.

What this memo adds:

1. **A closed form for the artefact.** The endpoint feature is a logarithmic
   singularity, which we can write down explicitly. It accounts for the sampling
   instability you report in §5, and it explains why a zero is *forced* between each
   peak pair rather than arising coincidentally. (§3.)
2. **A 40× cutoff sweep.** The integral does eventually saturate — at roughly
   0.8 × (2π/a), eight times further out than the Methods claim, and well past where the
   states are bound. (§4.)
3. **Corroboration at a different reduced mass**, which turns your §4.4 degeneracy note
   into a two-point measurement of the same product. (§6.)

We do not dispute anything in your §4.1, §4.2, §6, §7 or §8, and did not independently
reproduce them.

---

## 2. The cutoff artefacts (your §4.4), reached independently

Same mechanism, same formula. Working from Eq. 2 as printed and substituting u = k²,
the in-plane integral is exact:

```
pi * INT_0^K2  du / [(M1*u + a)(M2*u + b)]
    =  (pi/C) * [ log((M2*K2 + b)/b)  -  log((M1*K2 + a)/a) ]

    with  a = dE13 - 2*hw + i*g,   b = dE23 - hw + i*g,   C = M2*a - M1*b
```

Each logarithm diverges twice: at the band edge (`|a| -> 0`, physical) and at the
integration endpoint (`|M1*K2 + a| -> 0`, i.e. `2*hw = dE(0) + M*k_max^2`). Your
`E(k_max) = E(0) + hbar^2 k_max^2 / 2mu` is the same condition. Because the endpoint
enters both denominators it produces its own 1w and 2w pair — your "omega and 2omega
images of the edge".

We confirmed the classification two ways, both agreeing with your 92%-cutoff test.

**(a) The peak tracks the integration limit.** Over k_max = 0.10 -> 0.30 pi/a the P1
feature marches 687, 656, 621, 584, 561, 546, 540, 531, 517, 473, 407 nm while P2 (752)
and P4 (1505) do not move at all.

**(b) Softening the boundary moves *and fades* it.** Replacing the hard cut with a cos^2
taper of fractional width t (height as fraction of spectrum max in parentheses):

| t | P1 | P3 | P2 | P4 |
|---|---|---|---|---|
| 0.00 (hard) | 546 (0.38) | 1093 (0.93) | 752 | 1505 |
| 0.10 | 561 (0.28) | 1122 (0.71) | 752 | 1505 |
| 0.35 | 595 (0.19) | 1191 (0.51) | 752 | 1505 |
| 0.50 | 612 (0.16) | 1227 (0.45) | 752 | 1505 |

The taper may be worth adding to your toolkit. Moving a cutoff shows a feature is
cutoff-dependent; tapering it shows the feature is specifically an *endpoint* artefact
rather than a real structure that happens to sit near the boundary.

---

## 3. The artefact is logarithmic — which explains your §5 sampling spread

You note that the artefact peak heights are unstable to wavelength sampling: 1200 points
puts the 1070 nm maximum at 4203 pm/V, 900 points at 3309 pm/V, a 27% spread, and you
correctly decline to read anything into it.

The closed form accounts for it. The endpoint feature is a *logarithmic* divergence,
regularised only by Gamma. Its true peak is therefore narrow and large, and the sampled
maximum depends on how close a grid point lands to it. The genuine band-edge resonances
are the other divergence of the same logarithm, but they are additionally broadened by
in-plane dispersion across the resonant disc — which is why they are stable. Exactly the
asymmetry you observed.

Two consequences:

- Comparing amplitudes at the paper's peak wavelengths rather than your own is not
  merely defensible; it is the only stable option for P1/P3.
- The two logarithms enter with **opposite sign**, so the endpoint feature and the
  band-edge feature have opposite sign in Re chi2. A zero is therefore *forced* between
  each pair. This is a sharper version of your "neighbouring resonances interfere
  destructively": the troughs are not coincidental, they are structurally required by
  the truncation.

---

## 4. New: the Methods' saturation claim, tested over a 40x sweep

The Methods state the k contribution "saturated by one-tenth of the Brillouin zone".
Your §4.4 observes it has not. We swept k_max from 0.05 to 2.0 pi/a — 0.025 to 1.0 of
the full zone — to find where it actually does:

```
krng (pi/a):   0.10   0.20   0.40   0.80   1.60   3.20   6.40
peak (pm/V):   32.3   41.2   46.4   48.3   48.9   49.0   49.1
```

It converges around **0.8 x (2pi/a)**, eight times further out than claimed. At
0.1 x (2pi/a) the result is at 84% of its converged value; at 0.1 x (pi/a), 66%. The
claim is false under either reading of "one-tenth of the Brillouin zone".

The artefacts behave accordingly. Pushed far enough they march out of the plotting
window entirely:

| k_max (pi/a) | x (2pi/a) | artefact 1w / 2w | genuine peaks |
|---|---|---|---|
| 0.10 | 0.050 | 687 / 1375 | 752, 1505 |
| 0.15 | 0.075 | 621 / 1241 | 752, 1505 |
| **0.20** | **0.100** | **546 / 1093** | **752, 1505** |
| 0.25 | 0.125 | 473 / 947 | 752, 1505 |
| 0.40 - 2.00 | 0.20 - 1.00 | both below 400 nm | 752, 1505 |

The genuine peaks do not move anywhere across the whole 40x range.

**But the model cannot be converged inside its own domain of validity.** The electron
subbands cross the Al0.55Ga0.45As conduction-band edge at k ~ 0.73-0.85 nm^-1, which is
0.066-0.076 x (2pi/a). Convergence needs ~0.8. So one either stops early and gets
artefacts, or integrates far enough to lose them and is then extrapolating a parabola
across the entire Brillouin zone. Note this also brackets the two BZ conventions:
0.1 x (pi/a) = 0.05 x (2pi/a) sits just inside the bound-state range, while
0.1 x (2pi/a) sits outside it.

This is an argument for your §6(b) approach — a dispersion that flattens where the
states actually leave the well — rather than for any choice of cutoff.

---

## 5. The plotted quantity (your §4.3)

Same argument, same conclusion: |chi2| = 0 requires Re and Im to vanish at the same
wavelength, which a one-parameter curve does not generically do, and the published curve
touches zero twice. Three independent calculations of the trough positions:

| | trough 1 | trough 2 |
|---|---|---|
| paper Fig. 2d | ~605 | ~1330 |
| yours, single-band | 616 | 1343 |
| yours, 8-band | 611 | 1310 |
| ours, kp8 parabolic fit | 617 | 1327 |

And of the genuine resonances: yours 758/1515 (single-band) and 749/1494 (8-band); ours
752/1505; paper 760/1520. Our observable comparison at fixed cutoff, as a fourth data
point:

| observable | norm. RMSE | correlation | at Z1 | at Z2 |
|---|---|---|---|---|
| \|Re chi2\| | **0.066** | **+0.941** | 0.014 | 0.017 |
| \|chi2\| | 0.237 | +0.441 | 0.265 | 0.580 |

**Your two readings both remain open.** We cannot distinguish "Re was plotted and the
axis bars are a slip" from "the computation was real-valued and the label is correct",
and neither can anyone without the authors' code. An earlier draft of this memo claimed
we could; that claim rested on mistaking a colleague's reimplementation for author
source and has been withdrawn (§8).

---

## 6. Our cutoff number, and your degeneracy note

We independently obtained **1.135 nm^-1** against your **1.000**, both claiming ~1% peak
alignment. Your §4.4 already explains it:

> "Note this is degenerate with the in-plane reduced mass: E(k_max) depends only on
> E(0) + hbar^2 k_max^2 / 2mu. We fixed mu at the textbook masses and fitted the cutoff
> rather than the reverse."

That is correct and we had missed it. The figure constrains only the product
mu * k_max^2 = 0.648 eV:

| mu source | mu (m0) | k_max for 540/1080 nm | as fraction of 2pi/a |
|---|---|---|---|
| textbook single-band (m_e 0.067, m_hh 0.34) — yours | 0.05597 | 1.000 nm^-1 | 0.090 |
| **"0.1 BZ" read as 0.1 x (2pi/a)** | — | **1.111 nm^-1** | **0.100** |
| our kp8 parabolic fits | 0.07574 | 1.135 nm^-1 | 0.102 |

We verified your arithmetic: your masses give 500.4 / 1000.9 nm at k = 0.1 x (2pi/a) and
535.0 / 1070.0 nm at k = 1.000, matching your quoted 500/1001 and 535/1071 to a tenth of
a nanometre.

Read together, the two fits bracket the literal reading. Two calculations with different
band models and no knowledge of each other land at 0.090 and 0.102 of the full zone,
with the stated 0.100 between them. That is at least suggestive that the Methods mean
what they say, with the zone radius taken as Gamma-X 2pi/a, and that the residual spread
is the reduced-mass degeneracy rather than a further discrepancy.

**Correction to us.** We had claimed the reproduction *established* that convention. It
does not — that claim assumed our mu. What survives both readings is only that k_max is
roughly twice the 0.1 x (pi/a) used in our production runs. Your "round 1.0 nm^-1 as a
stand-in for one-tenth of the zone" remains a reasonable alternative reading of the same
data.

A triangulation that may be useful. At a fixed cutoff of 1.1114 nm^-1, three band models
bracket the published artefact positions:

| band model | 1w | 2w |
|---|---|---|
| single-band parabolic (light mu) | 500 | 1001 |
| kp8 parabolic fit | 546 | 1093 |
| 8-band non-parabolic (your v24) | 567 | 1134 |
| **paper Fig. 2d** | **540** | **1080** |

The paper sits between parabolic and fully non-parabolic.

---

## 7. What we did not reproduce, and adopt from you

We had no independent account of the absolute scale. Our own gap was ~96x, computed
through frozen Demo 19 matrix elements rather than a fresh solve, and we could not
decompose it.

Your §4.1/§4.2 decomposition — the printed `1/6` absent (6x) and the 2D `1/(2pi)^2`
density of states absent (39.478x), product 237 against your observed ~200 — is a
materially better answer and we adopt it. We agree with your §6.1 that the two are
correlated and that the load-bearing claim is the narrower one: **the 1/(2pi)^2 is
absent**, putting the published values high by ~39.5x.

We have nothing to add to your §7 (the 5.1x measurement gap in the opposite direction)
or your §8 (the `wf_amplitudes_shift_*` offset, the HH/Gamma energy-zero mismatch,
fitting in k^2 rather than k). We had not encountered the first two, and they are
directly relevant to our Demo 23/24 pipeline.

---

## 8. A third reimplementation exists — and is not author code

Our repository contains `docs/equation_2_from_paper/Xi2 (1).m`, an Octave implementation
of Eq. 2. **It is a colleague's own attempt to recreate the paper, not source from the
authors.** Its header ("Copyright (C) 2025 eyinkk", "Created: 2025-12-17") and its date
relative to the arXiv posting invite the opposite reading; an earlier draft of this memo
made that mistake and drew two conclusions from it that are now withdrawn — that your
§4.3 ambiguity was settled in favour of reading 1, and that the paper used 8-band k·p.
Neither follows. Your §2 single-band argument stands unopposed, and if anything that
file cuts the other way: it reads 8-band output, so as a reproduction attempt it may be
using the wrong band model.

We flag it because it is a third independent shot at Eq. 2 and its failure modes may be
instructive, not as evidence about the paper. Its defects, as read:

- **The eight k·p spinor components are summed into one scalar** before overlaps are
  taken (`wftn(:,st) = wftn + 1e-5*(datwf(...))`, repeated eight times). The correct
  spinor inner product is componentwise, `SUM_n INT psi*_{a,n} psi_{b,n} dz`; this
  computes `INT (SUM_n psi_{a,n})* (SUM_m psi_{b,m}) dz`, retaining 56 cross terms that
  pair one state's conduction envelope against another's heavy-hole envelope.
  Orthonormality is lost and HH/LH character becomes unrecoverable. Relevant to us
  independently: the state labelled `hh2` in our Demo 23 output is 0% HH and 97.6% LH at
  k = 0.
- **`+i*gma`** places the pole in the upper half-plane — gain rather than loss. Re is
  unaffected, Im comes out with the wrong sign.
- **`nbdsts=9` with `eigens = eig(find(eig(:,11)~=0),:)`** retains the k-vector row as a
  state whenever `ke(11) != 0`, shifting every state index by one.
- **`hheig = find(eigens(:,11)<0.3)`** hard-codes the CB/VB split at 0.3 eV. Under our
  energy anchoring, holes sit at 1.41-1.45 eV and electrons at 2.95-3.09 eV, so it
  selects nothing.
- **`abs()` on the energy denominators** forces every term to a positive resonance
  energy, so a wrong state selection yields a plausible spectrum rather than obvious
  garbage.
- **`Apre` mixes SI, esu, angstrom and eV·s**, then applies an ad-hoc `1e9`.

One thing in it that is correct and worth noting, because it is easy to get wrong: the
electron and hole pathway lists are matched term-for-term with the right relative sign,
so the assembled sum is genuinely origin-invariant. We tested it — shifting the dipole
origin by 20 nm changes the total by 5e-13 pm/V. But the cancellation is severe: the
individual diagonal dipoles are 12-19 nm while the physically meaningful difference is
0.083 nm, a ~0.7% residue of two large numbers. Any error in the matrix elements is
amplified accordingly.

---

## 9. Open questions

**For the authors** — neither of us can answer these without their code:

1. What k cutoff was actually used, and is "one-tenth of the Brillouin zone" measured
   against pi/a or 2pi/a? Closes §4 and §6 together.
2. Was the plotted quantity the real part or the complex magnitude — i.e. is the axis
   label a slip, or was the computation real-valued? Closes your §4.3 either way.
3. What is the k-space measure in the sum-to-integral conversion? Your §4.2, the item
   with consequences beyond reproducing the figure.
4. What replaces the `1/6` in Eq. 2, and is it a transcription slip? Your §4.1.

**Between the two of us**, independent of the authors:

5. Single-band or 8-band as the better model of the *structure* — your §6(b) versus our
   kp8 fits. Distinct from the question of what the paper computed.
6. Your §7 measurement gap: 1345 pm/V measured against 262 pm/V corrected, 5.1x in the
   opposite direction to the normalization error. Unexplained by anything either of us
   has.

---

## 10. Provenance

Our side: analytic evaluation of Eq. 2 with a hard k cutoff, using aligned parabolic fits
from `demo24/demo23_reanalysis/tables/parabolic_fit_report.csv` and frozen matrix
elements from `demo19/tables/demo19_master_results.csv` (case 00, abrupt reference). No
solver was run and no prior artefact was modified. Scripts, figures and full write-up in
`nextnano/demos/26_real_chi2_paper_comparison/outputs/CUTOFF_ARTIFACT_FINDING/`.

We hold no code or data from the paper. Everything in §2, §3 and §5 was obtained before
we had read `chi2_replication_findings.md`.
