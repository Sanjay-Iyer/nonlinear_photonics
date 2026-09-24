# Demo 30 provenance

Everything below was copied into Demo 30 on 2026-09-24. Demo 30 does not import or read
any other demo at runtime. The originals are untouched.

## Copied code

Source: `nextnano/demos/28_kspace_chi2_study/`, tracked and clean at commit `8f8e1d7`
(the last commit touching `chi2/`; repository HEAD was `061c10c`).

| Demo 30 file | Source file | SHA-256 of the source | Modified? |
|---|---|---|---|
| `demo30/parse_nextnano.py` | `chi2/parse_nextnano.py` | `0f0577055b39c6ab33aa20e4b6d5965c18b894cde7a1176d26a0ba112efaa2a2` | no |
| `demo30/matrix_elements.py` | `chi2/matrix_elements.py` | `a655fc37046f7f047a5a7c40c2f017fa87d96d713893407ffe235ebc3bc67407` | no |
| `demo30/input_builder.py` | `chi2/input_builder.py` | `e3209cbaebda5951dae5832fe7e69d6408d38f238669da298780e692e7dea6df` | **yes**, see below |
| `demo30/k_integration.py` | `chi2/k_integration.py` | `c0e2085e7c33817a6583712cac17637bef45ae565fbdbe8f310bbfb7f85adbe6` | no |
| `demo30/equation2.py` | `chi2/equation2.py` | `6f69da8fe002f7954f6f5013712522c9e63445f7aa5e7ac447e608e36283a460` | no (a test asserts this hash) |
| `demo30/diagnostics.py` | `chi2/diagnostics.py` | `864ca3af9b26ec8ad848b4d0f081bc22be061bc10e78da54f47b383d847985c8` | no |
| `demo30/artifacts.py` | `chi2/artifacts.py` | `543f488acc2b7f54b3ec65afd41160d6377773433e7147e75b5123f2a14a575d` | no |
| `scripts/audit_isolation.py` | `scripts/audit_dependencies.py` | `be05cb9f05c7cc4bfe9592d17e12e1eb6f60644dd5347d0a3d56ad319cc9a738` | rewritten for Demo 30 (same audit-hook method) |

**The one change to copied physics code.** `build_inputs(root)` became
`build_inputs(kp8_root, singleband_root)`. Demo 28 kept both raw runs under one folder
with fixed subfolder names. In Demo 30 they are two separately registered packages. The
parsing, pair assignment, anchoring and matrices are unchanged. The regression test
proves the spectrum is the same.

The package is named `demo30` rather than `chi2`. Demo 28 and Demo 29 both use `chi2`,
and that name must not shadow across demos.

## Copied reference data

| Demo 30 file | Source | SHA-256 | Notes |
|---|---|---|---|
| `reference/paper_fig2d_simulated.csv` | Demo 28 `validation/paper_fig2d.csv` | `87f4b624ff576eca7ed1293674f95ceba8846ae271b95989313083ecc3cd99cb` | 45-point eye digitization of the **simulated** Fig. 2d curve (renamed only) |
| `reference/demo26_baseline_reference.csv` | Demo 28 `validation/demo26_baseline_reference.csv` | `cd2afab14c96b874314c011535d2a116799ca3416be54ce764695aa70605d469` | historical complex χ(2); Demo 28A's regression gate |
| `reference/prior_condensed_baseline_summary.json` | Demo 28 `validation/prior_condensed_baseline_summary.json` | `f3d61b23521d813d58cbc67d2aedd21381fbaae079b26e1008faf457145406b9` | Re-zero positions gate |
| `reference/demo28A_chi2_spectrum.csv` | Demo 28 `outputs/28A_baseline/chi2_results/chi2_spectrum.csv` | `1d30227d5caca911241fac4372d6d35b6f52596f9eade54dd5ea835dca64681e` | the Demo 28A spectrum that Demo 30's control must reproduce |

## Raw data (local only, never in Git)

Registered on 2026-09-24 with `nextnano/scripts/raw_data.py register`. These are copies:
the historical folders were not moved or edited.

| Run ID | Historical source (tracked) | Files | SHA256SUMS digest |
|---|---|---|---|
| `D020_2026-08-20_sb-case04-graded-300K` | `docs/case_04` | 50 | `add43763110b…` |
| `D023_2026-09-04_kp8-disp-k0p10pia-n301-300K` | `demo_results/demo23/raw/production_y_n301_k0100` | 738 | `8456d47381d3…` |
| `D023_2026-09-04_kp8-disp-k0p125pia-n301-300K` (optional, 30F) | `demo_results/demo23/raw/kmax_y_n301_k0125` | 738 | `8bbd6083fb1b…` |

The 0.125·π/a deck differs from the control deck only in the k endpoint. Its k = 0
spectrum and composition files are byte-identical to the control run's.

- **Same bytes as Demo 28A.** At registration the eight files Demo 28A consumes were
  compared with Demo 28's `outputs/28A_baseline/raw_manifest.json`, and all eight are
  byte-identical.
- **Same decks.** Both decks are also identical to the copies in Demo 28 `nextnano/raw_results/`.
- **Pinned.** The exact hashes are in `inputs/raw_data.lock.json`. The registration
  metadata is in `inputs/registration/`.

## New data created for Demo 30

- **Fig. 2d, measured and traced.** Two files come from a reproducible digitization of the
  embedded Fig. 2d raster (image SHA-256 `865de452…`) by `scripts/digitize_fig2d_measured.py`;
  details in `reference/FIG2D_DIGITIZATION.md`:
  - `reference/paper_fig2d_measured.csv`: the measured points;
  - `reference/paper_fig2d_simulated_traced.csv`: the traced simulated curve.
- **Background refractive indices.** Values and sources are in `config/demo30.json` →
  `background_index`, read from the refractiveindex.info database on 2026-09-24.
- **Work-laptop package for 0.2·π/a** (`work_laptop/`):
  - two decks rendered by `kmax_run.py prepare` from the locked control deck, with exactly
    two lines changed (checked by the script);
  - `control_reference_nodes.json`: the control's 8-band energies at four shared k nodes,
    as derived numbers used by the WORK-side validation;
  - `run_plan.json`: deck hashes and the Free-parser check.
- **Failed Demo 28K run** (`nextnano_pro_raw_results/`): inspected read-only on 2026-09-24.
  It is not copied, registered or modified.
