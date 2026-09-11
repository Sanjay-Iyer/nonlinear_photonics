# 28C: cached extended-k diagnostic

Run `python studies/28C_extended_k/run.py` from Demo 28. It uses local `nextnano/raw_extended` and the only Eq2 engine, `chi2/equation2.py`. Edit `config/extended_k.json` to change cutoffs inside the actual solved range. Every cutoff saves its derived inputs, complex spectra, Re/Im/magnitudes, pathway spectra and metadata.

The actual cached Professional grid reaches 0.125 pi/a. Nested 0.1, 0.1125 and 0.125 pi/a cutoffs retain 241, 271 and 301 native samples, respectively. This is a genuine numerical extension, not a parabolic extrapolation. `extended_cutoffs.csv` gives global maxima; `windowed_features.csv` gives three fixed-window local extrema with an interior flag. The global Im maximum switches between spectral lobes; do not report that as one continuously shifting resonance.

The extended dataset uses 301 points over a wider domain than the baseline. Compare nested cutoffs in this one dataset to isolate cutoff effects. Finite-k state identity remains unresolved, and historical h2 is LH dominated. These spectra therefore extend the historical model, not its verified physical validity.

`prepare_work_laptop.py` generates a modest, provisional 0.15 pi/a / 901-point work plan and static preflight, without any executable launch. See `../../WORK_LAPTOP_RUN.md` before an actual solve.
