"""Report exactly what the first licensed Demo 14 gate actually accomplished.

Run on the WORK LAPTOP. Reads only; changes nothing.
"""
import json, sys
from pathlib import Path

roots = [
    Path(r"C:\Code\optics\nextnano\nonlinear_photonics\nextnano\results\demo_runs\demo_runs\14_absolute_chi2_graded_acqw_bo\demo14_startup_gate"),
    Path(r"C:\Code\optics\nextnano\nonlinear_photonics\nextnano\results\demo_runs\14_absolute_chi2_graded_acqw_bo\demo14_startup_gate"),
]
root = next((r for r in roots if r.is_dir()), None)
if root is None:
    print("No gate directory found at either candidate path:")
    for r in roots:
        print("   ", r)
    sys.exit(1)

print("GATE DIRECTORY:", root)
print("=" * 78)

result = root / "demo14_startup_gate_result.json"
if result.is_file():
    payload = json.loads(result.read_text(encoding="utf-8"))
    print("gate_passed            :", payload.get("gate_passed"))
    print("gate_unavailable_reason:", (payload.get("gate_unavailable_reason") or "")[:300])
    print("results recorded for   :", sorted(payload.get("results") or {}))
else:
    print("!! no demo14_startup_gate_result.json")

for case in ("gate_a_native_linear", "gate_b_imported_linear"):
    d = root / case
    print("\n" + "-" * 78)
    print("CASE:", case)
    if not d.is_dir():
        print("   directory does not exist -> this case NEVER STARTED")
        continue
    deck = d / "nextnano_input" / "case.in"
    print("   deck written        :", deck.is_file(), deck.stat().st_size if deck.is_file() else "")
    for name in ("stdout.txt", "stderr.txt"):
        f = d / "logs" / name
        print(f"   {name:<20}:", f.is_file(), f.stat().st_size if f.is_file() else "")
    out = d / "nextnano_output"
    files = sorted(p for p in out.rglob("*") if p.is_file()) if out.is_dir() else []
    print("   raw output files    :", len(files),
          f"({sum(p.stat().st_size for p in files)/1e6:.2f} MB)")
    for marker in ("job_done.txt", "simulation_info.txt", "simulation_input.txt"):
        hits = [p for p in files if p.name == marker]
        print(f"   {marker:<20}:", "PRESENT" if hits else "absent")
    stage = d / "case_stage.json"
    if stage.is_file():
        s = json.loads(stage.read_text(encoding="utf-8"))
        print("   recorded stage      :", s.get("stage"))
        solver = s.get("solver") or {}
        print("   solver return code  :", solver.get("solver_return_code"))
        print("   solver elapsed (s)  :", solver.get("solver_elapsed_seconds"))
    else:
        print("   recorded stage      : (none -- this gate predates stage tracking)")
    # The solver's own verdict, straight from its log.
    log = d / "logs" / "stdout.txt"
    if log.is_file():
        text = log.read_text(encoding="utf-8", errors="replace").lower()
        for marker in ("simulation completed", "calculation successfully completed",
                       "terminating program", "fatal error", "license"):
            if marker in text:
                print(f"   stdout contains     : '{marker}'")
