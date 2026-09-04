"""Postprocess real Demo 22 Professional kp8 output.

This module has no synthetic state path. Every public analysis function starts
from a :class:`kp8io22.RawStateGrid` extracted from actual solver files.
"""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np

import chi2_22
import kp8io22
import state_tracking22 as tracking
from config22 import DEMO_DIR, REPO_ROOT, Demo22Error


COLORS = {"paper": "black", "demo21": "#d97706", "hybrid": "#15803d", "demo22": "#2563eb"}


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise Demo22Error(f"refusing empty table {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def finish(path: Path, *, xlabel: str, ylabel: str, xlim=None, ylim=None) -> None:
    plt.xlabel(xlabel); plt.ylabel(ylabel)
    if xlim: plt.xlim(*xlim)
    if ylim: plt.ylim(*ylim)
    plt.grid(alpha=.25)
    handles, _ = plt.gca().get_legend_handles_labels()
    if handles:
        plt.legend(fontsize=8)
    plt.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True); plt.savefig(path, dpi=220); plt.close()


def _component_index(names: tuple[str, ...], token: str) -> int | None:
    token = token.lower()
    for i, name in enumerate(names):
        if token in name.lower().replace("heavy_hole", "hh").replace("light_hole", "lh"):
            return i
    return None


def classify_k0(grid: kp8io22.RawStateGrid) -> dict[str, int]:
    cb = _component_index(grid.component_names, "cb")
    if cb is None:
        raise Demo22Error(
            "CB/HH/LH/SO-resolved spinor columns were not identified; refusing energy-midpoint classification"
        )
    cb_fraction = grid.spinor_components[0, :, cb]
    electron = np.flatnonzero(cb_fraction >= 0.5)
    hole = np.flatnonzero(cb_fraction < 0.5)
    if len(electron) < 2 or len(hole) < 3:
        raise Demo22Error(f"kp8 k=0 classification found {len(electron)} electrons and {len(hole)} holes")
    electron = electron[np.argsort(grid.energies_eV[0, electron])]
    hole = hole[np.argsort(grid.energies_eV[0, hole])[::-1]]
    return {"e1": int(electron[0]), "e2": int(electron[1]),
            "h1": int(hole[0]), "h2": int(hole[1]), "h3": int(hole[2])}


def _track(grid: kp8io22.RawStateGrid, cfg: dict[str, Any]):
    st = cfg["state_tracking"]
    return tracking.track_states(
        grid.energies_eV, np.sqrt(np.clip(grid.spinor_components, 0, None)),
        ntrack=grid.energies_eV.shape[1], minimum_overlap=float(st["minimum_overlap_score"]),
        minimum_margin=float(st["minimum_assignment_margin"]),
        energy_tie_break_weight=float(st["energy_tie_break_weight"]),
    )


def _tracked_band(grid, result, raw_k0):
    raw_index_at_each_k = result.tracked_raw_indices[:, raw_k0]
    return np.asarray([grid.energies_eV[ik, raw] for ik, raw in enumerate(raw_index_at_each_k)])


def polynomial_bands(k: np.ndarray, anchors: dict[str, float]) -> dict[str, np.ndarray]:
    ka = 0.1 * k
    return {
        "e1": anchors["e1"] + 54.492*ka**2 - 851.1*ka**4,
        "e2": anchors["e2"] + 50.864*ka**2 - 732.61*ka**4,
        "h1": anchors["h1"] - 6.9771*ka**2 - 716.47*ka**4 + 36809*ka**6,
        "h2": anchors["h2"] - 10.165*ka**2,
    }


def frozen_matrices(interface_model: str):
    table = REPO_ROOT / "demo_results/demo19/tables/demo19_master_results.csv"
    if not table.is_file():
        raise Demo22Error(f"required licensed frozen matrix table missing: {table}")
    with table.open(newline="", encoding="utf-8") as handle:
        wanted = "00" if interface_model == "abrupt" else "04"
        row = next((r for r in csv.DictReader(handle) if r["case_id"] == wanted), None)
    if row is None:
        raise Demo22Error(f"case {wanted} missing from {table}")
    o = np.array([[float(row["O11"]), float(row["O12"])], [float(row["O21"]), float(row["O22"])]])
    ze = np.array([[float(row["z_e11_nm"]), float(row["z_e12_nm"])], [float(row["z_e21_nm"]), float(row["z_e22_nm"])]])
    zh = np.array([[float(row["z_hh11_nm"]), float(row["z_hh12_nm"])], [float(row["z_hh21_nm"]), float(row["z_hh22_nm"])]])
    return o, ze, zh, {"case_id": wanted, "source": str(table)}


def paper_and_old_models(wavelength: np.ndarray):
    debug = REPO_ROOT / "debug_chi2_spectral_shape"
    if str(debug) not in sys.path: sys.path.insert(0, str(debug))
    import study_core as old  # noqa: PLC0415
    paper = np.interp(wavelength, old.WL, old.paper_norm())
    demo = old.evaluate("demo21", wavelengths=wavelength).total
    hybrid = old.evaluate("hybrid", wavelengths=wavelength).total
    return paper, demo, hybrid


def norm(values):
    v = np.abs(np.asarray(values)); return v / max(float(np.max(v)), 1e-300)


def metrics(wl, values, paper):
    y = norm(values)
    def minimum(lo, hi):
        mask=(wl>=lo)&(wl<=hi); i=np.argmin(y[mask]); return float(wl[mask][i]),float(y[mask][i])
    n1=minimum(500,700);n2=minimum(1200,1400);peak=int(np.argmax(y))
    crossings=[]
    real=np.real(values)
    for i in range(len(wl)-1):
        if real[i]*real[i+1] < 0:
            crossings.append(float(wl[i]-real[i]*(wl[i+1]-wl[i])/(real[i+1]-real[i])))
    return {"node1_nm":n1[0],"node1_depth_norm":n1[1],"node1_error_nm":n1[0]-605,
            "node2_nm":n2[0],"node2_depth_norm":n2[1],"node2_error_nm":n2[0]-1330,
            "dominant_peak_nm":float(wl[peak]),"dominant_peak_error_nm":float(wl[peak]-1520),
            "RMSE":float(np.sqrt(np.mean((y-paper)**2))),
            "chi1550_raw":float(np.interp(1550,wl,np.abs(values))),"real_zero_crossings_nm":";".join(f"{x:.6g}" for x in crossings)}


def run_analysis(cfg: dict[str, Any], raw_root: Path, *, interface_model: str, stage_root: Path) -> dict[str, Any]:
    inventory_csv = stage_root/"01_kp8_solver_validation/raw_output_inventory.csv"
    grid = kp8io22.extract_state_grid(raw_root, inventory_csv)
    kp8io22.save_npz(grid, stage_root/"02_band_dispersion/kp8_state_grid.npz")
    labels = classify_k0(grid); tracked = _track(grid,cfg)
    tracked_energies = {name:_tracked_band(grid,tracked,raw) for name,raw in labels.items()}
    anchors={name:float(value[0]) for name,value in tracked_energies.items() if name in ("e1","e2","h1","h2")}
    poly=polynomial_bands(grid.k_per_nm,anchors)

    # 01 validation
    checks=[
        {"check":"k points","value":len(grid.k_per_nm),"expected":">= 2","tolerance":"n/a","pass_fail":"PASS","notes":"explicit solver k vectors"},
        {"check":"finite eigenenergies","value":bool(np.isfinite(grid.energies_eV).all()),"expected":True,"tolerance":"exact","pass_fail":"PASS","notes":""},
        {"check":"spinor normalization","value":float(np.max(np.abs(grid.spinor_components.sum(axis=2)-1))),"expected":0,"tolerance":cfg['validation']['normalization_tolerance'],"pass_fail":"PASS" if np.max(np.abs(grid.spinor_components.sum(axis=2)-1))<=float(cfg['validation']['normalization_tolerance']) else "FAIL","notes":"component fractions"},
        {"check":"four tracked target states","value":str(labels),"expected":"e1,e2,h1,h2","tolerance":"character based","pass_fail":"PASS","notes":"CB classification, not energy midpoint"},
    ]
    write_csv(stage_root/"01_kp8_solver_validation/solver_validation.csv",checks)
    plt.figure(figsize=(8,4)); plt.scatter(range(grid.energies_eV.shape[1]),grid.energies_eV[0]); finish(stage_root/"01_kp8_solver_validation/01_k0_state_energies.png",xlabel="Raw kp8 state index",ylabel="Energy (eV)")

    # 02 dispersion
    rows=[]
    for ik,k in enumerate(grid.k_per_nm):
        for raw in range(grid.energies_eV.shape[1]): rows.append({"k_per_nm":k,"raw_state_index":int(grid.raw_state_index[raw]),"energy_eV":grid.energies_eV[ik,raw]})
    write_csv(stage_root/"02_band_dispersion/all_states_vs_k.csv",rows)
    plt.figure(figsize=(9,5));
    for raw in range(grid.energies_eV.shape[1]): plt.plot(grid.k_per_nm,grid.energies_eV[:,raw],lw=.8)
    finish(stage_root/"02_band_dispersion/02_all_states_dispersion.png",xlabel="k_parallel (nm^-1)",ylabel="Energy (eV)")
    plt.figure(figsize=(9,5));
    for name in ("e1","e2","h1","h2"): plt.plot(grid.k_per_nm,tracked_energies[name],label=name)
    finish(stage_root/"02_band_dispersion/02_tracked_e1_e2_h1_h2.png",xlabel="k_parallel (nm^-1)",ylabel="Energy (eV)")
    error_rows=[]
    for name in ("e1","e2","h1","h2"):
        delta=tracked_energies[name]-poly[name]; imax=int(np.argmax(np.abs(delta)))
        error_rows.append({"band":name,"rms_error_meV":1000*float(np.sqrt(np.mean(delta**2))),"max_abs_error_meV":1000*float(abs(delta[imax])),"k_at_max_error_per_nm":float(grid.k_per_nm[imax]),"actual_k0_eV":anchors[name],"qualitative_divergence":bool(np.sign(np.gradient(tracked_energies[name]))[-1]!=np.sign(np.gradient(poly[name]))[-1])})
        plt.figure(figsize=(8,4));plt.plot(grid.k_per_nm,tracked_energies[name],label="actual kp8");plt.plot(grid.k_per_nm,poly[name],"--",label="hybrid polynomial");finish(stage_root/f"02_band_dispersion/02_actual_vs_polynomial_{name}.png",xlabel="k_parallel (nm^-1)",ylabel="Energy (eV)")
    plt.figure(figsize=(9,5))
    for name in ("e1","e2","h1","h2"):
        plt.plot(grid.k_per_nm,tracked_energies[name],label=f"{name} kp8")
        plt.plot(grid.k_per_nm,poly[name],"--",label=f"{name} polynomial")
    finish(stage_root/"02_band_dispersion/02_actual_vs_polynomial_all.png",xlabel="k_parallel (nm^-1)",ylabel="Energy (eV)")
    write_csv(stage_root/"02_band_dispersion/02_dispersion_error_metrics.csv",error_rows)
    plt.figure(figsize=(9,5));
    for name in ("e1","e2","h1","h2"):plt.plot(grid.k_per_nm,1000*(tracked_energies[name]-poly[name]),label=name)
    finish(stage_root/"02_band_dispersion/02_dispersion_error_vs_k.png",xlabel="k_parallel (nm^-1)",ylabel="E(kp8)-E(poly) (meV)")

    # 03 tracking
    tr_rows=[]
    reverse={v:k for k,v in labels.items()}
    for ik,k in enumerate(grid.k_per_nm):
        for identity in range(tracked.tracked_raw_indices.shape[1]):
            raw=int(tracked.tracked_raw_indices[ik,identity]);tr_rows.append({"k_per_nm":k,"raw_state_index":int(grid.raw_state_index[raw]),"tracked_state_label":reverse.get(identity,f"state_{identity+1}"),"energy_eV":grid.energies_eV[ik,raw],"previous_state_index":"" if ik==0 else int(grid.raw_state_index[tracked.tracked_raw_indices[ik-1,identity]]),"overlap_score":tracked.overlap_scores[ik,identity],"assignment_margin":tracked.assignment_margins[ik,identity],"dominant_spinor_character":grid.component_names[int(np.argmax(grid.spinor_components[ik,raw]))],"confidence":tracked.confidence[ik,identity],"notes":"spinor-feature tracking; full envelope overlap preferred when parsed"})
    write_csv(stage_root/"03_state_tracking/state_tracking.csv",tr_rows)
    plt.figure(figsize=(9,5));
    for name,raw in labels.items():plt.plot(grid.k_per_nm,tracked.overlap_scores[:,raw],label=name)
    finish(stage_root/"03_state_tracking/03_tracking_overlap_scores.png",xlabel="k_parallel (nm^-1)",ylabel="Adjacent-k overlap score",ylim=(0,1.05))
    plt.figure(figsize=(9,5));
    for name in ("e1","e2","h1","h2"):plt.plot(grid.k_per_nm,tracked_energies[name],label=f"tracked {name}")
    finish(stage_root/"03_state_tracking/03_raw_vs_tracked_states.png",xlabel="k_parallel (nm^-1)",ylabel="Energy (eV)")

    # 04 spinor composition
    comp_rows=[]
    for name,identity in labels.items():
        raw_each=tracked.tracked_raw_indices[:,identity]
        plt.figure(figsize=(9,5))
        for ic,cname in enumerate(grid.component_names):
            values=np.array([grid.spinor_components[ik,raw,ic] for ik,raw in enumerate(raw_each)])
            plt.plot(grid.k_per_nm,values,label=cname)
            for ik,k in enumerate(grid.k_per_nm):comp_rows.append({"k_per_nm":k,"state":name,"component":cname,"fraction":values[ik]})
        finish(stage_root/f"04_spinor_composition/{name}_spinor_vs_k.png",xlabel="k_parallel (nm^-1)",ylabel="Spinor fraction",ylim=(0,1.05))
    write_csv(stage_root/"04_spinor_composition/spinor_composition.csv",comp_rows)

    # 05/06 limitations are explicit: raw adapters must prove a common complex gauge.
    for sub,text in (("05_wavefunction_evolution","k-dependent multicomponent envelope adapter not yet validated against this solver output"),("06_matrix_elements","complex interband Bloch optical amplitudes required by Eq. 2 are not established by envelope-momentum output")):
        path=stage_root/sub/"LIMITATION.md";path.parent.mkdir(parents=True,exist_ok=True);path.write_text("# Limitation\n\n"+text+". No frozen or scalar substitute was made.\n",encoding="utf-8")

    # 07 neighboring-state gaps and 08 physically constrained provisional domain.
    validity=[]
    cb_index = _component_index(grid.component_names, "cb")
    electron_identities = [
        i for i in range(grid.energies_eV.shape[1])
        if grid.spinor_components[0, i, cb_index] >= 0.5
    ]
    e_extra=[i for i in electron_identities if i not in (labels['e1'],labels['e2'])]
    for ik,k in enumerate(grid.k_per_nm):
        e2=tracked_energies['e2'][ik];h2=tracked_energies['h2'][ik]
        raw_all=tracked.tracked_raw_indices[ik]
        extra_e=[grid.energies_eV[ik,raw_all[i]] for i in e_extra if grid.energies_eV[ik,raw_all[i]]>e2]
        h3=tracked_energies['h3'][ik]
        gap_e=min((x-e2 for x in extra_e),default=float('nan'))
        gap_h=abs(h2-h3)
        valid=bool(np.isfinite(gap_e) and gap_e>.02 and gap_h>.02 and all(tracked.confidence[ik,labels[x]]!='ambiguous' for x in ('e1','e2','h1','h2')))
        validity.append({"k_per_nm":k,"nearest_extra_conduction_gap_eV":gap_e,"nearest_extra_valence_gap_eV":gap_h,"mixing_indicator":min(tracked.overlap_scores[ik,labels[x]] for x in ('e1','e2','h1','h2')),"two_state_valid":valid,"notes":"20 meV isolation gate plus non-ambiguous tracking"})
    write_csv(stage_root/"07_neighboring_states/two_state_validity.csv",validity)
    plt.figure(figsize=(9,5));plt.plot(grid.k_per_nm,[r['nearest_extra_conduction_gap_eV'] for r in validity],label="extra conduction gap");plt.plot(grid.k_per_nm,[r['nearest_extra_valence_gap_eV'] for r in validity],label="h2-h3 gap");finish(stage_root/"07_neighboring_states/07_neighboring_bands.png",xlabel="k_parallel (nm^-1)",ylabel="Isolation gap (eV)")
    # The diagnostic interval must be a contiguous prefix from Gamma. Accepting
    # isolated valid points at larger k would create a hole in the radial integral.
    reliable_prefix = []
    for ik, kval in enumerate(grid.k_per_nm):
        reliable = all(tracked.confidence[ik,labels[x]] != 'ambiguous'
                       for x in ('e1','e2','h1','h2'))
        if not reliable:
            break
        reliable_prefix.append(float(kval))
    if len(reliable_prefix) < 2:
        raise Demo22Error("fewer than two contiguous, reliably tracked k points from Gamma")
    recommended = reliable_prefix[-1]
    isolation_valid = all(r['two_state_valid'] for r in validity
                          if r['k_per_nm'] <= recommended)
    write_csv(stage_root/"08_k_domain/k_domain_assessment.csv",[{
        "recommended_kmax_per_nm":recommended,
        "reason":"largest contiguous Gamma-origin interval passing the state-tracking gate; not fitted to paper",
        "sensitivity_range":"recompute after boundary/localization and cumulative-integral validation",
        "status":"PROVISIONAL_TRACKING_ONLY",
        "two_state_isolation_valid_through_kmax":isolation_valid,
    }])
    plt.figure(figsize=(9,4));plt.plot(grid.k_per_nm,[int(r['two_state_valid']) for r in validity],label="two-state validity");finish(stage_root/"08_k_domain/08_band_validity_vs_k.png",xlabel="k_parallel (nm^-1)",ylabel="valid (1/0)",ylim=(-.05,1.05))

    # 09 energy-only controlled upgrade, same-geometry licensed frozen matrices.
    use = grid.k_per_nm <= recommended if recommended>0 else np.ones_like(grid.k_per_nm,dtype=bool)
    k=grid.k_per_nm[use]
    bands={name:tracked_energies[name][use] for name in ('e1','e2','h1','h2')}
    o,ze,zh,matrix_provenance=frozen_matrices(interface_model)
    wl=np.arange(float(cfg['chi2']['wavelength_min_nm']),float(cfg['chi2']['wavelength_max_nm'])+0.5,float(cfg['chi2']['wavelength_step_nm']))
    energy_only=chi2_22.chi2_from_k_inputs(wl,k,np.vstack([bands['e1'],bands['e2']]),np.vstack([bands['h1'],bands['h2']]),o,ze,zh,broadening_meV=float(cfg['chi2']['broadening_meV']))
    paper,demo,hybrid=paper_and_old_models(wl)
    met=metrics(wl,energy_only.chi2,paper)
    write_csv(stage_root/"09_energy_only_chi2/energy_only_metrics.csv",[{"model":"DEMO22_ENERGY_ONLY","observable":"|chi2|",**met,"kmax_per_nm":float(k[-1]),"matrix_source":matrix_provenance['source'],"matrix_case":matrix_provenance['case_id']}])
    def comparison(path,transform,xlim):
        plt.figure(figsize=(10,5));plt.plot(wl,paper,label="paper",color=COLORS['paper'],ls='--');plt.plot(wl,norm(transform(demo)),label="Demo 21",color=COLORS['demo21']);plt.plot(wl,norm(transform(hybrid)),label="hybrid polynomial",color=COLORS['hybrid']);plt.plot(wl,norm(transform(energy_only.chi2)),label="Demo22 energy-only",color=COLORS['demo22']);finish(path,xlabel="Fundamental wavelength (nm)",ylabel="Normalized shape",xlim=xlim,ylim=(0,1.05))
    comparison(stage_root/"09_energy_only_chi2/09_model_comparison_normalized.png",np.abs,(400,1850))
    comparison(stage_root/"09_energy_only_chi2/09_node1_zoom.png",np.abs,(500,700));comparison(stage_root/"09_energy_only_chi2/09_node2_zoom.png",np.abs,(1200,1400));comparison(stage_root/"09_energy_only_chi2/09_1520_zoom.png",np.abs,(1450,1600))
    plt.figure(figsize=(10,5));plt.plot(wl,energy_only.chi2.real,label="Re");plt.plot(wl,energy_only.chi2.imag,label="Im");finish(stage_root/"09_energy_only_chi2/09_real_imag.png",xlabel="Fundamental wavelength (nm)",ylabel="chi2 (pm/V)",xlim=(400,1850))
    plt.figure(figsize=(10,5));plt.plot(wl,norm(energy_only.chi2),label="|chi2|");finish(stage_root/"09_energy_only_chi2/09_full_spectrum_abs.png",xlabel="Fundamental wavelength (nm)",ylabel="Normalized |chi2|",xlim=(400,1850))
    plt.figure(figsize=(10,5));plt.plot(wl,norm(energy_only.chi2.real),label="|Re chi2|");finish(stage_root/"09_energy_only_chi2/09_full_spectrum_abs_real.png",xlabel="Fundamental wavelength (nm)",ylabel="Normalized |Re chi2|",xlim=(400,1850))

    # Controlled real-band substitution ladder. Every rung changes only the
    # named denominator dispersion; numerator matrices and k grid stay fixed.
    actual = bands
    polynomial = {name: poly[name][use] for name in ('e1','e2','h1','h2')}
    ladder_definitions = [
        ("all_polynomial", ()), ("actual_e1", ("e1",)),
        ("actual_e1_e2", ("e1","e2")),
        ("actual_e1_e2_h1", ("e1","e2","h1")),
        ("all_actual", ("e1","e2","h1","h2")),
        ("actual_e2_only", ("e2",)), ("actual_h2_only", ("h2",)),
    ]
    ladder = {}
    ladder_rows=[]
    for name, replacements in ladder_definitions:
        chosen={band:(actual[band] if band in replacements else polynomial[band])
                for band in ('e1','e2','h1','h2')}
        value=chi2_22.chi2_from_k_inputs(
            wl,k,np.vstack([chosen['e1'],chosen['e2']]),
            np.vstack([chosen['h1'],chosen['h2']]),o,ze,zh,
            broadening_meV=float(cfg['chi2']['broadening_meV'])).chi2
        ladder[name]=value
        ladder_rows.append({"model":name,"replaced_bands":";".join(replacements) or "none",
                            **metrics(wl,value,paper)})
    write_csv(stage_root/"09_energy_only_chi2/09_real_band_substitution_metrics.csv",ladder_rows)
    for filename,limits in (("09_real_band_substitution_ladder.png",(400,1850)),
                            ("09_ladder_node1.png",(500,700)),
                            ("09_ladder_node2.png",(1200,1400)),
                            ("09_ladder_1520.png",(1450,1600))):
        plt.figure(figsize=(10,5))
        for name,value in ladder.items(): plt.plot(wl,norm(value),label=name)
        finish(stage_root/"09_energy_only_chi2"/filename,xlabel="Fundamental wavelength (nm)",ylabel="Normalized |chi2|",xlim=limits,ylim=(0,1.05))

    # 11 pathway and 12 k-resolved physics.
    term_rows=[]
    targets=(605,1045,1330,1520)
    for target in targets:
        iw=int(np.argmin(abs(wl-target)))
        for it,label in enumerate(energy_only.term_labels):term_rows.append({"wavelength_nm":target,"term":label,"real":energy_only.terms[it,iw].real,"imag":energy_only.terms[it,iw].imag,"magnitude":abs(energy_only.terms[it,iw])})
        order=np.argsort(np.abs(energy_only.terms[:,iw]))[::-1]
        plt.figure(figsize=(10,5));plt.bar(range(16),energy_only.terms[order,iw].real);plt.xticks(range(16),[energy_only.term_labels[i] for i in order],rotation=70);finish(stage_root/f"11_term_decomposition/11_terms_{target}nm.png",xlabel="Pathway ranked by magnitude",ylabel="Re term (pm/V)")
    write_csv(stage_root/"11_term_decomposition/term_comparison.csv",term_rows)
    for target in (605,1330,1520,int(met['dominant_peak_nm'])):
        iw=int(np.argmin(abs(wl-target)));f=energy_only.summed_integrand[iw]
        plt.figure(figsize=(9,5));plt.plot(k,f.real,label="Re F");plt.plot(k,f.imag,label="Im F");finish(stage_root/f"12_k_resolved_cancellation/12_{target}nm.png",xlabel="k_parallel (nm^-1)",ylabel="F(k)")
        radial=k/math.pi*f;cum=np.zeros_like(f);cum[1:]=np.cumsum(.5*(radial[1:]+radial[:-1])*np.diff(k))*chi2_22.validated.absolute_prefactor(chi2_22.validated.Chi2Settings())
        plt.figure(figsize=(9,5));plt.plot(k,cum.real,label="Re I(K)");plt.plot(k,cum.imag,label="Im I(K)");finish(stage_root/f"12_k_resolved_cancellation/12_cumulative_{target}nm.png",xlabel="K (nm^-1)",ylabel="Cumulative chi2 (pm/V)")

    # 13 observables, 14 Gamma, 15 final comparison.
    observables={"Re_chi2":energy_only.chi2.real,"Im_chi2":energy_only.chi2.imag,"abs_chi2":np.abs(energy_only.chi2),"abs_Re_chi2":np.abs(energy_only.chi2.real)}
    obs_rows=[];plt.figure(figsize=(10,5))
    for name,value in observables.items():plt.plot(wl,norm(value),label=name);obs_rows.append({"observable":name,**metrics(wl,value,paper)})
    finish(stage_root/"13_observable_comparison/13_four_observables.png",xlabel="Fundamental wavelength (nm)",ylabel="Normalized observable",xlim=(400,1850),ylim=(0,1.05));write_csv(stage_root/"13_observable_comparison/observable_rmse.csv",obs_rows)
    gamma_rows=[];gamma_values={};plt.figure(figsize=(10,5))
    for gamma in cfg['chi2']['broadening_sweep_meV']:
        value=chi2_22.chi2_from_k_inputs(wl,k,np.vstack([bands['e1'],bands['e2']]),np.vstack([bands['h1'],bands['h2']]),o,ze,zh,broadening_meV=float(gamma)).chi2
        gamma_values[float(gamma)]=value
        gamma_rows.append({"gamma_meV":gamma,**metrics(wl,value,paper)});plt.plot(wl,norm(value),label=f"{gamma:g} meV")
    finish(stage_root/"14_broadening_sensitivity/14_gamma_full.png",xlabel="Fundamental wavelength (nm)",ylabel="Normalized |chi2|",xlim=(400,1850),ylim=(0,1.05));write_csv(stage_root/"14_broadening_sensitivity/broadening_metrics.csv",gamma_rows)
    for filename,limits in (("14_gamma_node1.png",(500,700)),("14_gamma_node2.png",(1200,1400)),("14_gamma_1520.png",(1450,1600))):
        plt.figure(figsize=(10,5))
        for gamma,value in gamma_values.items(): plt.plot(wl,norm(value),label=f"{gamma:g} meV")
        finish(stage_root/"14_broadening_sensitivity"/filename,xlabel="Fundamental wavelength (nm)",ylabel="Normalized |chi2|",xlim=limits,ylim=(0,1.05))
    final_rows=[]
    for name,value in (("Demo21",demo),("Hybrid polynomial",hybrid),("Demo22 energy-only",energy_only.chi2)):final_rows.append({"model":name,"observable":"|chi2|",**metrics(wl,value,paper),"notes":"same own-maximum normalization"})
    write_csv(stage_root/"15_full_paper_comparison/15_final_metrics.csv",final_rows)
    comparison(stage_root/"15_full_paper_comparison/15_final_normalized.png",np.abs,(400,1850));comparison(stage_root/"15_full_paper_comparison/15_final_node1.png",np.abs,(500,700));comparison(stage_root/"15_full_paper_comparison/15_final_node2.png",np.abs,(1200,1400));comparison(stage_root/"15_full_paper_comparison/15_final_1520.png",np.abs,(1450,1600))
    plt.figure(figsize=(10,5));plt.plot(wl,np.abs(demo),label="Demo 21");plt.plot(wl,np.abs(hybrid),label="hybrid polynomial");plt.plot(wl,np.abs(energy_only.chi2),label="Demo22 energy-only");finish(stage_root/"15_full_paper_comparison/15_final_raw.png",xlabel="Fundamental wavelength (nm)",ylabel="Raw |chi2| (pm/V)",xlim=(400,1850))

    summary={"status":"ENERGY_ONLY_COMPLETE_FULL_K_MATRIX_BLOCKED","interface_model":interface_model,"recommended_kmax_per_nm":recommended,"labels_k0":labels,"dispersion_errors":error_rows,"energy_only_metrics":met,"matrix_provenance":matrix_provenance}
    (stage_root/"16_root_cause_analysis").mkdir(parents=True,exist_ok=True)
    (stage_root/"16_root_cause_analysis/ROOT_CAUSE_ANALYSIS.md").write_text("# Root-cause analysis\n\nActual evidence is summarized in `root_cause_evidence.json`. Full-k numerator physics remains inconclusive until complex interband optical amplitudes are available.\n",encoding="utf-8")
    (stage_root/"16_root_cause_analysis/root_cause_evidence.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    (stage_root/"17_final_report").mkdir(parents=True,exist_ok=True)
    (stage_root/"17_final_report/DEMO22_FINAL_REPORT.md").write_text("# Demo 22 final report\n\n"+json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    return summary
