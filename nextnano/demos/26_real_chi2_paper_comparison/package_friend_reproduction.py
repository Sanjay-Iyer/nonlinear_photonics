"""Build portable data bundle from preserved repository inputs; no solver run."""
from pathlib import Path
import ast
import csv
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE/"friend_reproduction"
DATA = OUT/"data"
DATA.mkdir(exist_ok=True)
provenance = []

def rows(path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def copy(source, name):
    destination = DATA/name
    shutil.copy2(source,destination)
    provenance.append({"source":source.relative_to(ROOT).as_posix(),"bundled":"data/"+name,
                       "sha256":hashlib.sha256(destination.read_bytes()).hexdigest()})

matrix = ROOT/"demo_results/demo19/tables/demo19_master_results.csv"
disp = ROOT/"demo_results/demo24/demo23_reanalysis/tables/tracked_dispersions_and_fits.csv"
row = next(r for r in rows(matrix) if r["case_id"] == "04")
states = {s: [r for r in rows(disp) if r["state"]==s] for s in ["e1","e2","hh1","hh2"]}
b = {"k_per_nm":[float(r["k_per_nm"]) for r in states["e1"]],
     "electron_eV":[[float(r["demo21_aligned_energy_eV"]) for r in states[s]] for s in ["e1","e2"]],
     "valence_eV":[[float(r["demo21_aligned_energy_eV"]) for r in states[s]] for s in ["hh1","hh2"]]}
for key,prefix,suffix in [("overlap","O",""),("ze_nm","z_e","_nm"),("zh_nm","z_hh","_nm")]:
    b[key] = [[float(row[f"{prefix}{i}{j}{suffix}"]) for j in [1,2]] for i in [1,2]]
source = HERE/"outputs/CUTOFF_ARTIFACT_FINDING/cutoff_test.py"
constants = {}
for node in ast.parse(source.read_text()).body:
    if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name):
        name=node.targets[0].id
        if name in ["E0","AC","O","ZE","ZH"]:
            constants[name]=ast.literal_eval(node.value)
d = {"energy_eV":[constants["E0"][s] for s in ["e1","e2","h1","h2"]],
     "curvature_eV_nm2":[constants["AC"][s] for s in ["e1","e2","h1","h2"]]}
for key,name in [("overlap","O"),("ze_nm","ZE"),("zh_nm","ZH")]:
    d[key]=[[constants[name][i,j] for j in [1,2]] for i in [1,2]]
(OUT/"inputs.json").write_text(json.dumps({"baseline":b,"diagnostic":d},indent=2))
copy(disp,"tracked_dispersions_and_fits.csv")
copy(ROOT/"demo_results/demo24/demo23_reanalysis/spectra/23D_chi2.csv","baseline_reference.csv")
copy(HERE/"outputs/CUTOFF_ARTIFACT_FINDING/fig2d_chi2_components.csv","diagnostic_reference.csv")
copy(ROOT/"nextnano/demos/23_k_resolved_dispersion_validation/paper_figure2d_digitized_simulation.csv","paper.csv")
copy(ROOT/"demo_results/demo23/raw/production_y_n301_k0100/production_y_n301_k0100/production_y_n301_k0100.in","nextnano_production.in")
copy(ROOT/"nextnano/demos/23_k_resolved_dispersion_validation/demo23_config.yaml","demo23_config.yaml")
# Single-band Gamma/HH decks that produced the frozen k=0 energies and O/z matrix
# elements (Demo 19 tables; Demo 20 decks are identical apart from the comment header).
copy(ROOT/"demo_results/demo20/inputs/case_00/case.in","nextnano_single_band_case00_abrupt.in")
copy(ROOT/"demo_results/demo20/inputs/case_04/case.in","nextnano_single_band_case04_linear_1nm.in")
for p in [matrix,source]:
    provenance.append({"source":p.relative_to(ROOT).as_posix(),"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"note":"Selected numeric inputs extracted into inputs.json"})
(OUT/"provenance.json").write_text(json.dumps(provenance,indent=2))
print(OUT)
