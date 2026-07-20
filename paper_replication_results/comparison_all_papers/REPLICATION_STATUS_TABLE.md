# Replication Status Table

This table is optimized for quick expert discussion. It separates publication
claims from repo-generated results and explicitly marks unknowns.

| Paper | Paper-reported result class | Repo-generated result class | Agreement | Blocker |
| --- | --- | --- | --- | --- |
| Quantum-Well-Metasurface | MQW chi^(2) about 1.6 nm/V at 1.57 um; MQW+MS about 14 nm/V; GMR B 1567-1580 nm; enhancement 57x/11.5x | Aestimo/kdotpy E22 agree; chi^(2) peak position reproduced; GMR B 1574 nm; Q-corrected enhancement about 76x/14x; coherent MQW chi^(2) about 0.062 nm/V at 1.57 um | Strong for EM and peak placement; weak for coherent chi^(2) magnitude | Missing exact author states and DFT/HSE06-corrected intermediate quantities |
| 2602.23246v1 | Same 16-period x = 0.55 ACQW; E11 about 1.49 eV, E22 about 1.62 eV; graded-interface chi^(2) context | Shared Aestimo/kdotpy stack reproduces E11/E22 internally; chi^(2) peak position near expected region; coherent chi^(2) low | Partial | No standalone pipeline/report; exact author inputs absent |
| APL 2023 | GaAs/Al0.4Ga0.6As ACQW chi^(2) versus asymmetry, barrier, width, and spectrum | Aestimo and BDD reproduce HH2 relocation; relative chi^(2) partially reproduced; 35 tests passed; absolute chi^(2) frozen | Partial | Public figure data insufficient; exact Nextnano/material conventions absent |
| Schaefer 2024 | Type-II InP/AlGaInAs AQWs predicted about 20 to 1.60e3 pm/V depending design/application | Not found in repo | Not started | Need target manifest, material parameters, and implementation |

## Model contribution matrix

| Model | Quantum-Well-Metasurface | 2602.23246v1 | APL 2023 | Schaefer 2024 |
| --- | --- | --- | --- | --- |
| Aestimo | Main electronic solver and chi^(2) route | Shared ACQW state/chi^(2) route | Main electronic solver | Not used |
| BDD | Prior consensus context | Prior consensus context | Independent state/pathway check | Not used |
| kdotpy | 8-band energy cross-check; hybrid chi^(2) route | Shared 8-band check | Not counted/testable for APL gate | Not used |
| GRCWA | Main metasurface solver | Not central | Not applicable | Not applicable |
| BNN/deep ensemble | Surrogate for E22, Delta z, chi^(2) peak, peak wavelength | Shared design-space surrogate context | Not used | Not used |

## Discussion-ready one-line conclusions

- The metasurface electromagnetic replication is strong; the material chi^(2)
  coherent magnitude is the main failure.
- The 2602.23246 paper is currently represented as a companion materials anchor,
  not as an isolated complete replication.
- The APL 2023 state physics is validated, but full relative/absolute chi^(2)
  reproduction is author-data limited.
- The Schaefer 2024 type-II AQW paper has not yet been modeled in this repo.
