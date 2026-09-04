# Demo 22 — k-resolved 8-band k·p validation of the χ² spectrum

Demo 22 is a Professional-solver experiment that replaces the manually imposed
finite-k polynomial bands in the validated 16-pathway χ² calculation with bands
from one internally consistent, structure-specific nextnano++ 8-band run.

The primary model is the paper's ideal-abrupt 30 nm period:

`Al0.55Ga0.45As 9.1 | GaAs 7.1 | Al0.55Ga0.45As 1.8 | GaAs 2.9 | Al0.55Ga0.45As 9.1 nm`.

The 1 nm linearly graded Demo 21 Case 04 geometry is a labelled secondary
control. Its matrices are never mixed into the abrupt primary calculation.

## Model separation

- A: Demo 21 parabolic baseline.
- B: hybrid polynomial dispersion.
- C: actual kp8 energies plus same-geometry frozen k=0 matrices.
- D: actual kp8 energies and rigorously established complex k-dependent
  matrices, only if the Professional export supports them.

The validated Demo 20 equation is reused by `chi2_22.py`; Demo 22 changes its
physical inputs, not its algebra. State labels are assigned from k=0 spinor
character and tracked by adjacent-k overlap/character, never by energy order
alone. The raw parser refuses to infer k from a filename index.

## Run

```powershell
conda activate ai
python .\nextnano\demos\22_k_resolved_8band_chi2_validation\run_demo22.py
python .\nextnano\demos\22_k_resolved_8band_chi2_validation\run_demo22.py --physics
```

The first command renders the four production/control decks plus 48- and
72-point primary integration-convergence decks, syntax-checks them when the free parser is
installed, records provenance, and reports whether Professional execution is
possible. The second command fails nonzero unless a complete, enabled,
non-free machine configuration resolves. It never substitutes synthetic data.

To adapt already-produced Professional output without rerunning the solver:

```powershell
python .\nextnano\demos\22_k_resolved_8band_chi2_validation\run_demo22.py `
  --analyse-existing C:\nn_results\...\raw\abrupt_integration
```

Current execution state is recorded in `STAGE_STATUS.csv`. A preflight-only
host has no Demo 22 spectral result; blocked-stage Markdown files are deliberate
evidence of this, not placeholders masquerading as completion.
