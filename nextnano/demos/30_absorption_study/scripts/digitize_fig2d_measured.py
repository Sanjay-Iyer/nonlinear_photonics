"""Reproducible digitization of the MEASURED points in Fig. 2d of arXiv:2602.23246v1.

Reads the embedded Fig. 2d raster straight out of the paper PDF (page 7, image Im1.png,
4441 x 1122 px, SHA-256 checked). It calibrates the three axes from the tick marks it
detects, finds the square markers of the three measured series by color, and writes:

    reference/paper_fig2d_measured.csv
    reference/paper_fig2d_measured_digitization.json
    plots/30A_fig2d_digitization_overlay.png

There is no manual clicking. The constants below are readings of the figure's own
printed tick labels, legend colors and legend position. Method and uncertainty:
reference/FIG2D_DIGITIZATION.md.

    <python> nextnano/demos/30_absorption_study/scripts/digitize_fig2d_measured.py
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import sys

import numpy as np
from scipy import ndimage

DEMO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PDF = DEMO_ROOT.parents[2] / "2602.23246v1.pdf"
PAGE_INDEX, IMAGE_NAME = 6, "Im1.png"
EXPECTED_IMAGE_SHA256 = "865de45249bc9cb2ba77f012b173b8695ccd79a6d4cde4032de68da54373c288"

# Readings of the printed figure (not fitted):
X_LEFT_SPINE_NM, X_TICK_STEP_NM = 400.0, 50.0        # ticks every 50 nm, 400 nm on the left spine
RIGHT_TICK_STEP, RIGHT_LOWEST_MAJOR = 25.0, 0.0      # SH axis: long ticks labelled 0..200, short between
LEFT_MAJOR_STEP_PM_PER_V = 1000.0                    # chi2 axis: bottom spine is 0.00, long ticks 1000..4000
SERIES = {  # legend order and the fill color of each series' square markers
    "80pd_sample": (247, 66, 66),
    "AlGaAs_control": (206, 156, 0),
    "GaAs_control": (24, 107, 222),
}
COLOR_TOLERANCE = 40.0
LEGEND_BOX_PX = (3540, 100, 4160, 310)               # x0, y0, x1, y1 of the legend; markers inside are ignored
REFERENCE_SERIES = "80pd_sample"                     # complete, isolated markers: defines the wavelengths
NOMINAL_STEP_NM = 10.0
SIM_CURVE_GRAY, SIM_GRAY_TOL, SIM_MIN_COMPONENT_PX = 82, 10, 20  # the dashed "Simulation" line is RGB (82,82,82)


def extract_image(pdf: Path) -> tuple[bytes, np.ndarray]:
    from pypdf import PdfReader
    from PIL import Image
    page = PdfReader(str(pdf)).pages[PAGE_INDEX]
    matches = [img for img in page.images if img.name == IMAGE_NAME]
    if len(matches) != 1:
        raise ValueError(f"expected one {IMAGE_NAME} on page {PAGE_INDEX + 1}, found {len(matches)}")
    data = matches[0].data
    rgb = np.asarray(Image.open(io.BytesIO(data)).convert("RGB")).astype(int)
    return data, rgb


def runs(mask_1d: np.ndarray) -> list[tuple[int, int]]:
    idx = np.flatnonzero(mask_1d)
    if not len(idx):
        return []
    groups = np.split(idx, np.flatnonzero(np.diff(idx) > 1) + 1)
    return [(int(g[0]), int(g[-1])) for g in groups]


def spines(dark: np.ndarray) -> dict:
    h, w = dark.shape
    rows = runs(dark.sum(axis=1) > 0.6 * w)
    cols = runs(dark.sum(axis=0) > 0.6 * (rows[-1][0] - rows[0][1]))
    if len(rows) != 2 or len(cols) != 2:
        raise ValueError(f"expected a rectangular frame, got rows {rows} cols {cols}")
    return {"top": rows[0], "bottom": rows[1], "left": cols[0], "right": cols[1]}


def tick_centres(counts: np.ndarray, min_len: int, max_width: int = 4) -> list[tuple[float, int]]:
    """(centre, length) of short perpendicular dark runs next to a spine."""
    out = []
    for a, b in runs(counts >= min_len):
        if b - a + 1 <= max_width:
            out.append(((a + b) / 2, int(counts[a:b + 1].max())))
    return out


def calibrate(rgb: np.ndarray) -> dict:
    dark = rgb.sum(axis=2) < 250
    s = spines(dark)
    top, bottom, left, right = s["top"][1], s["bottom"][0], s["left"][1], s["right"][0]
    # x axis: all ticks (50 nm apart) inside the frame above the bottom spine
    counts = dark[bottom - 26:bottom, :].sum(axis=0)
    ticks = [(c, n) for c, n in tick_centres(counts, 15) if left + 5 < c < right - 5]
    xs = np.array([c for c, _ in ticks])
    spacing = float(np.median(np.diff(xs)))
    x_left = (s["left"][0] + s["left"][1]) / 2
    lam = X_LEFT_SPINE_NM + X_TICK_STEP_NM * np.round((xs - x_left) / spacing)
    xfit = np.polyfit(lam, xs, 1)
    x_resid = xs - np.polyval(xfit, lam)
    # right (SH) axis: ticks inside the frame left of the right spine
    counts = dark[:, right - 36:right].sum(axis=1)
    rticks = [(c, n) for c, n in tick_centres(counts, 15) if top + 5 < c < bottom - 5]
    longest = max(n for _, n in rticks)
    lowest_major = max(c for c, n in rticks if n >= longest - 2)
    ry = np.array([c for c, _ in rticks])
    rspacing = float(np.median(np.diff(np.sort(ry))))
    rval = RIGHT_LOWEST_MAJOR + RIGHT_TICK_STEP * np.round((lowest_major - ry) / rspacing)
    rfit = np.polyfit(rval, ry, 1)
    r_resid = ry - np.polyval(rfit, rval)
    # left (chi2) axis: long ticks right of the left spine, plus the bottom spine at 0.00
    counts = dark[:, left + 1:left + 37].sum(axis=1)
    lticks = [(c, n) for c, n in tick_centres(counts, 15) if top + 5 < c < bottom - 5]
    longest = max(n for _, n in lticks)
    majors = sorted((c for c, n in lticks if n >= longest - 2), reverse=True)
    y0 = (s["bottom"][0] + s["bottom"][1]) / 2
    ly = np.array([y0, *majors])
    lval = LEFT_MAJOR_STEP_PM_PER_V * np.arange(len(ly))
    lfit = np.polyfit(lval, ly, 1)
    l_resid = ly - np.polyval(lfit, lval)
    return {"spines_px": s, "x_fit_px_per_nm": xfit.tolist(), "x_ticks": len(xs),
            "x_fit_max_residual_px": float(np.max(abs(x_resid))),
            "right_fit_px_per_unit": rfit.tolist(), "right_ticks": len(ry),
            "right_fit_max_residual_px": float(np.max(abs(r_resid))),
            "left_fit_px_per_pm_per_V": lfit.tolist(), "left_ticks": len(ly),
            "left_fit_max_residual_px": float(np.max(abs(l_resid)))}


def px_to_nm(x, cal):
    a, b = cal["x_fit_px_per_nm"]
    return (np.asarray(x, float) - b) / a


def px_to_sh(y, cal):
    a, b = cal["right_fit_px_per_unit"]
    return (np.asarray(y, float) - b) / a


def nm_to_px(lam, cal):
    return np.polyval(cal["x_fit_px_per_nm"], lam)


def chi2_to_px(v, cal):
    return np.polyval(cal["left_fit_px_per_pm_per_V"], v)


def series_mask(rgb, colour, cal):
    dist = np.sqrt(((rgb - np.array(colour)) ** 2).sum(axis=2))
    mask = dist < COLOR_TOLERANCE
    s = cal["spines_px"]
    frame = np.zeros_like(mask)
    frame[s["top"][1] + 3:s["bottom"][0] - 2, s["left"][1] + 3:s["right"][0] - 2] = True
    x0, y0, x1, y1 = LEGEND_BOX_PX
    frame[y0:y1, x0:x1] = False
    return mask & frame


def reference_markers(rgb, cal):
    """Complete square markers of the reference series: centres and marker size."""
    opened = ndimage.binary_opening(series_mask(rgb, SERIES[REFERENCE_SERIES], cal), np.ones((9, 9), bool))
    labels, n = ndimage.label(opened)
    boxes = ndimage.find_objects(labels)
    sizes = np.array([[b[1].stop - b[1].start, b[0].stop - b[0].start] for b in boxes])
    side = int(np.median(sizes))
    keep = [b for b, (w, h) in zip(boxes, sizes) if abs(w - side) <= 2 and abs(h - side) <= 2]
    centres = sorted(((b[1].start + b[1].stop - 1) / 2, (b[0].start + b[0].stop - 1) / 2) for b in keep)
    if len(keep) != n:
        raise ValueError(f"{REFERENCE_SERIES}: {n - len(keep)} marker(s) are not complete squares")
    return centres, side


def locate_in_band(mask, xc, side):
    """Vertical centre of the square marker in a narrow central column band around xc.

    Rows count as marker rows when >= 80% of the band is the series color (a
    connecting line is narrow and fails this). If the run is shorter than the marker,
    the hidden edge is the one touching another series' color, and the centre is taken
    from the visible edge.
    """
    half = max(3, side // 2 - 5)
    band = mask[:, int(round(xc)) - half:int(round(xc)) + half + 1]
    full = band.sum(axis=1) >= 0.8 * band.shape[1]
    candidates = [(b - a + 1, a, b) for a, b in runs(full)]
    if not candidates:
        return None
    length, a, b = max(candidates)
    if length > side + 2:
        raise ValueError(f"marker run of {length} px at x={xc:.0f} is taller than a marker ({side})")
    if length >= side - 2:
        return (a + b) / 2, "none"
    return a, b, length


def detect(rgb, cal):
    ref, side = reference_markers(rgb, cal)
    background = rgb.sum(axis=2) > 3 * 235
    rows = []
    for name, colour in SERIES.items():
        mask = series_mask(rgb, colour, cal)
        for i, (xc, yc_ref) in enumerate(ref):
            found = locate_in_band(mask, xc, side)
            if found is None:
                rows.append({"series": name, "index": i, "x_px": xc, "y_px": np.nan, "hidden_edge": "not found"})
                continue
            if len(found) == 2:
                y, hidden = found
            else:
                a, b, _ = found
                above = background[a - 2, int(round(xc))]
                below = background[b + 2, int(round(xc))]
                if above and not below:
                    y, hidden = a + (side - 1) / 2, "bottom"
                elif below and not above:
                    y, hidden = b - (side - 1) / 2, "top"
                else:
                    raise ValueError(f"{name} at x={xc:.0f}: cannot tell which edge is hidden")
            rows.append({"series": name, "index": i, "x_px": xc, "y_px": float(y), "hidden_edge": hidden})
    return rows, side


def trace_simulated(rgb, cal):
    """Column-by-column centre of the dashed gray 'Simulation' curve (NaN in dash gaps)."""
    s = cal["spines_px"]
    grey = np.all(np.abs(rgb - SIM_CURVE_GRAY) <= SIM_GRAY_TOL, axis=2)
    frame = np.zeros_like(grey)
    frame[s["top"][1] + 3:s["bottom"][0] - 2, s["left"][1] + 3:s["right"][0] - 2] = True
    labels, n = ndimage.label(grey & frame)
    sizes = ndimage.sum(np.ones_like(labels), labels, index=np.arange(1, n + 1))
    keep = np.isin(labels, 1 + np.flatnonzero(sizes >= SIM_MIN_COMPONENT_PX))
    xs, ys = [], []
    for x in range(s["left"][1] + 3, s["right"][0] - 2):
        rows_ = np.flatnonzero(keep[:, x])
        if len(rows_):
            xs.append(x)
            ys.append(rows_.mean())
    a, b = cal["left_fit_px_per_pm_per_V"]
    return px_to_nm(np.array(xs), cal), (np.array(ys) - b) / a


def overlay(rgb, cal, rows, simulated_csv: Path, out_png: Path, traced=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(15, 4.4), dpi=150)
    ax.imshow(rgb.astype(np.uint8), interpolation="nearest")
    styles = {"80pd_sample": "#7f0000", "AlGaAs_control": "#4d3b00", "GaAs_control": "#001a4d"}
    for name, colour in styles.items():
        pts = [(r["x_px"], r["y_px"]) for r in rows if r["series"] == name and np.isfinite(r["y_px"])]
        ax.plot(*zip(*pts), "o", ms=11, mfc="none", mec=colour, mew=1.6, label=f"detected: {name}")
    if traced is not None:
        ax.plot(nm_to_px(traced[0], cal), chi2_to_px(traced[1], cal), ".", color="#00c0c0", ms=1.2,
                label="traced simulated curve (this script)")
    sim = np.loadtxt(simulated_csv, delimiter=",", skiprows=1)
    ax.plot(nm_to_px(sim[:, 0], cal), chi2_to_px(sim[:, 1], cal), "+", color="#00a000", ms=9, mew=1.6,
            label="existing 45-point simulated-curve digitization (Demo 26/28)")
    x0, y0, x1, y1 = LEGEND_BOX_PX
    ax.add_patch(plt.Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, ls=":", ec="grey", lw=1))
    ax.set_axis_off()
    ax.legend(loc="upper center", bbox_to_anchor=(0.30, 0.985), fontsize=8, framealpha=0.95)
    ax.set_title("30A — Fig. 2d digitization check on the paper's own raster: detected measured markers (circles), "
                 "traced simulated curve (cyan) and the older 45-point eye digitization (+)", fontsize=10)
    fig.tight_layout()
    fig.savefig(out_png)
    plt.close(fig)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    args = parser.parse_args(argv)
    data, rgb = extract_image(args.pdf)
    digest = hashlib.sha256(data).hexdigest()
    if EXPECTED_IMAGE_SHA256 != "SET_ON_FIRST_RUN" and digest != EXPECTED_IMAGE_SHA256:
        raise SystemExit(f"embedded image hash {digest} differs from the recorded {EXPECTED_IMAGE_SHA256}")
    cal = calibrate(rgb)
    rows, side = detect(rgb, cal)
    for r in rows:
        r["digitized_wavelength_nm"] = float(px_to_nm(r["x_px"], cal))
        r["nominal_wavelength_nm"] = float(NOMINAL_STEP_NM * round(r["digitized_wavelength_nm"] / NOMINAL_STEP_NM))
        r["normalized_sh_arb"] = float(px_to_sh(r["y_px"], cal))
    px_per_nm = cal["x_fit_px_per_nm"][0]
    px_per_unit = abs(cal["right_fit_px_per_unit"][0])
    residual = max(abs(r["digitized_wavelength_nm"] - r["nominal_wavelength_nm"]) for r in rows)
    ref = DEMO_ROOT / "reference"
    with (ref / "paper_fig2d_measured.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["series", "nominal_wavelength_nm", "digitized_wavelength_nm", "normalized_sh_arb",
                    "x_px", "y_px", "hidden_edge"])
        for r in rows:
            w.writerow([r["series"], f"{r['nominal_wavelength_nm']:.0f}", f"{r['digitized_wavelength_nm']:.2f}",
                        f"{r['normalized_sh_arb']:.2f}", f"{r['x_px']:.1f}", f"{r['y_px']:.1f}", r["hidden_edge"]])
    meta = {"source": {"pdf": args.pdf.name, "page": PAGE_INDEX + 1, "image": IMAGE_NAME,
                       "image_sha256": digest, "image_size_px": [int(rgb.shape[1]), int(rgb.shape[0])]},
            "calibration": cal, "marker_side_px": side,
            "resolution": {"px_per_nm": px_per_nm, "px_per_sh_unit": px_per_unit},
            "max_distance_from_nominal_10nm_grid_nm": residual,
            "counts": {name: sum(1 for r in rows if r["series"] == name and np.isfinite(r["y_px"])) for name in SERIES},
            "hidden_edges": sum(1 for r in rows if r["hidden_edge"] not in ("none",)),
            "script": "scripts/digitize_fig2d_measured.py"}
    lam_t, chi_t = trace_simulated(rgb, cal)
    with (ref / "paper_fig2d_simulated_traced.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["wavelength_nm", "simulated_abs_chi2_pm_per_V"])
        for x, y in zip(lam_t, chi_t):
            w.writerow([f"{x:.2f}", f"{y:.1f}"])
    eye = np.loadtxt(ref / "paper_fig2d_simulated.csv", delimiter=",", skiprows=1)
    near = [(lam, val, float(np.interp(lam, lam_t, chi_t))) for lam, val in eye
            if np.min(np.abs(lam_t - lam)) <= 1.0]  # only where the trace has data within 1 nm
    diffs = np.array([v - t for _, v, t in near])
    meta["simulated_trace"] = {
        "columns_with_curve": int(len(lam_t)), "wavelength_range_nm": [float(lam_t.min()), float(lam_t.max())],
        "gray_level": SIM_CURVE_GRAY, "note": "dash gaps and marker-covered columns have no points",
        "eye_45_point_minus_trace_pm_per_V": {"points_compared": len(near),
                                              "rms": float(np.sqrt(np.mean(diffs ** 2))),
                                              "max_abs": float(np.max(np.abs(diffs))),
                                              "worst_wavelength_nm": float(near[int(np.argmax(np.abs(diffs)))][0])}}
    (ref / "paper_fig2d_measured_digitization.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    overlay(rgb, cal, rows, ref / "paper_fig2d_simulated.csv", DEMO_ROOT / "plots" / "30A_fig2d_digitization_overlay.png",
            traced=(lam_t, chi_t))
    print(f"simulated curve traced in {len(lam_t)} columns; 45-point eye file vs trace: "
          f"rms {meta['simulated_trace']['eye_45_point_minus_trace_pm_per_V']['rms']:.0f} pm/V, "
          f"max {meta['simulated_trace']['eye_45_point_minus_trace_pm_per_V']['max_abs']:.0f} pm/V "
          f"at {meta['simulated_trace']['eye_45_point_minus_trace_pm_per_V']['worst_wavelength_nm']:.0f} nm")
    print(f"image sha256 {digest}")
    print(f"axes: x {cal['x_ticks']} ticks (max resid {cal['x_fit_max_residual_px']:.2f} px), "
          f"SH {cal['right_ticks']} ticks ({cal['right_fit_max_residual_px']:.2f} px), "
          f"chi2 {cal['left_ticks']} ticks ({cal['left_fit_max_residual_px']:.2f} px)")
    print(f"{px_per_nm:.3f} px/nm, {px_per_unit:.3f} px per SH unit, marker {side} px; "
          f"max distance from the 10 nm grid {residual:.2f} nm")
    for name in SERIES:
        vals = [(r["nominal_wavelength_nm"], round(r["normalized_sh_arb"], 1), r["hidden_edge"])
                for r in rows if r["series"] == name]
        print(name, vals)
    return 0


if __name__ == "__main__":
    sys.exit(main())
