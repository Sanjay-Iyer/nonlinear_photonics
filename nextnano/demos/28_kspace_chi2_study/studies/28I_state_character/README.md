# 28I: state evidence, not a validity certificate

Run `python scripts/run_state_audit.py` from Demo 28. For the extension use `--input nextnano/raw_extended --output outputs/28I_state_character/extended`.

Current cached data support all raw energies versus k and spinor character/localization only at k=0. The audit does not infer missing finite-k spinors. Its adjacent-pair overlap machinery is phase/doublet-rotation invariant, but there are zero actual adjacent-k overlap comparisons in these caches. It does not relabel competing branches.

See `../../STATE_AUDIT.md` for output mapping, the LH-dominated historical h2 finding and the limits on high-k physical interpretation.
