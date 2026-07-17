"""Schema check for paper_params.yaml (Phase 0 gate).

Usage:  python check_config.py [--config path/to/paper_params.yaml]
Exits 0 if the config validates, 1 with a list of violations otherwise.
"""
import argparse
import sys
from pathlib import Path

import yaml

ERRORS = []


def err(msg):
    ERRORS.append(msg)


def need(d, path, typ=None):
    """Fetch a dotted path; record an error if missing or wrongly typed."""
    node = d
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            err(f"missing key: {path}")
            return None
        node = node[part]
    if typ is not None and not isinstance(node, typ):
        err(f"key {path} has type {type(node).__name__}, expected {typ}")
    return node


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(Path(__file__).with_name("paper_params.yaml")))
    args = ap.parse_args()

    cfg = yaml.safe_load(open(args.config, encoding="utf-8"))

    layers = need(cfg, "material.period_layers_nm", list)
    if layers is not None:
        if len(layers) != 4:
            err("material.period_layers_nm must have 4 entries")
        elif abs(sum(layers) - 30.0) > 1e-6:
            err(f"period must sum to 30.0 nm, got {sum(layers)}")
        elif layers != [18.2, 7.1, 1.8, 2.9]:
            err("layer sequence must be [18.2, 7.1, 1.8, 2.9] per paper Methods")

    if need(cfg, "material.n_periods", int) != 16:
        err("material.n_periods must be 16")
    ft = need(cfg, "material.film_thickness_nm", (int, float))
    if ft is not None and abs(ft - 595) > 1e-6:
        err("film_thickness_nm must be 595 (paper value; known != 16*30)")
    # al_fraction must exist and be either null (pre-calibration) or in [0.2, 0.7]
    mat = need(cfg, "material", dict) or {}
    if "al_fraction" not in mat:
        err("material.al_fraction key must exist (null until Phase 2 calibrates it)")
    elif mat["al_fraction"] is not None and not (0.2 <= mat["al_fraction"] <= 0.7):
        err("material.al_fraction outside plausible range [0.2, 0.7]")

    if need(cfg, "chi2.broadening_gamma_meV", (int, float)) != 5:
        err("chi2.broadening_gamma_meV must be 5")
    if need(cfg, "chi2.k_integration_bz_fraction", (int, float)) != 0.1:
        err("chi2.k_integration_bz_fraction must be 0.1")
    scan = need(cfg, "chi2.pump_scan_nm", list)
    if scan and (scan[0] != 700 or scan[1] != 1700):
        err("chi2.pump_scan_nm must be [700, 1700]")
    ep = need(cfg, "chi2.interband_dipole.kane_Ep_eV", (int, float))
    if ep is not None and not (25.0 <= ep <= 29.0):
        err("kane_Ep_eV outside the plan's 25-29 eV literature window")
    ff = need(cfg, "chi2.fill_factor", dict) or {}
    if ff and abs(ff.get("qw_region_nm", 0) / ff.get("period_nm", 1) - 0.593) > 0.01:
        err("fill_factor ratio should be ~0.593 (17.8/30, Ref38 convention)")

    pil = need(cfg, "metasurface.pillar", dict) or {}
    if pil.get("height_nm") != 390 or pil.get("radius_nm") != 230:
        err("metasurface pillar must be height 390 nm, radius 230 nm")
    per = need(cfg, "metasurface.period_nm", dict) or {}
    if per.get("x") != 891 or per.get("y") != 650:
        err("metasurface periods must be x=891, y=650 nm")
    idx = need(cfg, "metasurface.mqw_index_780nm", list)
    if idx and (abs(idx[0] - 3.39) > 1e-6 or abs(idx[1] - 0.11) > 1e-6):
        err("mqw_index_780nm must be [3.39, 0.11]")

    for k in ("wide_well_nm", "narrow_well_nm", "coupling_barrier_nm",
              "al_fraction_delta", "grading_width_nm"):
        v = need(cfg, f"bnn.input_space.{k}", list)
        if v is not None and (len(v) != 2 or v[0] >= v[1]):
            err(f"bnn.input_space.{k} must be [lo, hi] with lo < hi")

    if need(cfg, "calibration.target_E22_eV", (int, float)) != 1.58:
        err("calibration.target_E22_eV must be 1.58")

    if "fig2e_anchors" not in cfg:
        err("fig2e_anchors key must exist (empty until Phase 4 digitization)")

    if ERRORS:
        print(f"CONFIG INVALID ({len(ERRORS)} problems):")
        for e in ERRORS:
            print("  -", e)
        sys.exit(1)
    print(f"CONFIG OK: {args.config}")
    sys.exit(0)


if __name__ == "__main__":
    main()
