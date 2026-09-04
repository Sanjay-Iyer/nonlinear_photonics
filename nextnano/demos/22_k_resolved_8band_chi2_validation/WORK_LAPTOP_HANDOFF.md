# Work-laptop handoff

1. Pull the repository and activate the Python environment containing NumPy,
   SciPy, matplotlib, PyYAML, and Jinja2.
2. Confirm the local machine YAML resolves the **Professional** executable,
   full database, licence, and results root. Either use the repository's
   established configuration or pass `--machine C:\path\to\machine.yaml`.
3. Run:

```powershell
python .\nextnano\demos\22_k_resolved_8band_chi2_validation\run_demo22.py --physics
```

The runner executes abrupt integration/dispersion and the graded control,
stores raw output below `demo_results/demo22`, and analyzes the primary abrupt
integration output. If the Professional version's output filenames differ from
the documented kp8 form, the fail-loud parser first writes
`01_kp8_solver_validation/raw_output_inventory.csv`; update `kp8io22.py` against
those real files and rerun with `--analyse-existing`.

Do not point this at the free executable. Its `--parse` success proves grammar
only and is not a kp8 physics result.
