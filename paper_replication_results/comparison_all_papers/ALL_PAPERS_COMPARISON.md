# All-Paper Replication Comparison

## Executive comparison

| Paper | Objective | Material system | Quantum-well design | Repo models used | Replication status |
| --- | --- | --- | --- | --- | --- |
| Quantum-Well-Metasurface | Combine ACQW material chi^(2) with metasurface field engineering | GaAs/Al0.55Ga0.45As plus TiO2 metasurface | 16 periods of 18.2/7.1/1.8/2.9 nm ACQW, 595 nm optical film | Aestimo, kdotpy, BDD context, GRCWA, deep ensemble | Strongest completed track; EM/metasurface mostly reproduced; material chi^(2) magnitude not reproduced |
| 2602.23246v1 enhanced interband nonlinearities | Demonstrate enhanced interband response from coupled wells and realistic grown structure | GaAs/Al0.55Ga0.45As | Same 16-period ACQW used as the metasurface material anchor | Aestimo, kdotpy, BDD context, deep ensemble | Partially reproduced through shared ACQW stack; no standalone report existed before this layer |
| APL 2023 interband chi^(2) ACQW | Theoretical ACQW chi^(2) design rules versus asymmetry, width, and barrier | GaAs/Al0.4Ga0.6As | d1 = D(1+s)/2, d2 = D(1-s)/2; D = 5, 7.5, 10, 12.5 nm; tb = 1 nm baseline | Aestimo, BDD, diagnostic postprocessing; kdotpy not counted | Electronic states reproduced; relative chi^(2) partially reproduced; absolute chi^(2) frozen |
| Schaefer 2024 type-II AQW | Use type-II alignment to increase interband charge shift and chi^(2) | InP/AlGaInAs family | Multiple type-I/type-II AQW designs; details not yet extracted into repo configs | None found | Not yet reproduced |

## Paper-reported versus repo-reproduced results

| Quantity | Quantum-Well-Metasurface | 2602.23246v1 | APL 2023 | Schaefer 2024 |
| --- | --- | --- | --- | --- |
| E11 | Paper/companion anchor about 1.49 eV; repo Aestimo 1.496/1.499 eV, kdotpy 1.507 eV | Same ACQW anchor; repo values shared | Paper does not publish exact state energies; repo reports state sweeps | Not found in repo |
| E22 | Paper/companion context about 1.62 eV; repo Aestimo 1.657/1.674 eV, kdotpy 1.669 eV | Same ACQW anchor; repo values shared | Near s = 0.45 and D = 10 nm, repo BDD 1.61678 eV and Aestimo 1.61814 eV; no exact paper target | Not found in repo |
| Localization | Graded repo structure matches key Fig. 2a-style claims | Shared ACQW localization tested | HH2 relocation near s about 0.45 reproduced by Aestimo and BDD | Not found in repo |
| Oscillator strengths / transition dipoles | Interband overlaps and Kane/DFT dipole anchors used; exact author states missing | Same | Pathway ledgers and r(e,hh) recorded; absolute normalization frozen | Not found in repo |
| chi^(2) peak position | Paper simulated near 1500 nm; repo about 1438-1482 nm depending route | Similar near-1500 nm reproduction | Spectral resonance locations partially reproduced; mean errors about 0.052-0.061 eV | Not found in repo |
| chi^(2) magnitude | Paper MQW about 1.6 nm/V at 1.57 um; repo coherent about 0.062 nm/V at 1.57 um | Paper scale about nm/V; repo coherent low but electron channel about 2.34 nm/V | Relative only partially reproduced; absolute chi^(2) not audited | Paper text mentions about 20 to 1.60e3 pm/V; repo not reproduced |
| Metasurface resonances | Paper GMR B 1567-1580 nm; repo 1574 nm | Not the main focus | Not applicable | Not applicable |
| Field enhancement | Paper 57x and 11.5x; repo Q-corrected about 76x and 14x | Not the main focus | Not applicable | Not applicable |
| Effective MQW+MS chi^(2) | Paper about 14 nm/V; repo 2.23 nm/V using coherent material value | Not the main focus | Not applicable | Not applicable |

## Agreement levels

| Paper | Agreement level | Main reason |
| --- | --- | --- |
| Quantum-Well-Metasurface | High for electronic energies and metasurface EM; low for coherent material chi^(2) magnitude | Electron/hole channel cancellation in envelope-function states leaves coherent chi^(2) far below paper |
| 2602.23246v1 | Moderate/partial | The shared ACQW structure and transition energies are tested, but a standalone full-paper reproduction is not present |
| APL 2023 | Partial | Electronic states and mechanisms are validated, but several relative chi^(2) figure trends remain unresolved |
| Schaefer 2024 | Not started | No repo implementation or extracted config found |

## Main discrepancies

| Theme | Affected papers | Description |
| --- | --- | --- |
| Electron-hole cancellation in chi^(2) | Quantum-Well-Metasurface, 2602.23246v1 | Individual electron/hole channels can be nm/V scale, but the coherent sum nearly cancels in local envelope-function states. |
| Missing author simulation inputs | Quantum-Well-Metasurface, 2602.23246v1, APL 2023 | Exact Nextnano inputs, material databases, band offsets, state wavefunctions, and intermediate matrix elements are absent. |
| Figure-level relative chi^(2) mismatch | APL 2023 | Fig. 2a peaks are late, Fig. 5a optimum differs under baseline, and Fig. 5b is internally inconsistent/not reproduced. |
| No implementation | Schaefer 2024 | The PDF exists but no scripts/configs/results were found for the type-II InP/AlGaInAs paper. |

## Missing work and next actions

| Priority | Action | Applies to |
| --- | --- | --- |
| 1 | Request or obtain author intermediate data: raw wavefunctions, state energies, centroids, overlaps, separated electron/hole pathway terms, material database, and input decks | Quantum-Well-Metasurface, 2602.23246v1, APL 2023 |
| 2 | Create a standalone 2602.23246 reproduction report or pipeline if the goal is to discuss it independent of the metasurface paper | 2602.23246v1 |
| 3 | Keep the coherent chi^(2) versus channel-magnitude distinction explicit in every discussion | Quantum-Well-Metasurface, 2602.23246v1 |
| 4 | Do not adopt the APL Qc=0.60/Qv=0.40 diagnostic as baseline unless author evidence supports it | APL 2023 |
| 5 | Extract a full target manifest from the Schaefer 2024 PDF and implement a first BDD/envelope reproduction | Schaefer 2024 |
| 6 | Add machine-readable provenance for this documentation layer if it becomes a release artifact | All |

## Evidence paths

- Per-paper summaries:
  - `../01_quantum_well_metasurface/SUMMARY.md`
  - `../02_enhanced_interband_nonlinearities_2602_23246/SUMMARY.md`
  - `../03_apl2023_interband_chi2_acqw/SUMMARY.md`
  - `../04_schaefer2024_type_ii_aqw/SUMMARY.md`
- Main metasurface report:
  `../../replication/qw_metasurface/REPORT.md`
- APL final status:
  `../../git/aestimo/paper/apl_2023/releases/apl2023_public_reproduction_final_v1/docs/APL_2023_FINAL_PUBLIC_REPRODUCTION_STATUS.md`
- Solver consensus:
  `../../git/aestimo/paper/reference_data/acqw_solver_consensus_v1/`
