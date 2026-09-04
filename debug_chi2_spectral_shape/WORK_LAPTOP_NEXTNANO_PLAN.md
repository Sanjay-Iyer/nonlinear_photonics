# Work-laptop nextnano++ Professional plan

Run the exact full 30 nm Case 04 structure (7.1/1.8/2.9/18.2 nm; Al0.55 barrier; 1.0 nm linear grading at I1-I4) with the 8-band k.p solver over a justified k_parallel range. Also run the abrupt reference as a controlled geometry comparison.

Export Ee1(k), Ee2(k), Eh1(k), Eh2(k), spinor composition/eigenvectors versus k, state-overlap information needed for branch tracking through anticrossings, and all available k-dependent interband/intraband optical matrix elements. Retain full complex phases or a documented gauge and use overlap-based state tracking rather than sorting only by energy. Sample densely around anticrossings and every k region identified by the local cumulative-integral plots.

Re-evaluate the same explicit 16-term equation using the tracked k-dependent data, sweep Gamma only within a physically justified range, and compare Re chi2, |Re chi2|, Im chi2, and |chi2| against the paper without retuning normalization. Preserve coherent term and k summation. This run is intended to replace the hybrid's polynomial-dispersion/k=0-matrix approximation, not to mask an algebra or normalization defect.
