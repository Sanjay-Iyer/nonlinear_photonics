# Modeling-Only Replication Plan: Enhanced Interband Optical Nonlinearities

This document provides a highly detailed, step-by-step computational blueprint to replicate the modeling, simulation, and parameter extraction pipelines from Ramesh et al., *"Enhanced Interband Optical Nonlinearities from Coupled Quantum Wells"*. 

---

## Technical Summary of Modeling Pipelines

| Pipeline | Target Figures | Tools | Core Physics / Math |
| :--- | :--- | :--- | :--- |
| **1. QW & $\chi^{(2)}$** | Fig. 2a, 2b, 2e | Nextnano or Custom 1D Solver | Schrödinger-Poisson, Kane $k \cdot p$ theory, $k_{\parallel}$ integration |
| **2. RCWA Metasurface** | Fig. 3c (Resonances) | GRCWA (or S⁴ / Meep) | Guided-Mode Resonances (GMR), S-matrix propagation |
| **3. Modal Overlap $\beta$** | Fig. 3d, 3f | GRCWA + Numerical Integration | Spatial overlap of $\omega$ and $2\omega$ local fields in MQW volume |
| **4. Comparison & FDTD** | Fig. 11 (Extraction) | Tidy3D or Meep | Pulse propagation, time-domain non-linear polarization |

---

## Pipeline 1: Quantum Well Electronic Structure & $\chi^{(2)}$

This pipeline reproduces the conduction and valence band alignments, the quantized envelope wavefunctions, and the spectral resonance curve of the second-order non-linear susceptibility ($\chi^{(2)}$).
