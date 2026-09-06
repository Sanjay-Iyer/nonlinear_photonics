# Demo 26 — Exhaustive Home-Laptop Reproduction Audit

## 1. Executive summary

**Decision: NEED FRIEND'S FILES BEFORE RUNNING PRO.**

No defensible full paper reproduction has been established. The real frozen baseline is numerically consistent with the independently implemented printed equation. The strongest new concerns are matrix/state provenance and state-specific energy anchoring, alongside geometry and BZ ambiguity. A latent production complex-conjugation bug is demonstrated, but does not explain the present real-input mismatch. Production files and prior outputs remain preserved.

This is a finite, declared audit of the supplied test families using the searched datasets. It is not a claim that every conceivable home analysis or improved physical reduction is exhausted. Lower RMSE never establishes reproduction by itself.

{
  "total_tests": 176,
  "improved_agreement": 52,
  "did_not_improve": 96,
  "fit_not_applicable": 28,
  "inconclusive": 43,
  "requires_new_pro": 6,
  "status_counts": {
    "PASS": 25,
    "FAIL": 102,
    "INCONCLUSIVE": 43,
    "NOT TESTABLE": 6
  }
}

Counts overlap: improved/not-improved concern fit metrics; INCONCLUSIVE concerns physical interpretation; Pro-required concerns missing eigenstates. PASS means the stated numerical/provenance check passed, not that the paper was reproduced. Variant rows include repeated baselines as controls, not independent discoveries.

## 2. Available data and baseline

See EXISTING_REUSABLE_DATA_INVENTORY.md and EXISTING_DEMO26_TEST_INVENTORY.md. Seven real Professional dispersion datasets include101/201/301 grids and cutoffs0.05/0.075/0.10/0.125pi/a plus45-degree direction. Only k0 wavefunctions/character were exported. Thirteen scalar geometry records include abrupt, but all physical_valid flags are false. Coarse Free abrupt/Poisson fixtures are not converged matching alternatives.

Baseline: Demo23D, frozen case04 scalar M0, statewise-anchored kp8 E(k), 1nm grading, Gamma5meV,16pathways, gs*k*dk/(2pi), magnitude. Wavelength400–1850nm, paper45point linear interpolation, full-window separate normalization. RMSE0.2623911179. Strict target windows: P1 490–580,P2 690–820,P3 990–1170,P4 1450–1610nm; minima use their separately declared windows in numerical_home_audit.py. Missing interior extrema remain null rather than forced endpoints. Baseline P2=752/P4=1503nm; no strict P1/P3/Z1/Z2 extrema. Local errors and target amplitudes are in TEST01.

## 3. What cannot be tested without additional eigenstates

- TEST 134 0.20pi/a candidate: Largest available cutoff0.125pi/a, not0.20. No extrapolation permitted; request missing output or new same-geometry solve.
- TEST 137 Finite-k character tracking: Energy columns exist; nonzero-k character/overlap exports absent. Energy continuity is not wavefunction continuity. Export finite-k characters or overlaps.
- TEST 139 Equivalent abrupt kp8: Abrupt scalar and coarse Free fixtures exist; matching converged abrupt kp8 dispersion absent. Scalar diagnostic is available separately, but exact abrupt E(k) needs new output.
- TEST 141 Matching Poisson alternative: Different coarse doped fixture exists; matching converged paper-geometry Poisson absent. Need exact electrostatic conditions first, then matching solve if files unavailable.
- TEST 142 Finite-k matrix physics: Only k00000 matrices/envelopes found. No fabricated matrices; finite-k physics useful but necessity for paper reproduction unproved.
- TEST 143 Temperature or database changes: No certified same-geometry controlled alternate temperature/database eigenstates. Friend version/database can settle settings; changed eigenstates require output.

## 4. Numbered audit

### TEST 01 — observable magnitude

- **Question:** Does observable magnitude explain the paper discrepancy?
- **Method:** Normalize over original complete 400–1850 nm grid; same physical chi. Non-magnitude observables DIAGNOSTIC ONLY.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** RMSE 0.262391; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=None, P4=1503.0. Full physical reproduction not established.
- **Status:** PASS
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.26239111786932695, "correlation": 0.24755539373540594, "P1_nm": null, "P1_local_RMSE": 0.18355832245681228, "Z1_nm": null, "Z1_local_RMSE": 0.02149182751741102, "P2_nm": 752.0, "P2_local_RMSE": 0.18300269017624166, "P3_nm": null, "P3_local_RMSE": 0.43189844880285366, "Z2_nm": null, "Z2_local_RMSE": 0.3889313933218363, "P4_nm": 1503.0, "P4_local_RMSE": 0.2637088552636287, "all_peaks_nm": "688.0;752.0;837.0;1376.0;1503.0", "all_minima_nm": "720.0;832.0;953.0;1455.0", "topology_json": "[{\"nm\": 688.0, \"local_prominence\": 0.09763940881279826, \"half_prominence_width_nm\": 10.0}, {\"nm\": 752.0, \"local_prominence\": 0.19711267904504853, \"half_prominence_width_nm\": 11.0}, {\"nm\": 837.0, \"local_prominence\": 0.0006496885138127656, \"half_prominence_width_nm\": 9.0}, {\"nm\": 1376.0, \"local_prominence\": 0.2621557638752432, \"half_prominence_width_nm\": 22.0}, {\"nm\": 1503.0, \"local_prominence\": 0.354655473337367, \"half_prominence_width_nm\": 18.0}]"}
```

### TEST 02 — observable Re

- **Question:** Does observable Re explain the paper discrepancy?
- **Method:** Normalize over original complete 400–1850 nm grid; same physical chi. Non-magnitude observables DIAGNOSTIC ONLY.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** RMSE 0.383379; strict feature locations nm: P1=None, Z1=None, P2=None, P3=None, Z2=1374.0, P4=1505.0. Full physical reproduction not established.
- **Status:** FAIL
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.38337877530443165, "correlation": 0.3643059329585638, "P1_nm": null, "P1_local_RMSE": 0.1812118642714305, "Z1_nm": null, "Z1_local_RMSE": 0.024024322877130237, "P2_nm": null, "P2_local_RMSE": 0.5986789881100909, "P3_nm": null, "P3_local_RMSE": 0.6211349283907983, "Z2_nm": 1374.0, "Z2_local_RMSE": 0.5027403667611652, "P4_nm": 1505.0, "P4_local_RMSE": 0.20405132706773954, "all_peaks_nm": "687.0;831.0;953.0;1505.0", "all_minima_nm": "753.0;837.0;1374.0", "topology_json": "[{\"nm\": 687.0, \"local_prominence\": 0.42513774532254006, \"half_prominence_width_nm\": 19.0}, {\"nm\": 831.0, \"local_prominence\": 0.0007812501805682243, \"half_prominence_width_nm\": 4.0}, {\"nm\": 953.0, \"local_prominence\": 0.013939696817684089, \"half_prominence_width_nm\": 175.0}, {\"nm\": 1505.0, \"local_prominence\": 0.9171183458165177, \"half_prominence_width_nm\": 34.0}]"}
```

### TEST 03 — observable abs_Re

- **Question:** Does observable abs_Re explain the paper discrepancy?
- **Method:** Normalize over original complete 400–1850 nm grid; same physical chi. Non-magnitude observables DIAGNOSTIC ONLY.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** lower RMSE; reproduction not established
- **Status:** FAIL
- **Improved paper agreement?:** YES
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.23787347931116054, "correlation": 0.3096300795070898, "P1_nm": null, "P1_local_RMSE": 0.1812118642714305, "Z1_nm": null, "Z1_local_RMSE": 0.024024322877130237, "P2_nm": 753.0, "P2_local_RMSE": 0.2212267507487411, "P3_nm": null, "P3_local_RMSE": 0.419675646517712, "Z2_nm": null, "Z2_local_RMSE": 0.36529336340893653, "P4_nm": 1505.0, "P4_local_RMSE": 0.20405132706773954, "all_peaks_nm": "687.0;753.0;837.0;1374.0;1505.0", "all_minima_nm": "714.0;831.0;953.0;1437.0", "topology_json": "[{\"nm\": 687.0, \"local_prominence\": 0.42513774532254006, \"half_prominence_width_nm\": 19.0}, {\"nm\": 753.0, \"local_prominence\": 0.4374506695641285, \"half_prominence_width_nm\": 16.0}, {\"nm\": 837.0, \"local_prominence\": 0.0007812501805682243, \"half_prominence_width_nm\": 10.0}, {\"nm\": 1374.0, \"local_prominence\": 0.8329744491991558, \"half_prominence_width_nm\": 36.0}, {\"nm\": 1505.0, \"local_prominence\": 0.9171183458165177, \"half_prominence_width_nm\": 34.0}]"}
```

### TEST 04 — observable Im

- **Question:** Does observable Im explain the paper discrepancy?
- **Method:** Normalize over original complete 400–1850 nm grid; same physical chi. Non-magnitude observables DIAGNOSTIC ONLY.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** RMSE 0.491303; strict feature locations nm: P1=None, Z1=None, P2=748.0, P3=None, Z2=1398.0, P4=1458.0. Full physical reproduction not established.
- **Status:** FAIL
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.49130269469301585, "correlation": -0.029178513346183817, "P1_nm": null, "P1_local_RMSE": 0.20003465704466417, "Z1_nm": null, "Z1_local_RMSE": 0.05050015705109586, "P2_nm": 748.0, "P2_local_RMSE": 0.3340246060151968, "P3_nm": null, "P3_local_RMSE": 0.5192001063169227, "Z2_nm": 1398.0, "Z2_local_RMSE": 0.4242134086496791, "P4_nm": 1458.0, "P4_local_RMSE": 0.9844226491762986, "all_peaks_nm": "702.0;748.0;857.0;1458.0;1611.0", "all_minima_nm": "729.0;804.0;1398.0;1496.0;1698.0", "topology_json": "[{\"nm\": 702.0, \"local_prominence\": 0.022008888760316037, \"half_prominence_width_nm\": 22.0}, {\"nm\": 748.0, \"local_prominence\": 0.044186125282918376, \"half_prominence_width_nm\": 8.0}, {\"nm\": 857.0, \"local_prominence\": 0.02417911165628912, \"half_prominence_width_nm\": 485.0}, {\"nm\": 1458.0, \"local_prominence\": 0.05160262780835556, \"half_prominence_width_nm\": 45.0}, {\"nm\": 1611.0, \"local_prominence\": 0.034190116308977704, \"half_prominence_width_nm\": 89.0}]"}
```

### TEST 05 — observable abs_Im

- **Question:** Does observable abs_Im explain the paper discrepancy?
- **Method:** Normalize over original complete 400–1850 nm grid; same physical chi. Non-magnitude observables DIAGNOSTIC ONLY.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** RMSE 0.358331; strict feature locations nm: P1=None, Z1=None, P2=748.0, P3=None, Z2=None, P4=1496.0. Full physical reproduction not established.
- **Status:** FAIL
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.3583312336345216, "correlation": 0.09561271338999845, "P1_nm": null, "P1_local_RMSE": 0.20003465704466417, "Z1_nm": null, "Z1_local_RMSE": 0.05050015705109586, "P2_nm": 748.0, "P2_local_RMSE": 0.3173432014101159, "P3_nm": null, "P3_local_RMSE": 0.5188773927303835, "Z2_nm": null, "Z2_local_RMSE": 0.3214754158064859, "P4_nm": 1496.0, "P4_local_RMSE": 0.5422858398734928, "all_peaks_nm": "702.0;748.0;804.0;857.0;1398.0;1496.0;1611.0;1698.0", "all_minima_nm": "729.0;767.0;836.0;1072.0;1458.0;1534.0;1666.0", "topology_json": "[{\"nm\": 702.0, \"local_prominence\": 0.022008888760316037, \"half_prominence_width_nm\": 22.0}, {\"nm\": 748.0, \"local_prominence\": 0.044186125282918376, \"half_prominence_width_nm\": 8.0}, {\"nm\": 804.0, \"local_prominence\": 0.022088256204301923, \"half_prominence_width_nm\": 54.0}, {\"nm\": 857.0, \"local_prominence\": 0.001263197289885798, \"half_prominence_width_nm\": 100.0}, {\"nm\": 1398.0, \"local_prominence\": 0.05160262780835556, \"half_prominence_width_nm\": 46.0}, {\"nm\": 1496.0, \"local_prominence\": 0.10419404607004312, \"half_prominence_width_nm\": 17.0}, {\"nm\": 1611.0, \"local_prominence\": 0.030970247327192876, \"half_prominence_width_nm\": 81.0}, {\"nm\": 1698.0, \"local_prominence\": 0.0013566908422767497, \"half_prominence_width_nm\": 93.0}]"}
```

### TEST 06 — observable Re_squared

- **Question:** Does observable Re_squared explain the paper discrepancy?
- **Method:** Normalize over original complete 400–1850 nm grid; same physical chi. Non-magnitude observables DIAGNOSTIC ONLY.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** RMSE 0.301046; strict feature locations nm: P1=None, Z1=None, P2=753.0, P3=None, Z2=None, P4=1505.0. Full physical reproduction not established.
- **Status:** FAIL
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.3010455027414372, "correlation": 0.257787117685016, "P1_nm": null, "P1_local_RMSE": 0.1998694314377488, "Z1_nm": null, "Z1_local_RMSE": 0.048356853817202075, "P2_nm": 753.0, "P2_local_RMSE": 0.3533095008380725, "P3_nm": null, "P3_local_RMSE": 0.5084188659126131, "Z2_nm": null, "Z2_local_RMSE": 0.23421078238177442, "P4_nm": 1505.0, "P4_local_RMSE": 0.38555380107882803, "all_peaks_nm": "687.0;753.0;837.0;1374.0;1505.0", "all_minima_nm": "714.0;831.0;953.0;1437.0", "topology_json": "[{\"nm\": 687.0, \"local_prominence\": 0.1855103535635928, \"half_prominence_width_nm\": 10.0}, {\"nm\": 753.0, \"local_prominence\": 0.2825054319101589, \"half_prominence_width_nm\": 10.0}, {\"nm\": 837.0, \"local_prominence\": 0.0001633829279436786, \"half_prominence_width_nm\": 10.0}, {\"nm\": 1374.0, \"local_prominence\": 0.8454744012855805, \"half_prominence_width_nm\": 20.0}, {\"nm\": 1505.0, \"local_prominence\": 0.9931306313998096, \"half_prominence_width_nm\": 19.0}]"}
```

### TEST 07 — observable magnitude_squared

- **Question:** Does observable magnitude_squared explain the paper discrepancy?
- **Method:** Normalize over original complete 400–1850 nm grid; same physical chi. Non-magnitude observables DIAGNOSTIC ONLY.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** RMSE 0.302087; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=None, P4=1503.0. Full physical reproduction not established.
- **Status:** FAIL
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.3020874199256219, "correlation": 0.19699552182896055, "P1_nm": null, "P1_local_RMSE": 0.19996882718384076, "Z1_nm": null, "Z1_local_RMSE": 0.04926159981221132, "P2_nm": 752.0, "P2_local_RMSE": 0.3229662547312783, "P3_nm": null, "P3_local_RMSE": 0.510922783318045, "Z2_nm": null, "Z2_local_RMSE": 0.27437004642849777, "P4_nm": 1503.0, "P4_local_RMSE": 0.3728176374420221, "all_peaks_nm": "688.0;752.0;837.0;1376.0;1503.0", "all_minima_nm": "720.0;832.0;953.0;1455.0", "topology_json": "[{\"nm\": 688.0, \"local_prominence\": 0.07450355631909472, \"half_prominence_width_nm\": 9.0}, {\"nm\": 752.0, \"local_prominence\": 0.17001387972863996, \"half_prominence_width_nm\": 9.0}, {\"nm\": 837.0, \"local_prominence\": 0.000118918403509213, \"half_prominence_width_nm\": 9.0}, {\"nm\": 1376.0, \"local_prominence\": 0.4070872192329119, \"half_prominence_width_nm\": 20.0}, {\"nm\": 1503.0, \"local_prominence\": 0.5835304419065822, \"half_prominence_width_nm\": 16.0}]"}
```

### TEST 08 — Gamma 0 meV magnitude

- **Question:** Does Gamma 0 meV magnitude explain the paper discrepancy?
- **Method:** Single prescribed Gamma; 2.5 meV tests paper 5 meV as FWHM; 5 meV tests HWHM. Zero Gamma is off-pole sampled diagnostic only.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** RMSE 0.333033; strict feature locations nm: P1=None, Z1=None, P2=758.0, P3=None, Z2=1376.0, P4=1520.0. Full physical reproduction not established.
- **Status:** FAIL
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.33303301147216724, "correlation": 0.0528401906728894, "P1_nm": null, "P1_local_RMSE": 0.19987583709831505, "Z1_nm": null, "Z1_local_RMSE": 0.05108332197885111, "P2_nm": 758.0, "P2_local_RMSE": 0.39631191250562076, "P3_nm": null, "P3_local_RMSE": 0.5169471435765058, "Z2_nm": 1376.0, "Z2_local_RMSE": 0.09299362872432923, "P4_nm": 1520.0, "P4_local_RMSE": 0.5624222185375468, "all_peaks_nm": "687.0;689.0;693.0;696.0;700.0;705.0;713.0;721.0;727.0;729.0;731.0;733.0;736.0;738.0;743.0;746.0;749.0;753.0;758.0;762.0;765.0;767.0;771.0;774.0;778.0;780.0;783.0;785.0;788.0;793.0;795.0;802.0;806.0;810.0;812.0;814.0;818.0;821.0;824.0;826.0;839.0;1375.0;1378.0;1381.0;1383.0;1386.0;1389.0;1392.0;1394.0;1397.0;1400.0;1402.0;1405.0;1407.0;1410.0;1412.0;1415.0;1417.0;1419.0;1422.0;1424.0;1426.0;1428.0;1430.0;1432.0;1434.0;1436.0;1438.0;1440.0;1442.0;1444.0;1447.0;1449.0;1452.0;1454.0;1458.0;1461.0;1466.0;1472.0;1477.0;1481.0;1483.0;1486.0;1488.0;1492.0;1495.0;1497.0;1501.0;1503.0;1505.0;1511.0;1514.0;1516.0;1518.0;1520.0;1522.0;1525.0;1527.0;1530.0;1534.0;1536.0;1541.0;1543.0;1545.0;1548.0;1550.0;1552.0;1556.0;1560.0;1563.0;1567.0;1570.0;1573.0;1576.0;1579.0;1581.0;1584.0;1586.0;1589.0;1593.0;1595.0;1597.0;1599.0;1601.0;1604.0;1607.0;1609.0;1612.0;1614.0;1617.0;1620.0;1623.0;1627.0;1635.0;1642.0;1645.0;1647.0;1653.0;1655.0;1657.0;1659.0;1668.0", "all_minima_nm": "688.0;691.0;695.0;699.0;703.0;709.0;717.0;725.0;728.0;730.0;732.0;735.0;737.0;742.0;745.0;748.0;752.0;756.0;761.0;763.0;766.0;768.0;773.0;777.0;779.0;782.0;784.0;787.0;791.0;794.0;801.0;803.0;808.0;811.0;813.0;817.0;819.0;823.0;825.0;829.0;953.0;1376.0;1379.0;1382.0;1385.0;1387.0;1390.0;1393.0;1396.0;1398.0;1401.0;1403.0;1406.0;1409.0;1411.0;1413.0;1416.0;1418.0;1420.0;1423.0;1425.0;1427.0;1429.0;1431.0;1433.0;1435.0;1437.0;1439.0;1441.0;1443.0;1445.0;1448.0;1450.0;1453.0;1456.0;1459.0;1463.0;1471.0;1473.0;1479.0;1482.0;1484.0;1487.0;1490.0;1493.0;1496.0;1499.0;1502.0;1504.0;1509.0;1513.0;1515.0;1517.0;1519.0;1521.0;1523.0;1526.0;1528.0;1531.0;1535.0;1538.0;1542.0;1544.0;1546.0;1549.0;1551.0;1554.0;1558.0;1561.0;1564.0;1569.0;1572.0;1574.0;1578.0;1580.0;1583.0;1585.0;1587.0;1592.0;1594.0;1596.0;1598.0;1600.0;1602.0;1606.0;1608.0;1611.0;1613.0;1616.0;1619.0;1621.0;1626.0;1634.0;1637.0;1643.0;1646.0;1651.0;1654.0;1656.0;1658.0;1660.0", "topology_json": "[{\"nm\": 687.0, \"local_prominence\": 0.011896507311301043, \"half_prominence_width_nm\": 2.0}, {\"nm\": 689.0, \"local_prominence\": 0.04839902479479541, \"half_prominence_width_nm\": 2.0}, {\"nm\": 693.0, \"local_prominence\": 0.01952678996318681, \"half_prominence_width_nm\": 2.0}, {\"nm\": 696.0, \"local_prominence\": 0.05746943565637032, \"half_prominence_width_nm\": 2.0}, {\"nm\": 700.0, \"local_prominence\": 0.035535863769051504, \"half_prominence_width_nm\": 2.0}, {\"nm\": 705.0, \"local_prominence\": 0.05757368179464143, \"half_prominence_width_nm\": 2.0}, {\"nm\": 713.0, \"local_prominence\": 0.38712231939388014, \"half_prominence_width_nm\": 2.0}, {\"nm\": 721.0, \"local_prominence\": 0.48378653072401545, \"half_prominence_width_nm\": 2.0}, {\"nm\": 727.0, \"local_prominence\": 0.016300086322877095, \"half_prominence_width_nm\": 3.0}, {\"nm\": 729.0, \"local_prominence\": 0.0088679436819005, \"half_prominence_width_nm\": 2.0}, {\"nm\": 731.0, \"local_prominence\": 0.0032782125437961513, \"half_prominence_width_nm\": 2.0}, {\"nm\": 733.0, \"local_prominence\": 0.05523162437012466, \"half_prominence_width_nm\": 2.0}, {\"nm\": 736.0, \"local_prominence\": 0.001370266859917198, \"half_prominence_width_nm\": 2.0}, {\"nm\": 738.0, \"local_prominence\": 0.014665071124836069, \"half_prominence_width_nm\": 3.0}, {\"nm\": 743.0, \"local_prominence\": 0.01608676568531032, \"half_prominence_width_nm\": 3.0}, {\"nm\": 746.0, \"local_prominence\": 0.01781785378897932, \"half_prominence_width_nm\": 2.0}, {\"nm\": 749.0, \"local_prominence\": 0.02677147892380637, \"half_prominence_width_nm\": 2.0}, {\"nm\": 753.0, \"local_prominence\": 1.6804746014280336e-06, \"half_prominence_width_nm\": 2.0}, {\"nm\": 758.0, \"local_prominence\": 0.09910548918615383, \"half_prominence_width_nm\": 2.0}, {\"nm\": 762.0, \"local_prominence\": 0.0016972358417841373, \"half_prominence_width_nm\": 2.0}, {\"nm\": 765.0, \"local_prominence\": 0.0007723594973941175, \"half_prominence_width_nm\": 3.0}, {\"nm\": 767.0, \"local_prominence\": 0.011360818305910837, \"half_prominence_width_nm\": 2.0}, {\"nm\": 771.0, \"local_prominence\": 0.0018842558316242183, \"half_prominence_width_nm\": 3.0}, {\"nm\": 774.0, \"local_prominence\": 0.012120113594660404, \"half_prominence_width_nm\": 3.0}, {\"nm\": 778.0, \"local_prominence\": 0.0013796160457579228, \"half_prominence_width_nm\": 2.0}, {\"nm\": 780.0, \"local_prominence\": 0.001796186966119889, \"half_prominence_width_nm\": 2.0}, {\"nm\": 783.0, \"local_prominence\": 0.0009731369716337113, \"half_prominence_width_nm\": 2.0}, {\"nm\": 785.0, \"local_prominence\": 0.0011473815448145895, \"half_prominence_width_nm\": 2.0}, {\"nm\": 788.0, \"local_prominence\": 0.001519350338112554, \"half_prominence_width_nm\": 2.0}, {\"nm\": 793.0, \"local_prominence\": 0.004664572145385666, \"half_prominence_width_nm\": 2.0}, {\"nm\": 795.0, \"local_prominence\": 0.0005231257123122697, \"half_prominence_width_nm\": 2.0}, {\"nm\": 802.0, \"local_prominence\": 0.0044449664220985695, \"half_prominence_width_nm\": 2.0}, {\"nm\": 806.0, \"local_prominence\": 0.0018927272455303173, \"half_prominence_width_nm\": 3.0}, {\"nm\": 810.0, \"local_prominence\": 0.0017723573223719395, \"half_prominence_width_nm\": 2.0}, {\"nm\": 812.0, \"local_prominence\": 0.0008241814887373334, \"half_prominence_width_nm\": 2.0}, {\"nm\": 814.0, \"local_prominence\": 0.0010138480848408261, \"half_prominence_width_nm\": 3.0}, {\"nm\": 818.0, \"local_prominence\": 0.010780214128647736, \"half_prominence_width_nm\": 2.0}, {\"nm\": 821.0, \"local_prominence\": 0.0006940204427234764, \"half_prominence_width_nm\": 2.0}, {\"nm\": 824.0, \"local_prominence\": 0.0002002522974506745, \"half_prominence_width_nm\": 2.0}, {\"nm\": 826.0, \"local_prominence\": 0.0002576016338063413, \"half_prominence_width_nm\": 2.0}, {\"nm\": 839.0, \"local_prominence\": 0.00029526750581383536, \"half_prominence_width_nm\": 44.0}, {\"nm\": 1375.0, \"local_prominence\": 0.2945796908662906, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1378.0, \"local_prominence\": 0.09461442793803967, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1381.0, \"local_prominence\": 0.03754248344308407, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1383.0, \"local_prominence\": 0.02492978332843147, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1386.0, \"local_prominence\": 0.037628172505928995, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1389.0, \"local_prominence\": 0.10063639189185739, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1392.0, \"local_prominence\": 0.11613401527734485, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1394.0, \"local_prominence\": 0.021364226068122348, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1397.0, \"local_prominence\": 0.0654121113200003, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1400.0, \"local_prominence\": 0.07049333051156888, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1402.0, \"local_prominence\": 0.0296583571348049, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1405.0, \"local_prominence\": 0.19471260775712748, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1407.0, \"local_prominence\": 0.02129968987994551, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1410.0, \"local_prominence\": 0.10440460447982923, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1412.0, \"local_prominence\": 0.03544351274868426, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1415.0, \"local_prominence\": 0.026529693572976944, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1417.0, \"local_prominence\": 0.3672888527544741, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1419.0, \"local_prominence\": 0.026681720893788, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1422.0, \"local_prominence\": 0.015731991841123484, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1424.0, \"local_prominence\": 0.0580516670762939, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1426.0, \"local_prominence\": 0.8021756637533538, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1428.0, \"local_prominence\": 0.06779531915263508, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1430.0, \"local_prominence\": 0.034379695648571997, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1432.0, \"local_prominence\": 0.023619230912042394, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1434.0, \"local_prominence\": 0.0174726047653212, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1436.0, \"local_prominence\": 0.019125822476625993, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1438.0, \"local_prominence\": 0.027305131200286756, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1440.0, \"local_prominence\": 0.0548686243419272, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1442.0, \"local_prominence\": 0.9969949968047395, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1444.0, \"local_prominence\": 0.04351414462298761, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1447.0, \"local_prominence\": 0.0161468889843441, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1449.0, \"local_prominence\": 0.8834407558217723, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1452.0, \"local_prominence\": 0.027055300199812192, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1454.0, \"local_prominence\": 0.032452976807618814, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1458.0, \"local_prominence\": 0.028962596520241753, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1461.0, \"local_prominence\": 0.09840289002045553, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1466.0, \"local_prominence\": 0.11642805189885522, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1472.0, \"local_prominence\": 0.0009287691574277764, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1477.0, \"local_prominence\": 0.19278599040909672, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1481.0, \"local_prominence\": 0.03734789747866873, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1483.0, \"local_prominence\": 0.17753974306545506, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1486.0, \"local_prominence\": 0.037083684564444046, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1488.0, \"local_prominence\": 0.017678796984425645, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1492.0, \"local_prominence\": 0.03806289848002228, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1495.0, \"local_prominence\": 0.012682728864732122, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1497.0, \"local_prominence\": 0.13901199908077444, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1501.0, \"local_prominence\": 0.030638034482713357, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1503.0, \"local_prominence\": 0.4014036700531469, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1505.0, \"local_prominence\": 0.05142123107332239, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1511.0, \"local_prominence\": 0.0188696140684109, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1514.0, \"local_prominence\": 5.279858044248201e-05, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1516.0, \"local_prominence\": 0.10624466604307653, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1518.0, \"local_prominence\": 0.0024598850015965217, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1520.0, \"local_prominence\": 0.0002474803712476468, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1522.0, \"local_prominence\": 4.8986759589295104e-05, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1525.0, \"local_prominence\": 0.003963061835562311, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1527.0, \"local_prominence\": 0.0006132476122955727, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1530.0, \"local_prominence\": 0.0014564281974172345, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1534.0, \"local_prominence\": 0.003070395661274523, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1536.0, \"local_prominence\": 0.010811181376455248, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1541.0, \"local_prominence\": 0.0015071326344402221, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1543.0, \"local_prominence\": 0.008077181179753402, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1545.0, \"local_prominence\": 0.0007767368770208657, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1548.0, \"local_prominence\": 0.00883975244014414, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1550.0, \"local_prominence\": 0.017876701725780896, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1552.0, \"local_prominence\": 0.00139614314208035, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1556.0, \"local_prominence\": 0.001928061252028772, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1560.0, \"local_prominence\": 0.002464270295330649, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1563.0, \"local_prominence\": 0.002054537921216611, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1567.0, \"local_prominence\": 0.0036249800990462025, \"half_prominence_width_nm\": 4.0}, {\"nm\": 1570.0, \"local_prominence\": 0.001248371125047598, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1573.0, \"local_prominence\": 0.0012998719336545696, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1576.0, \"local_prominence\": 0.0010947818619768982, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1579.0, \"local_prominence\": 0.005369707750271343, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1581.0, \"local_prominence\": 0.0013911702019950567, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1584.0, \"local_prominence\": 0.002140056022886072, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1586.0, \"local_prominence\": 0.01075253521881599, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1589.0, \"local_prominence\": 0.005966957857514888, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1593.0, \"local_prominence\": 0.0005955913644083181, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1595.0, \"local_prominence\": 0.0007264754829354901, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1597.0, \"local_prominence\": 0.0010743900249437156, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1599.0, \"local_prominence\": 0.001358093964105407, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1601.0, \"local_prominence\": 0.002609970641776531, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1604.0, \"local_prominence\": 0.010050294844005693, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1607.0, \"local_prominence\": 0.0011176864435009978, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1609.0, \"local_prominence\": 0.001461790435725442, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1612.0, \"local_prominence\": 0.002507649570826661, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1614.0, \"local_prominence\": 0.000803166701979335, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1617.0, \"local_prominence\": 0.0010149219130878443, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1620.0, \"local_prominence\": 0.0029616130197979255, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1623.0, \"local_prominence\": 0.0016615311713106978, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1627.0, \"local_prominence\": 0.0025876545064086012, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1635.0, \"local_prominence\": 0.02449254398244263, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1642.0, \"local_prominence\": 0.0015888161062389112, \"half_prominence_width_nm\": 4.0}, {\"nm\": 1645.0, \"local_prominence\": 0.0010137339061070867, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1647.0, \"local_prominence\": 0.0015013357103451567, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1653.0, \"local_prominence\": 0.0006768907313730674, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1655.0, \"local_prominence\": 0.006605135926807728, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1657.0, \"local_prominence\": 0.0010761942402230848, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1659.0, \"local_prominence\": 0.000639214464203482, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1668.0, \"local_prominence\": 0.0003879351498941117, \"half_prominence_width_nm\": 38.0}]"}
```

### TEST 09 — Gamma 0 meV Re

- **Question:** Does Gamma 0 meV Re explain the paper discrepancy?
- **Method:** Single prescribed Gamma; 2.5 meV tests paper 5 meV as FWHM; 5 meV tests HWHM. Zero Gamma is off-pole sampled diagnostic only.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** RMSE 0.340699; strict feature locations nm: P1=None, Z1=None, P2=761.0, P3=None, Z2=1374.0, P4=1520.0. Full physical reproduction not established.
- **Status:** FAIL
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.34069898434044216, "correlation": 0.05728757448787339, "P1_nm": null, "P1_local_RMSE": 0.19987583709831505, "Z1_nm": null, "Z1_local_RMSE": 0.05108332197885111, "P2_nm": 761.0, "P2_local_RMSE": 0.4083976412735551, "P3_nm": null, "P3_local_RMSE": 0.5213062620969812, "Z2_nm": 1374.0, "Z2_local_RMSE": 0.10910463916338016, "P4_nm": 1520.0, "P4_local_RMSE": 0.5706669242355699, "all_peaks_nm": "687.0;690.0;693.0;697.0;701.0;706.0;713.0;721.0;726.0;729.0;731.0;734.0;738.0;740.0;743.0;745.0;749.0;752.0;756.0;758.0;761.0;763.0;766.0;768.0;774.0;777.0;779.0;782.0;784.0;787.0;791.0;794.0;801.0;803.0;808.0;811.0;813.0;818.0;823.0;825.0;829.0;953.0;1375.0;1378.0;1381.0;1384.0;1387.0;1390.0;1392.0;1395.0;1398.0;1400.0;1403.0;1405.0;1408.0;1410.0;1413.0;1415.0;1418.0;1420.0;1422.0;1424.0;1427.0;1429.0;1431.0;1433.0;1435.0;1437.0;1439.0;1441.0;1444.0;1446.0;1449.0;1451.0;1454.0;1457.0;1461.0;1466.0;1472.0;1477.0;1481.0;1483.0;1485.0;1488.0;1492.0;1495.0;1497.0;1501.0;1503.0;1505.0;1511.0;1514.0;1518.0;1520.0;1522.0;1524.0;1527.0;1530.0;1533.0;1536.0;1541.0;1543.0;1545.0;1547.0;1550.0;1552.0;1556.0;1560.0;1563.0;1567.0;1570.0;1573.0;1576.0;1579.0;1581.0;1584.0;1586.0;1589.0;1593.0;1595.0;1597.0;1599.0;1601.0;1604.0;1607.0;1609.0;1612.0;1614.0;1617.0;1620.0;1623.0;1627.0;1642.0;1645.0;1647.0;1653.0;1655.0;1657.0;1659.0;1668.0", "all_minima_nm": "689.0;692.0;696.0;700.0;705.0;712.0;717.0;722.0;727.0;730.0;733.0;736.0;739.0;741.0;744.0;746.0;750.0;753.0;757.0;759.0;762.0;765.0;767.0;771.0;775.0;778.0;780.0;783.0;785.0;788.0;793.0;795.0;802.0;806.0;810.0;812.0;814.0;821.0;824.0;826.0;839.0;1374.0;1377.0;1380.0;1383.0;1386.0;1389.0;1391.0;1394.0;1397.0;1399.0;1402.0;1404.0;1407.0;1409.0;1412.0;1414.0;1417.0;1419.0;1421.0;1423.0;1426.0;1428.0;1430.0;1432.0;1434.0;1436.0;1438.0;1440.0;1442.0;1445.0;1447.0;1450.0;1452.0;1455.0;1458.0;1462.0;1467.0;1476.0;1480.0;1482.0;1484.0;1486.0;1491.0;1493.0;1496.0;1498.0;1502.0;1504.0;1509.0;1513.0;1516.0;1519.0;1521.0;1523.0;1525.0;1528.0;1531.0;1534.0;1538.0;1542.0;1544.0;1546.0;1548.0;1551.0;1554.0;1558.0;1561.0;1564.0;1569.0;1572.0;1574.0;1578.0;1580.0;1583.0;1585.0;1587.0;1592.0;1594.0;1596.0;1598.0;1600.0;1602.0;1606.0;1608.0;1611.0;1613.0;1616.0;1619.0;1621.0;1626.0;1635.0;1643.0;1646.0;1651.0;1654.0;1656.0;1658.0;1660.0", "topology_json": "[{\"nm\": 687.0, \"local_prominence\": 0.01889971013875309, \"half_prominence_width_nm\": 3.0}, {\"nm\": 690.0, \"local_prominence\": 0.02873413821822602, \"half_prominence_width_nm\": 3.0}, {\"nm\": 693.0, \"local_prominence\": 0.03705313262791765, \"half_prominence_width_nm\": 3.0}, {\"nm\": 697.0, \"local_prominence\": 0.053904728934788315, \"half_prominence_width_nm\": 4.0}, {\"nm\": 701.0, \"local_prominence\": 0.05635588931083735, \"half_prominence_width_nm\": 5.0}, {\"nm\": 706.0, \"local_prominence\": 0.05589009152918159, \"half_prominence_width_nm\": 5.0}, {\"nm\": 713.0, \"local_prominence\": 0.38712231939388014, \"half_prominence_width_nm\": 2.0}, {\"nm\": 721.0, \"local_prominence\": 0.48378653072401545, \"half_prominence_width_nm\": 2.0}, {\"nm\": 726.0, \"local_prominence\": 0.03437565513739534, \"half_prominence_width_nm\": 3.0}, {\"nm\": 729.0, \"local_prominence\": 0.02317201186173356, \"half_prominence_width_nm\": 2.0}, {\"nm\": 731.0, \"local_prominence\": 0.01758228072362921, \"half_prominence_width_nm\": 2.0}, {\"nm\": 734.0, \"local_prominence\": 0.010331727234204537, \"half_prominence_width_nm\": 2.0}, {\"nm\": 738.0, \"local_prominence\": 0.018245149000553892, \"half_prominence_width_nm\": 2.0}, {\"nm\": 740.0, \"local_prominence\": 0.009713370742525476, \"half_prominence_width_nm\": 2.0}, {\"nm\": 743.0, \"local_prominence\": 0.020304190730448094, \"half_prominence_width_nm\": 2.0}, {\"nm\": 745.0, \"local_prominence\": 0.012866918315559637, \"half_prominence_width_nm\": 2.0}, {\"nm\": 749.0, \"local_prominence\": 0.061577512866735074, \"half_prominence_width_nm\": 2.0}, {\"nm\": 752.0, \"local_prominence\": 0.03076527854397908, \"half_prominence_width_nm\": 2.0}, {\"nm\": 756.0, \"local_prominence\": 0.004086029052432038, \"half_prominence_width_nm\": 2.0}, {\"nm\": 758.0, \"local_prominence\": 0.11528925085196273, \"half_prominence_width_nm\": 2.0}, {\"nm\": 761.0, \"local_prominence\": 0.0007919947159387656, \"half_prominence_width_nm\": 3.0}, {\"nm\": 763.0, \"local_prominence\": 0.0007723594973941175, \"half_prominence_width_nm\": 2.0}, {\"nm\": 766.0, \"local_prominence\": 0.002861816816616158, \"half_prominence_width_nm\": 2.0}, {\"nm\": 768.0, \"local_prominence\": 0.0029268283398537417, \"half_prominence_width_nm\": 3.0}, {\"nm\": 774.0, \"local_prominence\": 0.021717955044393843, \"half_prominence_width_nm\": 2.0}, {\"nm\": 777.0, \"local_prominence\": 0.0018257437606055043, \"half_prominence_width_nm\": 2.0}, {\"nm\": 779.0, \"local_prominence\": 0.0013796160457579228, \"half_prominence_width_nm\": 2.0}, {\"nm\": 782.0, \"local_prominence\": 0.005584942086050967, \"half_prominence_width_nm\": 2.0}, {\"nm\": 784.0, \"local_prominence\": 0.0009731369716337113, \"half_prominence_width_nm\": 2.0}, {\"nm\": 787.0, \"local_prominence\": 0.001519350338112554, \"half_prominence_width_nm\": 2.0}, {\"nm\": 791.0, \"local_prominence\": 0.0021213801006747706, \"half_prominence_width_nm\": 3.0}, {\"nm\": 794.0, \"local_prominence\": 0.0005231257123122697, \"half_prominence_width_nm\": 2.0}, {\"nm\": 801.0, \"local_prominence\": 0.0020957691513762786, \"half_prominence_width_nm\": 6.0}, {\"nm\": 803.0, \"local_prominence\": 0.0019006582212512, \"half_prominence_width_nm\": 4.0}, {\"nm\": 808.0, \"local_prominence\": 0.0017723573223719395, \"half_prominence_width_nm\": 3.0}, {\"nm\": 811.0, \"local_prominence\": 0.0008330480462149798, \"half_prominence_width_nm\": 2.0}, {\"nm\": 813.0, \"local_prominence\": 0.0008241814887373334, \"half_prominence_width_nm\": 2.0}, {\"nm\": 818.0, \"local_prominence\": 0.015415389742462204, \"half_prominence_width_nm\": 2.0}, {\"nm\": 823.0, \"local_prominence\": 0.0002002522974506745, \"half_prominence_width_nm\": 2.0}, {\"nm\": 825.0, \"local_prominence\": 0.0002576016338063413, \"half_prominence_width_nm\": 2.0}, {\"nm\": 829.0, \"local_prominence\": 0.0005608491804075498, \"half_prominence_width_nm\": 5.0}, {\"nm\": 953.0, \"local_prominence\": 0.00029526750581383536, \"half_prominence_width_nm\": 173.0}, {\"nm\": 1375.0, \"local_prominence\": 0.34519580358866914, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1378.0, \"local_prominence\": 0.14425710495002572, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1381.0, \"local_prominence\": 0.08328447527394542, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1384.0, \"local_prominence\": 0.06166778907657321, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1387.0, \"local_prominence\": 0.06103798542863236, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1390.0, \"local_prominence\": 0.023131065262839517, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1392.0, \"local_prominence\": 0.1415987146836795, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1395.0, \"local_prominence\": 0.05537395226836331, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1398.0, \"local_prominence\": 0.025065911111771838, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1400.0, \"local_prominence\": 0.09555924162334073, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1403.0, \"local_prominence\": 0.026668779637534466, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1405.0, \"local_prominence\": 0.22138138739466195, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1408.0, \"local_prominence\": 0.02859158399965646, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1410.0, \"local_prominence\": 0.13049214954842714, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1413.0, \"local_prominence\": 0.025888268803574376, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1415.0, \"local_prominence\": 0.052417962376551316, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1418.0, \"local_prominence\": 0.03863690432576722, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1420.0, \"local_prominence\": 0.02819046142216817, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1422.0, \"local_prominence\": 0.03549912469845827, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1424.0, \"local_prominence\": 0.07683000382924314, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1427.0, \"local_prominence\": 0.07402936995375425, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1429.0, \"local_prominence\": 0.04669080586151708, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1431.0, \"local_prominence\": 0.04057768184173327, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1433.0, \"local_prominence\": 0.03673011387076779, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1435.0, \"local_prominence\": 0.0372012552474891, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1437.0, \"local_prominence\": 0.03782487723938002, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1439.0, \"local_prominence\": 0.04260365119623728, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1441.0, \"local_prominence\": 0.06433741801146814, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1444.0, \"local_prominence\": 0.060577631444636515, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1446.0, \"local_prominence\": 0.028217719367524926, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1449.0, \"local_prominence\": 0.8967039543607978, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1451.0, \"local_prominence\": 0.026767873073152308, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1454.0, \"local_prominence\": 0.05590241991655386, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1457.0, \"local_prominence\": 0.051384034726664043, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1461.0, \"local_prominence\": 0.12396252339057964, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1466.0, \"local_prominence\": 0.1419876852689793, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1472.0, \"local_prominence\": 0.03689792028764764, \"half_prominence_width_nm\": 8.0}, {\"nm\": 1477.0, \"local_prominence\": 0.21768775484754885, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1481.0, \"local_prominence\": 0.03965797802995344, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1483.0, \"local_prominence\": 0.17753974306545506, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1485.0, \"local_prominence\": 0.036797541829507105, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1488.0, \"local_prominence\": 0.03986419827871724, \"half_prominence_width_nm\": 5.0}, {\"nm\": 1492.0, \"local_prominence\": 0.04884908378091781, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1495.0, \"local_prominence\": 0.012682728864732122, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1497.0, \"local_prominence\": 0.16487621812153463, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1501.0, \"local_prominence\": 0.031800165314559196, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1503.0, \"local_prominence\": 0.4015065166620864, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1505.0, \"local_prominence\": 0.06415499447179952, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1511.0, \"local_prominence\": 0.0188696140684109, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1514.0, \"local_prominence\": 5.279858044248201e-05, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1518.0, \"local_prominence\": 0.003622553181380935, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1520.0, \"local_prominence\": 0.0002474803712476468, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1522.0, \"local_prominence\": 4.8986759589295104e-05, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1524.0, \"local_prominence\": 0.001749115357618368, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1527.0, \"local_prominence\": 0.0006132476122955727, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1530.0, \"local_prominence\": 0.0014564281974172345, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1533.0, \"local_prominence\": 0.015080738686150574, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1536.0, \"local_prominence\": 0.014638919860952133, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1541.0, \"local_prominence\": 0.0015071326344402221, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1543.0, \"local_prominence\": 0.008077181179753402, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1545.0, \"local_prominence\": 0.0007767368770208657, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1547.0, \"local_prominence\": 0.0035139758105398357, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1550.0, \"local_prominence\": 0.017876701725780896, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1552.0, \"local_prominence\": 0.00139614314208035, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1556.0, \"local_prominence\": 0.001928061252028772, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1560.0, \"local_prominence\": 0.002464270295330649, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1563.0, \"local_prominence\": 0.002054537921216611, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1567.0, \"local_prominence\": 0.0036249800990462025, \"half_prominence_width_nm\": 4.0}, {\"nm\": 1570.0, \"local_prominence\": 0.001248371125047598, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1573.0, \"local_prominence\": 0.0012998719336545696, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1576.0, \"local_prominence\": 0.0010947818619768982, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1579.0, \"local_prominence\": 0.005369707750271343, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1581.0, \"local_prominence\": 0.0013911702019950567, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1584.0, \"local_prominence\": 0.002140056022886072, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1586.0, \"local_prominence\": 0.01075253521881599, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1589.0, \"local_prominence\": 0.005966957857514888, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1593.0, \"local_prominence\": 0.0005955913644083181, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1595.0, \"local_prominence\": 0.0007264754829354901, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1597.0, \"local_prominence\": 0.0010743900249437156, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1599.0, \"local_prominence\": 0.001358093964105407, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1601.0, \"local_prominence\": 0.002609970641776531, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1604.0, \"local_prominence\": 0.010050294844005693, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1607.0, \"local_prominence\": 0.0011176864435009978, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1609.0, \"local_prominence\": 0.001461790435725442, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1612.0, \"local_prominence\": 0.002507649570826661, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1614.0, \"local_prominence\": 0.000803166701979335, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1617.0, \"local_prominence\": 0.0010149219130878443, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1620.0, \"local_prominence\": 0.0029616130197979255, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1623.0, \"local_prominence\": 0.0016615311713106978, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1627.0, \"local_prominence\": 0.0025876545064086012, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1642.0, \"local_prominence\": 0.0015888161062389112, \"half_prominence_width_nm\": 4.0}, {\"nm\": 1645.0, \"local_prominence\": 0.0010137339061070867, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1647.0, \"local_prominence\": 0.0015013357103451567, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1653.0, \"local_prominence\": 0.0006768907313730674, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1655.0, \"local_prominence\": 0.006605135926807728, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1657.0, \"local_prominence\": 0.0010761942402230848, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1659.0, \"local_prominence\": 0.000639214464203482, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1668.0, \"local_prominence\": 0.0003879351498941117, \"half_prominence_width_nm\": 38.0}]"}
```

### TEST 10 — Gamma 0 meV abs_Re

- **Question:** Does Gamma 0 meV abs_Re explain the paper discrepancy?
- **Method:** Single prescribed Gamma; 2.5 meV tests paper 5 meV as FWHM; 5 meV tests HWHM. Zero Gamma is off-pole sampled diagnostic only.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** RMSE 0.333033; strict feature locations nm: P1=None, Z1=None, P2=758.0, P3=None, Z2=1376.0, P4=1520.0. Full physical reproduction not established.
- **Status:** FAIL
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.33303301147216724, "correlation": 0.0528401906728894, "P1_nm": null, "P1_local_RMSE": 0.19987583709831505, "Z1_nm": null, "Z1_local_RMSE": 0.05108332197885111, "P2_nm": 758.0, "P2_local_RMSE": 0.39631191250562076, "P3_nm": null, "P3_local_RMSE": 0.5169471435765058, "Z2_nm": 1376.0, "Z2_local_RMSE": 0.09299362872432923, "P4_nm": 1520.0, "P4_local_RMSE": 0.5624222185375468, "all_peaks_nm": "687.0;689.0;693.0;696.0;700.0;705.0;713.0;721.0;727.0;729.0;731.0;733.0;736.0;738.0;743.0;746.0;749.0;753.0;758.0;762.0;765.0;767.0;771.0;774.0;778.0;780.0;783.0;785.0;788.0;793.0;795.0;802.0;806.0;810.0;812.0;814.0;818.0;821.0;824.0;826.0;839.0;1375.0;1378.0;1381.0;1383.0;1386.0;1389.0;1392.0;1394.0;1397.0;1400.0;1402.0;1405.0;1407.0;1410.0;1412.0;1415.0;1417.0;1419.0;1422.0;1424.0;1426.0;1428.0;1430.0;1432.0;1434.0;1436.0;1438.0;1440.0;1442.0;1444.0;1447.0;1449.0;1452.0;1454.0;1458.0;1461.0;1466.0;1472.0;1477.0;1481.0;1483.0;1486.0;1488.0;1492.0;1495.0;1497.0;1501.0;1503.0;1505.0;1511.0;1514.0;1516.0;1518.0;1520.0;1522.0;1525.0;1527.0;1530.0;1534.0;1536.0;1541.0;1543.0;1545.0;1548.0;1550.0;1552.0;1556.0;1560.0;1563.0;1567.0;1570.0;1573.0;1576.0;1579.0;1581.0;1584.0;1586.0;1589.0;1593.0;1595.0;1597.0;1599.0;1601.0;1604.0;1607.0;1609.0;1612.0;1614.0;1617.0;1620.0;1623.0;1627.0;1635.0;1642.0;1645.0;1647.0;1653.0;1655.0;1657.0;1659.0;1668.0", "all_minima_nm": "688.0;691.0;695.0;699.0;703.0;709.0;717.0;725.0;728.0;730.0;732.0;735.0;737.0;742.0;745.0;748.0;752.0;756.0;761.0;763.0;766.0;768.0;773.0;777.0;779.0;782.0;784.0;787.0;791.0;794.0;801.0;803.0;808.0;811.0;813.0;817.0;819.0;823.0;825.0;829.0;953.0;1376.0;1379.0;1382.0;1385.0;1387.0;1390.0;1393.0;1396.0;1398.0;1401.0;1403.0;1406.0;1409.0;1411.0;1413.0;1416.0;1418.0;1420.0;1423.0;1425.0;1427.0;1429.0;1431.0;1433.0;1435.0;1437.0;1439.0;1441.0;1443.0;1445.0;1448.0;1450.0;1453.0;1456.0;1459.0;1463.0;1471.0;1473.0;1479.0;1482.0;1484.0;1487.0;1490.0;1493.0;1496.0;1499.0;1502.0;1504.0;1509.0;1513.0;1515.0;1517.0;1519.0;1521.0;1523.0;1526.0;1528.0;1531.0;1535.0;1538.0;1542.0;1544.0;1546.0;1549.0;1551.0;1554.0;1558.0;1561.0;1564.0;1569.0;1572.0;1574.0;1578.0;1580.0;1583.0;1585.0;1587.0;1592.0;1594.0;1596.0;1598.0;1600.0;1602.0;1606.0;1608.0;1611.0;1613.0;1616.0;1619.0;1621.0;1626.0;1634.0;1637.0;1643.0;1646.0;1651.0;1654.0;1656.0;1658.0;1660.0", "topology_json": "[{\"nm\": 687.0, \"local_prominence\": 0.011896507311301043, \"half_prominence_width_nm\": 2.0}, {\"nm\": 689.0, \"local_prominence\": 0.04839902479479541, \"half_prominence_width_nm\": 2.0}, {\"nm\": 693.0, \"local_prominence\": 0.01952678996318681, \"half_prominence_width_nm\": 2.0}, {\"nm\": 696.0, \"local_prominence\": 0.05746943565637032, \"half_prominence_width_nm\": 2.0}, {\"nm\": 700.0, \"local_prominence\": 0.035535863769051504, \"half_prominence_width_nm\": 2.0}, {\"nm\": 705.0, \"local_prominence\": 0.05757368179464143, \"half_prominence_width_nm\": 2.0}, {\"nm\": 713.0, \"local_prominence\": 0.38712231939388014, \"half_prominence_width_nm\": 2.0}, {\"nm\": 721.0, \"local_prominence\": 0.48378653072401545, \"half_prominence_width_nm\": 2.0}, {\"nm\": 727.0, \"local_prominence\": 0.016300086322877095, \"half_prominence_width_nm\": 3.0}, {\"nm\": 729.0, \"local_prominence\": 0.0088679436819005, \"half_prominence_width_nm\": 2.0}, {\"nm\": 731.0, \"local_prominence\": 0.0032782125437961513, \"half_prominence_width_nm\": 2.0}, {\"nm\": 733.0, \"local_prominence\": 0.05523162437012466, \"half_prominence_width_nm\": 2.0}, {\"nm\": 736.0, \"local_prominence\": 0.001370266859917198, \"half_prominence_width_nm\": 2.0}, {\"nm\": 738.0, \"local_prominence\": 0.014665071124836069, \"half_prominence_width_nm\": 3.0}, {\"nm\": 743.0, \"local_prominence\": 0.01608676568531032, \"half_prominence_width_nm\": 3.0}, {\"nm\": 746.0, \"local_prominence\": 0.01781785378897932, \"half_prominence_width_nm\": 2.0}, {\"nm\": 749.0, \"local_prominence\": 0.02677147892380637, \"half_prominence_width_nm\": 2.0}, {\"nm\": 753.0, \"local_prominence\": 1.6804746014280336e-06, \"half_prominence_width_nm\": 2.0}, {\"nm\": 758.0, \"local_prominence\": 0.09910548918615383, \"half_prominence_width_nm\": 2.0}, {\"nm\": 762.0, \"local_prominence\": 0.0016972358417841373, \"half_prominence_width_nm\": 2.0}, {\"nm\": 765.0, \"local_prominence\": 0.0007723594973941175, \"half_prominence_width_nm\": 3.0}, {\"nm\": 767.0, \"local_prominence\": 0.011360818305910837, \"half_prominence_width_nm\": 2.0}, {\"nm\": 771.0, \"local_prominence\": 0.0018842558316242183, \"half_prominence_width_nm\": 3.0}, {\"nm\": 774.0, \"local_prominence\": 0.012120113594660404, \"half_prominence_width_nm\": 3.0}, {\"nm\": 778.0, \"local_prominence\": 0.0013796160457579228, \"half_prominence_width_nm\": 2.0}, {\"nm\": 780.0, \"local_prominence\": 0.001796186966119889, \"half_prominence_width_nm\": 2.0}, {\"nm\": 783.0, \"local_prominence\": 0.0009731369716337113, \"half_prominence_width_nm\": 2.0}, {\"nm\": 785.0, \"local_prominence\": 0.0011473815448145895, \"half_prominence_width_nm\": 2.0}, {\"nm\": 788.0, \"local_prominence\": 0.001519350338112554, \"half_prominence_width_nm\": 2.0}, {\"nm\": 793.0, \"local_prominence\": 0.004664572145385666, \"half_prominence_width_nm\": 2.0}, {\"nm\": 795.0, \"local_prominence\": 0.0005231257123122697, \"half_prominence_width_nm\": 2.0}, {\"nm\": 802.0, \"local_prominence\": 0.0044449664220985695, \"half_prominence_width_nm\": 2.0}, {\"nm\": 806.0, \"local_prominence\": 0.0018927272455303173, \"half_prominence_width_nm\": 3.0}, {\"nm\": 810.0, \"local_prominence\": 0.0017723573223719395, \"half_prominence_width_nm\": 2.0}, {\"nm\": 812.0, \"local_prominence\": 0.0008241814887373334, \"half_prominence_width_nm\": 2.0}, {\"nm\": 814.0, \"local_prominence\": 0.0010138480848408261, \"half_prominence_width_nm\": 3.0}, {\"nm\": 818.0, \"local_prominence\": 0.010780214128647736, \"half_prominence_width_nm\": 2.0}, {\"nm\": 821.0, \"local_prominence\": 0.0006940204427234764, \"half_prominence_width_nm\": 2.0}, {\"nm\": 824.0, \"local_prominence\": 0.0002002522974506745, \"half_prominence_width_nm\": 2.0}, {\"nm\": 826.0, \"local_prominence\": 0.0002576016338063413, \"half_prominence_width_nm\": 2.0}, {\"nm\": 839.0, \"local_prominence\": 0.00029526750581383536, \"half_prominence_width_nm\": 44.0}, {\"nm\": 1375.0, \"local_prominence\": 0.2945796908662906, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1378.0, \"local_prominence\": 0.09461442793803967, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1381.0, \"local_prominence\": 0.03754248344308407, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1383.0, \"local_prominence\": 0.02492978332843147, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1386.0, \"local_prominence\": 0.037628172505928995, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1389.0, \"local_prominence\": 0.10063639189185739, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1392.0, \"local_prominence\": 0.11613401527734485, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1394.0, \"local_prominence\": 0.021364226068122348, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1397.0, \"local_prominence\": 0.0654121113200003, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1400.0, \"local_prominence\": 0.07049333051156888, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1402.0, \"local_prominence\": 0.0296583571348049, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1405.0, \"local_prominence\": 0.19471260775712748, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1407.0, \"local_prominence\": 0.02129968987994551, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1410.0, \"local_prominence\": 0.10440460447982923, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1412.0, \"local_prominence\": 0.03544351274868426, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1415.0, \"local_prominence\": 0.026529693572976944, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1417.0, \"local_prominence\": 0.3672888527544741, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1419.0, \"local_prominence\": 0.026681720893788, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1422.0, \"local_prominence\": 0.015731991841123484, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1424.0, \"local_prominence\": 0.0580516670762939, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1426.0, \"local_prominence\": 0.8021756637533538, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1428.0, \"local_prominence\": 0.06779531915263508, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1430.0, \"local_prominence\": 0.034379695648571997, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1432.0, \"local_prominence\": 0.023619230912042394, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1434.0, \"local_prominence\": 0.0174726047653212, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1436.0, \"local_prominence\": 0.019125822476625993, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1438.0, \"local_prominence\": 0.027305131200286756, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1440.0, \"local_prominence\": 0.0548686243419272, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1442.0, \"local_prominence\": 0.9969949968047395, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1444.0, \"local_prominence\": 0.04351414462298761, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1447.0, \"local_prominence\": 0.0161468889843441, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1449.0, \"local_prominence\": 0.8834407558217723, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1452.0, \"local_prominence\": 0.027055300199812192, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1454.0, \"local_prominence\": 0.032452976807618814, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1458.0, \"local_prominence\": 0.028962596520241753, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1461.0, \"local_prominence\": 0.09840289002045553, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1466.0, \"local_prominence\": 0.11642805189885522, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1472.0, \"local_prominence\": 0.0009287691574277764, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1477.0, \"local_prominence\": 0.19278599040909672, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1481.0, \"local_prominence\": 0.03734789747866873, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1483.0, \"local_prominence\": 0.17753974306545506, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1486.0, \"local_prominence\": 0.037083684564444046, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1488.0, \"local_prominence\": 0.017678796984425645, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1492.0, \"local_prominence\": 0.03806289848002228, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1495.0, \"local_prominence\": 0.012682728864732122, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1497.0, \"local_prominence\": 0.13901199908077444, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1501.0, \"local_prominence\": 0.030638034482713357, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1503.0, \"local_prominence\": 0.4014036700531469, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1505.0, \"local_prominence\": 0.05142123107332239, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1511.0, \"local_prominence\": 0.0188696140684109, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1514.0, \"local_prominence\": 5.279858044248201e-05, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1516.0, \"local_prominence\": 0.10624466604307653, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1518.0, \"local_prominence\": 0.0024598850015965217, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1520.0, \"local_prominence\": 0.0002474803712476468, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1522.0, \"local_prominence\": 4.8986759589295104e-05, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1525.0, \"local_prominence\": 0.003963061835562311, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1527.0, \"local_prominence\": 0.0006132476122955727, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1530.0, \"local_prominence\": 0.0014564281974172345, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1534.0, \"local_prominence\": 0.003070395661274523, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1536.0, \"local_prominence\": 0.010811181376455248, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1541.0, \"local_prominence\": 0.0015071326344402221, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1543.0, \"local_prominence\": 0.008077181179753402, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1545.0, \"local_prominence\": 0.0007767368770208657, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1548.0, \"local_prominence\": 0.00883975244014414, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1550.0, \"local_prominence\": 0.017876701725780896, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1552.0, \"local_prominence\": 0.00139614314208035, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1556.0, \"local_prominence\": 0.001928061252028772, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1560.0, \"local_prominence\": 0.002464270295330649, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1563.0, \"local_prominence\": 0.002054537921216611, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1567.0, \"local_prominence\": 0.0036249800990462025, \"half_prominence_width_nm\": 4.0}, {\"nm\": 1570.0, \"local_prominence\": 0.001248371125047598, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1573.0, \"local_prominence\": 0.0012998719336545696, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1576.0, \"local_prominence\": 0.0010947818619768982, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1579.0, \"local_prominence\": 0.005369707750271343, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1581.0, \"local_prominence\": 0.0013911702019950567, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1584.0, \"local_prominence\": 0.002140056022886072, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1586.0, \"local_prominence\": 0.01075253521881599, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1589.0, \"local_prominence\": 0.005966957857514888, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1593.0, \"local_prominence\": 0.0005955913644083181, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1595.0, \"local_prominence\": 0.0007264754829354901, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1597.0, \"local_prominence\": 0.0010743900249437156, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1599.0, \"local_prominence\": 0.001358093964105407, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1601.0, \"local_prominence\": 0.002609970641776531, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1604.0, \"local_prominence\": 0.010050294844005693, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1607.0, \"local_prominence\": 0.0011176864435009978, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1609.0, \"local_prominence\": 0.001461790435725442, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1612.0, \"local_prominence\": 0.002507649570826661, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1614.0, \"local_prominence\": 0.000803166701979335, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1617.0, \"local_prominence\": 0.0010149219130878443, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1620.0, \"local_prominence\": 0.0029616130197979255, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1623.0, \"local_prominence\": 0.0016615311713106978, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1627.0, \"local_prominence\": 0.0025876545064086012, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1635.0, \"local_prominence\": 0.02449254398244263, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1642.0, \"local_prominence\": 0.0015888161062389112, \"half_prominence_width_nm\": 4.0}, {\"nm\": 1645.0, \"local_prominence\": 0.0010137339061070867, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1647.0, \"local_prominence\": 0.0015013357103451567, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1653.0, \"local_prominence\": 0.0006768907313730674, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1655.0, \"local_prominence\": 0.006605135926807728, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1657.0, \"local_prominence\": 0.0010761942402230848, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1659.0, \"local_prominence\": 0.000639214464203482, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1668.0, \"local_prominence\": 0.0003879351498941117, \"half_prominence_width_nm\": 38.0}]"}
```

### TEST 11 — Gamma 0.25 meV magnitude

- **Question:** Does Gamma 0.25 meV magnitude explain the paper discrepancy?
- **Method:** Single prescribed Gamma; 2.5 meV tests paper 5 meV as FWHM; 5 meV tests HWHM. Zero Gamma is off-pole sampled diagnostic only.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** RMSE 0.266403; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=1376.0, P4=1504.0. Full physical reproduction not established.
- **Status:** FAIL
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.26640272893503186, "correlation": 0.23853347092480595, "P1_nm": null, "P1_local_RMSE": 0.19171966692129463, "Z1_nm": null, "Z1_local_RMSE": 0.030045424980731452, "P2_nm": 752.0, "P2_local_RMSE": 0.26908376166389997, "P3_nm": null, "P3_local_RMSE": 0.47443722918979975, "Z2_nm": 1376.0, "Z2_local_RMSE": 0.2082603353677504, "P4_nm": 1504.0, "P4_local_RMSE": 0.3484545819308974, "all_peaks_nm": "687.0;689.0;693.0;696.0;700.0;705.0;713.0;721.0;727.0;729.0;731.0;733.0;739.0;743.0;752.0;768.0;773.0;776.0;778.0;780.0;783.0;785.0;788.0;792.0;806.0;812.0;814.0;817.0;821.0;839.0;1375.0;1377.0;1380.0;1383.0;1386.0;1389.0;1392.0;1394.0;1397.0;1400.0;1402.0;1405.0;1407.0;1410.0;1412.0;1415.0;1417.0;1419.0;1422.0;1424.0;1426.0;1428.0;1430.0;1432.0;1434.0;1436.0;1438.0;1440.0;1442.0;1444.0;1447.0;1449.0;1452.0;1454.0;1457.0;1461.0;1466.0;1477.0;1481.0;1483.0;1485.0;1504.0;1540.0;1545.0;1556.0;1560.0;1563.0;1566.0;1570.0;1573.0;1575.0;1579.0;1581.0;1584.0;1586.0;1591.0;1593.0;1595.0;1597.0;1599.0;1601.0;1603.0;1605.0;1607.0;1609.0;1612.0;1614.0;1617.0;1624.0;1628.0;1668.0", "all_minima_nm": "688.0;691.0;695.0;698.0;703.0;709.0;717.0;725.0;728.0;730.0;732.0;735.0;741.0;744.0;767.0;772.0;775.0;777.0;779.0;782.0;784.0;787.0;791.0;805.0;811.0;813.0;816.0;820.0;830.0;953.0;1376.0;1379.0;1382.0;1385.0;1388.0;1390.0;1393.0;1396.0;1398.0;1401.0;1404.0;1406.0;1409.0;1411.0;1413.0;1416.0;1418.0;1420.0;1423.0;1425.0;1427.0;1429.0;1431.0;1433.0;1435.0;1437.0;1439.0;1441.0;1443.0;1445.0;1448.0;1450.0;1453.0;1456.0;1459.0;1463.0;1471.0;1479.0;1482.0;1484.0;1487.0;1539.0;1544.0;1554.0;1558.0;1561.0;1565.0;1568.0;1572.0;1574.0;1577.0;1580.0;1582.0;1585.0;1590.0;1592.0;1594.0;1596.0;1598.0;1600.0;1602.0;1604.0;1606.0;1608.0;1611.0;1613.0;1616.0;1623.0;1625.0;1661.0", "topology_json": "[{\"nm\": 687.0, \"local_prominence\": 0.12584169278221088, \"half_prominence_width_nm\": 2.0}, {\"nm\": 689.0, \"local_prominence\": 0.08138896058256531, \"half_prominence_width_nm\": 3.0}, {\"nm\": 693.0, \"local_prominence\": 0.11456741007681401, \"half_prominence_width_nm\": 2.0}, {\"nm\": 696.0, \"local_prominence\": 0.11292568377027737, \"half_prominence_width_nm\": 3.0}, {\"nm\": 700.0, \"local_prominence\": 0.0994738856874198, \"half_prominence_width_nm\": 3.0}, {\"nm\": 705.0, \"local_prominence\": 0.11567905001667897, \"half_prominence_width_nm\": 3.0}, {\"nm\": 713.0, \"local_prominence\": 0.04234632579677358, \"half_prominence_width_nm\": 4.0}, {\"nm\": 721.0, \"local_prominence\": 0.028685068515673207, \"half_prominence_width_nm\": 4.0}, {\"nm\": 727.0, \"local_prominence\": 0.06115874879110411, \"half_prominence_width_nm\": 3.0}, {\"nm\": 729.0, \"local_prominence\": 0.01880664519885844, \"half_prominence_width_nm\": 2.0}, {\"nm\": 731.0, \"local_prominence\": 0.008260962581266268, \"half_prominence_width_nm\": 2.0}, {\"nm\": 733.0, \"local_prominence\": 0.048143765087835855, \"half_prominence_width_nm\": 2.0}, {\"nm\": 739.0, \"local_prominence\": 0.017681323974137436, \"half_prominence_width_nm\": 4.0}, {\"nm\": 743.0, \"local_prominence\": 0.0030270961398742025, \"half_prominence_width_nm\": 2.0}, {\"nm\": 752.0, \"local_prominence\": 0.3080266872072752, \"half_prominence_width_nm\": 3.0}, {\"nm\": 768.0, \"local_prominence\": 0.001402729928553531, \"half_prominence_width_nm\": 2.0}, {\"nm\": 773.0, \"local_prominence\": 0.0004577965638675463, \"half_prominence_width_nm\": 2.0}, {\"nm\": 776.0, \"local_prominence\": 0.0005901907019318919, \"half_prominence_width_nm\": 2.0}, {\"nm\": 778.0, \"local_prominence\": 0.002479555975271719, \"half_prominence_width_nm\": 2.0}, {\"nm\": 780.0, \"local_prominence\": 0.0029999382746301873, \"half_prominence_width_nm\": 2.0}, {\"nm\": 783.0, \"local_prominence\": 0.000660534854762293, \"half_prominence_width_nm\": 2.0}, {\"nm\": 785.0, \"local_prominence\": 0.002172460824049968, \"half_prominence_width_nm\": 2.0}, {\"nm\": 788.0, \"local_prominence\": 0.00242934422348097, \"half_prominence_width_nm\": 2.0}, {\"nm\": 792.0, \"local_prominence\": 0.0019424883961359912, \"half_prominence_width_nm\": 2.0}, {\"nm\": 806.0, \"local_prominence\": 0.00012252626178600734, \"half_prominence_width_nm\": 2.0}, {\"nm\": 812.0, \"local_prominence\": 0.0006388613999799633, \"half_prominence_width_nm\": 2.0}, {\"nm\": 814.0, \"local_prominence\": 0.0010884853014043183, \"half_prominence_width_nm\": 2.0}, {\"nm\": 817.0, \"local_prominence\": 2.032673285200237e-05, \"half_prominence_width_nm\": 2.0}, {\"nm\": 821.0, \"local_prominence\": 1.9252556214481575e-05, \"half_prominence_width_nm\": 2.0}, {\"nm\": 839.0, \"local_prominence\": 0.004495492390205531, \"half_prominence_width_nm\": 34.0}, {\"nm\": 1375.0, \"local_prominence\": 0.3009997542594876, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1377.0, \"local_prominence\": 0.15546905320447307, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1380.0, \"local_prominence\": 0.18975788669361038, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1383.0, \"local_prominence\": 0.21454713925902358, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1386.0, \"local_prominence\": 0.21522706261343955, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1389.0, \"local_prominence\": 0.21838214428309816, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1392.0, \"local_prominence\": 0.2253813585024016, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1394.0, \"local_prominence\": 0.17656603150292105, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1397.0, \"local_prominence\": 0.236854373497418, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1400.0, \"local_prominence\": 0.19536600775014962, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1402.0, \"local_prominence\": 0.15752425091503708, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1405.0, \"local_prominence\": 0.17921033064218256, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1407.0, \"local_prominence\": 0.1384714102709947, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1410.0, \"local_prominence\": 0.1709285301427917, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1412.0, \"local_prominence\": 0.1643300253959591, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1415.0, \"local_prominence\": 0.11859624251321499, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1417.0, \"local_prominence\": 0.21997258851904194, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1419.0, \"local_prominence\": 0.13226469273420094, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1422.0, \"local_prominence\": 0.07924817033039872, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1424.0, \"local_prominence\": 0.16310802728539892, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1426.0, \"local_prominence\": 0.2167798814225952, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1428.0, \"local_prominence\": 0.190500458742401, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1430.0, \"local_prominence\": 0.14427532946008703, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1432.0, \"local_prominence\": 0.10779025319022312, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1434.0, \"local_prominence\": 0.09238959130622981, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1436.0, \"local_prominence\": 0.09333177872344373, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1438.0, \"local_prominence\": 0.1138895767520745, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1440.0, \"local_prominence\": 0.1500058134492152, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1442.0, \"local_prominence\": 0.179203128369411, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1444.0, \"local_prominence\": 0.126814282953906, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1447.0, \"local_prominence\": 0.07575556198789579, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1449.0, \"local_prominence\": 0.15217044243945543, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1452.0, \"local_prominence\": 0.10586094050997291, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1454.0, \"local_prominence\": 0.12075920688286346, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1457.0, \"local_prominence\": 0.1073441160948535, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1461.0, \"local_prominence\": 0.11892432782034423, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1466.0, \"local_prominence\": 0.09845805757184883, \"half_prominence_width_nm\": 4.0}, {\"nm\": 1477.0, \"local_prominence\": 0.05856223343544881, \"half_prominence_width_nm\": 4.0}, {\"nm\": 1481.0, \"local_prominence\": 0.046050162248105875, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1483.0, \"local_prominence\": 0.041993992512481204, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1485.0, \"local_prominence\": 0.01554316941715772, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1504.0, \"local_prominence\": 0.6087621484891521, \"half_prominence_width_nm\": 5.0}, {\"nm\": 1540.0, \"local_prominence\": 0.0010409704813909015, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1545.0, \"local_prominence\": 0.0002396296584137314, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1556.0, \"local_prominence\": 0.0021201941441301997, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1560.0, \"local_prominence\": 0.0037556049793360524, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1563.0, \"local_prominence\": 0.004758751495251068, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1566.0, \"local_prominence\": 0.003133797708203906, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1570.0, \"local_prominence\": 0.0008003340885864851, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1573.0, \"local_prominence\": 0.0035376210091042914, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1575.0, \"local_prominence\": 0.0031988735252849315, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1579.0, \"local_prominence\": 0.0008484114432124323, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1581.0, \"local_prominence\": 0.004501413090002515, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1584.0, \"local_prominence\": 0.0019509432190147613, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1586.0, \"local_prominence\": 0.0034903066045174486, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1591.0, \"local_prominence\": 0.0021060915739806313, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1593.0, \"local_prominence\": 0.001963133619349286, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1595.0, \"local_prominence\": 0.0019127243966368807, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1597.0, \"local_prominence\": 0.0012588397814541213, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1599.0, \"local_prominence\": 0.0009366442898448846, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1601.0, \"local_prominence\": 0.00040075891140008146, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1603.0, \"local_prominence\": 0.0012018447068904703, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1605.0, \"local_prominence\": 0.0013328362139383987, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1607.0, \"local_prominence\": 0.002110202646317963, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1609.0, \"local_prominence\": 0.0011960465208526866, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1612.0, \"local_prominence\": 0.0002486918037223479, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1614.0, \"local_prominence\": 0.0012994358971235576, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1617.0, \"local_prominence\": 0.0006651714772228506, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1624.0, \"local_prominence\": 0.000246495137427416, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1628.0, \"local_prominence\": 0.0017235152044862284, \"half_prominence_width_nm\": 4.0}, {\"nm\": 1668.0, \"local_prominence\": 0.0035851265617216216, \"half_prominence_width_nm\": 24.0}]"}
```

### TEST 12 — Gamma 0.25 meV Re

- **Question:** Does Gamma 0.25 meV Re explain the paper discrepancy?
- **Method:** Single prescribed Gamma; 2.5 meV tests paper 5 meV as FWHM; 5 meV tests HWHM. Zero Gamma is off-pole sampled diagnostic only.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** RMSE 0.346574; strict feature locations nm: P1=None, Z1=None, P2=767.0, P3=None, Z2=1374.0, P4=1505.0. Full physical reproduction not established.
- **Status:** FAIL
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.3465738836100932, "correlation": 0.3530603957109477, "P1_nm": null, "P1_local_RMSE": 0.19024757474463597, "Z1_nm": null, "Z1_local_RMSE": 0.02698160410470257, "P2_nm": 767.0, "P2_local_RMSE": 0.5101454764199356, "P3_nm": null, "P3_local_RMSE": 0.5721698294857057, "Z2_nm": 1374.0, "Z2_local_RMSE": 0.32292527354853795, "P4_nm": 1505.0, "P4_local_RMSE": 0.3658418911583173, "all_peaks_nm": "687.0;690.0;693.0;697.0;701.0;706.0;716.0;726.0;729.0;731.0;734.0;737.0;740.0;767.0;772.0;775.0;777.0;779.0;782.0;784.0;787.0;791.0;805.0;811.0;813.0;830.0;953.0;1376.0;1379.0;1381.0;1384.0;1387.0;1390.0;1393.0;1395.0;1398.0;1400.0;1403.0;1406.0;1408.0;1410.0;1413.0;1415.0;1418.0;1420.0;1422.0;1424.0;1427.0;1429.0;1431.0;1433.0;1435.0;1437.0;1439.0;1441.0;1444.0;1446.0;1448.0;1451.0;1454.0;1457.0;1460.0;1465.0;1472.0;1478.0;1481.0;1483.0;1485.0;1492.0;1505.0;1540.0;1545.0;1556.0;1559.0;1563.0;1566.0;1570.0;1573.0;1575.0;1579.0;1581.0;1584.0;1586.0;1591.0;1593.0;1595.0;1597.0;1599.0;1601.0;1603.0;1605.0;1607.0;1609.0;1612.0;1614.0;1617.0;1624.0;1628.0;1668.0", "all_minima_nm": "689.0;692.0;695.0;699.0;704.0;711.0;723.0;727.0;730.0;732.0;736.0;739.0;752.0;768.0;773.0;776.0;778.0;780.0;783.0;785.0;788.0;792.0;806.0;812.0;814.0;839.0;1374.0;1377.0;1380.0;1383.0;1386.0;1389.0;1391.0;1394.0;1397.0;1399.0;1402.0;1404.0;1407.0;1409.0;1412.0;1414.0;1416.0;1419.0;1421.0;1423.0;1425.0;1428.0;1430.0;1432.0;1434.0;1436.0;1438.0;1440.0;1443.0;1445.0;1447.0;1450.0;1452.0;1455.0;1458.0;1462.0;1468.0;1475.0;1480.0;1482.0;1484.0;1486.0;1493.0;1539.0;1544.0;1554.0;1558.0;1561.0;1565.0;1568.0;1572.0;1574.0;1577.0;1580.0;1582.0;1585.0;1590.0;1592.0;1594.0;1596.0;1598.0;1600.0;1602.0;1604.0;1606.0;1608.0;1611.0;1613.0;1616.0;1622.0;1625.0;1661.0", "topology_json": "[{\"nm\": 687.0, \"local_prominence\": 0.22999930697637455, \"half_prominence_width_nm\": 2.0}, {\"nm\": 690.0, \"local_prominence\": 0.08631840469596075, \"half_prominence_width_nm\": 2.0}, {\"nm\": 693.0, \"local_prominence\": 0.15125642283096802, \"half_prominence_width_nm\": 3.0}, {\"nm\": 697.0, \"local_prominence\": 0.12933227995102337, \"half_prominence_width_nm\": 2.0}, {\"nm\": 701.0, \"local_prominence\": 0.124511617038622, \"half_prominence_width_nm\": 3.0}, {\"nm\": 706.0, \"local_prominence\": 0.12512219666084548, \"half_prominence_width_nm\": 4.0}, {\"nm\": 716.0, \"local_prominence\": 0.1023795928242205, \"half_prominence_width_nm\": 9.0}, {\"nm\": 726.0, \"local_prominence\": 0.07802215147701647, \"half_prominence_width_nm\": 3.0}, {\"nm\": 729.0, \"local_prominence\": 0.06965789382314402, \"half_prominence_width_nm\": 2.0}, {\"nm\": 731.0, \"local_prominence\": 0.058557146340060304, \"half_prominence_width_nm\": 2.0}, {\"nm\": 734.0, \"local_prominence\": 0.027542667935846712, \"half_prominence_width_nm\": 2.0}, {\"nm\": 737.0, \"local_prominence\": 0.004191967396888582, \"half_prominence_width_nm\": 2.0}, {\"nm\": 740.0, \"local_prominence\": 0.025187762101541278, \"half_prominence_width_nm\": 2.0}, {\"nm\": 767.0, \"local_prominence\": 0.001462100061388527, \"half_prominence_width_nm\": 2.0}, {\"nm\": 772.0, \"local_prominence\": 0.0006809671092193048, \"half_prominence_width_nm\": 2.0}, {\"nm\": 775.0, \"local_prominence\": 0.00035842477550024343, \"half_prominence_width_nm\": 2.0}, {\"nm\": 777.0, \"local_prominence\": 0.0026750940124558448, \"half_prominence_width_nm\": 2.0}, {\"nm\": 779.0, \"local_prominence\": 0.0030030757608756897, \"half_prominence_width_nm\": 2.0}, {\"nm\": 782.0, \"local_prominence\": 0.0013864626509404454, \"half_prominence_width_nm\": 2.0}, {\"nm\": 784.0, \"local_prominence\": 0.0024140558391504835, \"half_prominence_width_nm\": 2.0}, {\"nm\": 787.0, \"local_prominence\": 0.0027114063007163125, \"half_prominence_width_nm\": 2.0}, {\"nm\": 791.0, \"local_prominence\": 0.0022711056053352774, \"half_prominence_width_nm\": 3.0}, {\"nm\": 805.0, \"local_prominence\": 4.727908755146337e-05, \"half_prominence_width_nm\": 2.0}, {\"nm\": 811.0, \"local_prominence\": 0.002261117246788985, \"half_prominence_width_nm\": 2.0}, {\"nm\": 813.0, \"local_prominence\": 0.0008793108467206184, \"half_prominence_width_nm\": 2.0}, {\"nm\": 830.0, \"local_prominence\": 0.005678139815299174, \"half_prominence_width_nm\": 3.0}, {\"nm\": 953.0, \"local_prominence\": 0.0071448382419902964, \"half_prominence_width_nm\": 173.0}, {\"nm\": 1376.0, \"local_prominence\": 0.18662465806447281, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1379.0, \"local_prominence\": 0.2170797290405999, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1381.0, \"local_prominence\": 0.2648330298461186, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1384.0, \"local_prominence\": 0.3032858506081986, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1387.0, \"local_prominence\": 0.23269388972870492, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1390.0, \"local_prominence\": 0.22801570962495785, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1393.0, \"local_prominence\": 0.20138136995085698, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1395.0, \"local_prominence\": 0.2517484156331009, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1398.0, \"local_prominence\": 0.24771949347724512, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1400.0, \"local_prominence\": 0.21645698021028215, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1403.0, \"local_prominence\": 0.22893186306833951, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1406.0, \"local_prominence\": 0.1454896887492616, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1408.0, \"local_prominence\": 0.23195887563636722, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1410.0, \"local_prominence\": 0.1525199241542789, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1413.0, \"local_prominence\": 0.23969444261238937, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1415.0, \"local_prominence\": 0.15478484701757586, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1418.0, \"local_prominence\": 0.09472888008263894, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1420.0, \"local_prominence\": 0.23421395419368418, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1422.0, \"local_prominence\": 0.20405600639665428, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1424.0, \"local_prominence\": 0.09784270987087577, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1427.0, \"local_prominence\": 0.0553239144786396, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1429.0, \"local_prominence\": 0.13937463812254924, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1431.0, \"local_prominence\": 0.1910893141083977, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1433.0, \"local_prominence\": 0.20007409522004757, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1435.0, \"local_prominence\": 0.19473389880549322, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1437.0, \"local_prominence\": 0.17363783574161756, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1439.0, \"local_prominence\": 0.12267634098673005, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1441.0, \"local_prominence\": 0.0410099587429686, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1444.0, \"local_prominence\": 0.10375840518132894, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1446.0, \"local_prominence\": 0.18243678902146715, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1448.0, \"local_prominence\": 0.0893569165382585, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1451.0, \"local_prominence\": 0.14980386184043148, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1454.0, \"local_prominence\": 0.16293439178775665, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1457.0, \"local_prominence\": 0.14404031208210197, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1460.0, \"local_prominence\": 0.1350584618153188, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1465.0, \"local_prominence\": 0.1167652117790573, \"half_prominence_width_nm\": 4.0}, {\"nm\": 1472.0, \"local_prominence\": 0.015539228545358094, \"half_prominence_width_nm\": 4.0}, {\"nm\": 1478.0, \"local_prominence\": 0.054395806770082294, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1481.0, \"local_prominence\": 0.032503837249647505, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1483.0, \"local_prominence\": 0.014448159686604761, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1485.0, \"local_prominence\": 0.031119361860177108, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1492.0, \"local_prominence\": 0.0006579211265583806, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1505.0, \"local_prominence\": 0.7637545921984963, \"half_prominence_width_nm\": 6.0}, {\"nm\": 1540.0, \"local_prominence\": 0.0013325303666585908, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1545.0, \"local_prominence\": 0.0004135323323097295, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1556.0, \"local_prominence\": 0.0024048578105539675, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1559.0, \"local_prominence\": 0.00394466465068169, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1563.0, \"local_prominence\": 0.005854750955897131, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1566.0, \"local_prominence\": 0.003488239082745287, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1570.0, \"local_prominence\": 0.0008057221278632842, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1573.0, \"local_prominence\": 0.003689212245408441, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1575.0, \"local_prominence\": 0.0042566568599764765, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1579.0, \"local_prominence\": 0.0005655573831236382, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1581.0, \"local_prominence\": 0.005113433370571241, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1584.0, \"local_prominence\": 0.0022448841985238943, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1586.0, \"local_prominence\": 0.0038986453816305666, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1591.0, \"local_prominence\": 0.002205347482394787, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1593.0, \"local_prominence\": 0.0022538602667011853, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1595.0, \"local_prominence\": 0.0024371536513740216, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1597.0, \"local_prominence\": 0.0018839498975282143, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1599.0, \"local_prominence\": 0.0015724059864615364, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1601.0, \"local_prominence\": 0.0008601599061476978, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1603.0, \"local_prominence\": 0.001899320922906081, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1605.0, \"local_prominence\": 0.0019301955716340136, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1607.0, \"local_prominence\": 0.002507873269783939, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1609.0, \"local_prominence\": 0.001014637328534379, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1612.0, \"local_prominence\": 0.0006692870389057998, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1614.0, \"local_prominence\": 0.0013031967845519299, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1617.0, \"local_prominence\": 0.0009271041967077037, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1624.0, \"local_prominence\": 0.000260283864293942, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1628.0, \"local_prominence\": 0.002006199829044486, \"half_prominence_width_nm\": 4.0}, {\"nm\": 1668.0, \"local_prominence\": 0.004215890477164211, \"half_prominence_width_nm\": 24.0}]"}
```

### TEST 13 — Gamma 0.25 meV abs_Re

- **Question:** Does Gamma 0.25 meV abs_Re explain the paper discrepancy?
- **Method:** Single prescribed Gamma; 2.5 meV tests paper 5 meV as FWHM; 5 meV tests HWHM. Zero Gamma is off-pole sampled diagnostic only.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** RMSE 0.266941; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=1376.0, P4=1505.0. Full physical reproduction not established.
- **Status:** FAIL
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.26694064188512207, "correlation": 0.2842817787593213, "P1_nm": null, "P1_local_RMSE": 0.19024757474463597, "Z1_nm": null, "Z1_local_RMSE": 0.02698160410470257, "P2_nm": 752.0, "P2_local_RMSE": 0.30096702037576256, "P3_nm": null, "P3_local_RMSE": 0.46676166723280077, "Z2_nm": 1376.0, "Z2_local_RMSE": 0.19783888729784163, "P4_nm": 1505.0, "P4_local_RMSE": 0.3652257268750344, "all_peaks_nm": "687.0;690.0;693.0;697.0;701.0;704.0;706.0;711.0;716.0;723.0;727.0;730.0;732.0;736.0;739.0;752.0;768.0;773.0;776.0;778.0;780.0;783.0;785.0;788.0;792.0;806.0;812.0;814.0;839.0;1374.0;1377.0;1380.0;1383.0;1386.0;1389.0;1391.0;1394.0;1397.0;1399.0;1402.0;1404.0;1407.0;1409.0;1412.0;1414.0;1416.0;1419.0;1421.0;1423.0;1425.0;1428.0;1430.0;1432.0;1434.0;1436.0;1438.0;1444.0;1446.0;1448.0;1451.0;1454.0;1457.0;1460.0;1465.0;1472.0;1478.0;1481.0;1483.0;1485.0;1492.0;1505.0;1540.0;1545.0;1556.0;1559.0;1563.0;1566.0;1570.0;1573.0;1575.0;1579.0;1581.0;1584.0;1586.0;1591.0;1593.0;1595.0;1597.0;1599.0;1601.0;1603.0;1605.0;1607.0;1609.0;1612.0;1614.0;1617.0;1624.0;1628.0;1668.0", "all_minima_nm": "689.0;692.0;695.0;699.0;703.0;705.0;709.0;713.0;720.0;726.0;729.0;731.0;734.0;737.0;740.0;767.0;772.0;775.0;777.0;779.0;782.0;784.0;787.0;791.0;805.0;811.0;813.0;830.0;953.0;1376.0;1379.0;1381.0;1384.0;1387.0;1390.0;1393.0;1395.0;1398.0;1400.0;1403.0;1406.0;1408.0;1410.0;1413.0;1415.0;1418.0;1420.0;1422.0;1424.0;1427.0;1429.0;1431.0;1433.0;1435.0;1437.0;1443.0;1445.0;1447.0;1450.0;1452.0;1455.0;1458.0;1462.0;1468.0;1475.0;1480.0;1482.0;1484.0;1486.0;1493.0;1539.0;1544.0;1554.0;1558.0;1561.0;1565.0;1568.0;1572.0;1574.0;1577.0;1580.0;1582.0;1585.0;1590.0;1592.0;1594.0;1596.0;1598.0;1600.0;1602.0;1604.0;1606.0;1608.0;1611.0;1613.0;1616.0;1622.0;1625.0;1661.0", "topology_json": "[{\"nm\": 687.0, \"local_prominence\": 0.22999930697637455, \"half_prominence_width_nm\": 2.0}, {\"nm\": 690.0, \"local_prominence\": 0.08631840469596075, \"half_prominence_width_nm\": 2.0}, {\"nm\": 693.0, \"local_prominence\": 0.15125642283096802, \"half_prominence_width_nm\": 3.0}, {\"nm\": 697.0, \"local_prominence\": 0.12933227995102337, \"half_prominence_width_nm\": 2.0}, {\"nm\": 701.0, \"local_prominence\": 0.11396986011865097, \"half_prominence_width_nm\": 3.0}, {\"nm\": 704.0, \"local_prominence\": 0.0014638849579178756, \"half_prominence_width_nm\": 2.0}, {\"nm\": 706.0, \"local_prominence\": 0.08650060642551186, \"half_prominence_width_nm\": 3.0}, {\"nm\": 711.0, \"local_prominence\": 0.047903861982656386, \"half_prominence_width_nm\": 4.0}, {\"nm\": 716.0, \"local_prominence\": 0.03669120084044129, \"half_prominence_width_nm\": 7.0}, {\"nm\": 723.0, \"local_prominence\": 0.0724406332119022, \"half_prominence_width_nm\": 4.0}, {\"nm\": 727.0, \"local_prominence\": 0.07000981155016667, \"half_prominence_width_nm\": 3.0}, {\"nm\": 730.0, \"local_prominence\": 0.06778306952547963, \"half_prominence_width_nm\": 2.0}, {\"nm\": 732.0, \"local_prominence\": 0.041184594590126064, \"half_prominence_width_nm\": 3.0}, {\"nm\": 736.0, \"local_prominence\": 0.004191967396888582, \"half_prominence_width_nm\": 2.0}, {\"nm\": 739.0, \"local_prominence\": 0.025187762101541278, \"half_prominence_width_nm\": 2.0}, {\"nm\": 752.0, \"local_prominence\": 0.3603551281632029, \"half_prominence_width_nm\": 3.0}, {\"nm\": 768.0, \"local_prominence\": 0.001462100061388527, \"half_prominence_width_nm\": 2.0}, {\"nm\": 773.0, \"local_prominence\": 0.0006809671092193048, \"half_prominence_width_nm\": 2.0}, {\"nm\": 776.0, \"local_prominence\": 0.00035842477550024343, \"half_prominence_width_nm\": 2.0}, {\"nm\": 778.0, \"local_prominence\": 0.0026750940124558448, \"half_prominence_width_nm\": 2.0}, {\"nm\": 780.0, \"local_prominence\": 0.0030030757608756897, \"half_prominence_width_nm\": 2.0}, {\"nm\": 783.0, \"local_prominence\": 0.0013864626509404454, \"half_prominence_width_nm\": 2.0}, {\"nm\": 785.0, \"local_prominence\": 0.0024140558391504835, \"half_prominence_width_nm\": 2.0}, {\"nm\": 788.0, \"local_prominence\": 0.0027114063007163125, \"half_prominence_width_nm\": 2.0}, {\"nm\": 792.0, \"local_prominence\": 0.0022711056053352774, \"half_prominence_width_nm\": 2.0}, {\"nm\": 806.0, \"local_prominence\": 4.727908755146337e-05, \"half_prominence_width_nm\": 2.0}, {\"nm\": 812.0, \"local_prominence\": 0.0008793108467206184, \"half_prominence_width_nm\": 2.0}, {\"nm\": 814.0, \"local_prominence\": 0.001381959262832147, \"half_prominence_width_nm\": 2.0}, {\"nm\": 839.0, \"local_prominence\": 0.005678139815299174, \"half_prominence_width_nm\": 36.0}, {\"nm\": 1374.0, \"local_prominence\": 0.38310219028618075, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1377.0, \"local_prominence\": 0.18662465806447281, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1380.0, \"local_prominence\": 0.2170797290405999, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1383.0, \"local_prominence\": 0.2648330298461186, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1386.0, \"local_prominence\": 0.3032858506081986, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1389.0, \"local_prominence\": 0.22801570962495785, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1391.0, \"local_prominence\": 0.20138136995085698, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1394.0, \"local_prominence\": 0.2167789002425105, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1397.0, \"local_prominence\": 0.24771949347724512, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1399.0, \"local_prominence\": 0.21645698021028215, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1402.0, \"local_prominence\": 0.22838492244247022, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1404.0, \"local_prominence\": 0.1454896887492616, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1407.0, \"local_prominence\": 0.1924541206010698, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1409.0, \"local_prominence\": 0.1525199241542789, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1412.0, \"local_prominence\": 0.17830572028119523, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1414.0, \"local_prominence\": 0.17308744350689426, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1416.0, \"local_prominence\": 0.07798650087934297, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1419.0, \"local_prominence\": 0.1445870457982989, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1421.0, \"local_prominence\": 0.10512448978099795, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1423.0, \"local_prominence\": 0.04845200253582277, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1425.0, \"local_prominence\": 0.030589990007338017, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1428.0, \"local_prominence\": 0.07477185887281462, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1430.0, \"local_prominence\": 0.07185664239826206, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1432.0, \"local_prominence\": 0.05736386686731636, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1434.0, \"local_prominence\": 0.0427260656144359, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1436.0, \"local_prominence\": 0.03094298141430052, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1438.0, \"local_prominence\": 0.014911411327831595, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1444.0, \"local_prominence\": 0.0525834816207138, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1446.0, \"local_prominence\": 0.06965803490811155, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1448.0, \"local_prominence\": 0.019652184468750264, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1451.0, \"local_prominence\": 0.11503962859884817, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1454.0, \"local_prominence\": 0.11359052903519495, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1457.0, \"local_prominence\": 0.12738569055760482, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1460.0, \"local_prominence\": 0.1350584618153188, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1465.0, \"local_prominence\": 0.1167652117790573, \"half_prominence_width_nm\": 4.0}, {\"nm\": 1472.0, \"local_prominence\": 0.015539228545358094, \"half_prominence_width_nm\": 4.0}, {\"nm\": 1478.0, \"local_prominence\": 0.054395806770082294, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1481.0, \"local_prominence\": 0.032503837249647505, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1483.0, \"local_prominence\": 0.014448159686604761, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1485.0, \"local_prominence\": 0.031119361860177108, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1492.0, \"local_prominence\": 0.0006579211265583806, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1505.0, \"local_prominence\": 0.7637545921984963, \"half_prominence_width_nm\": 6.0}, {\"nm\": 1540.0, \"local_prominence\": 0.0013325303666585908, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1545.0, \"local_prominence\": 0.0004135323323097295, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1556.0, \"local_prominence\": 0.0024048578105539675, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1559.0, \"local_prominence\": 0.00394466465068169, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1563.0, \"local_prominence\": 0.005854750955897131, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1566.0, \"local_prominence\": 0.003488239082745287, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1570.0, \"local_prominence\": 0.0008057221278632842, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1573.0, \"local_prominence\": 0.003689212245408441, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1575.0, \"local_prominence\": 0.0042566568599764765, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1579.0, \"local_prominence\": 0.0005655573831236382, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1581.0, \"local_prominence\": 0.005113433370571241, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1584.0, \"local_prominence\": 0.0022448841985238943, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1586.0, \"local_prominence\": 0.0038986453816305666, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1591.0, \"local_prominence\": 0.002205347482394787, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1593.0, \"local_prominence\": 0.0022538602667011853, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1595.0, \"local_prominence\": 0.0024371536513740216, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1597.0, \"local_prominence\": 0.0018839498975282143, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1599.0, \"local_prominence\": 0.0015724059864615364, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1601.0, \"local_prominence\": 0.0008601599061476978, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1603.0, \"local_prominence\": 0.001899320922906081, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1605.0, \"local_prominence\": 0.0019301955716340136, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1607.0, \"local_prominence\": 0.002507873269783939, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1609.0, \"local_prominence\": 0.001014637328534379, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1612.0, \"local_prominence\": 0.0006692870389057998, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1614.0, \"local_prominence\": 0.0013031967845519299, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1617.0, \"local_prominence\": 0.0009271041967077037, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1624.0, \"local_prominence\": 0.000260283864293942, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1628.0, \"local_prominence\": 0.002006199829044486, \"half_prominence_width_nm\": 4.0}, {\"nm\": 1668.0, \"local_prominence\": 0.004215890477164211, \"half_prominence_width_nm\": 24.0}]"}
```

### TEST 14 — Gamma 0.5 meV magnitude

- **Question:** Does Gamma 0.5 meV magnitude explain the paper discrepancy?
- **Method:** Single prescribed Gamma; 2.5 meV tests paper 5 meV as FWHM; 5 meV tests HWHM. Zero Gamma is off-pole sampled diagnostic only.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** lower RMSE; reproduction not established
- **Status:** FAIL
- **Improved paper agreement?:** YES
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.2623566308039067, "correlation": 0.24793567990658325, "P1_nm": null, "P1_local_RMSE": 0.19100169565005656, "Z1_nm": null, "Z1_local_RMSE": 0.028501736679663423, "P2_nm": 752.0, "P2_local_RMSE": 0.259229033283336, "P3_nm": null, "P3_local_RMSE": 0.4706937150334189, "Z2_nm": 1376.0, "Z2_local_RMSE": 0.2184689843489242, "P4_nm": 1504.0, "P4_local_RMSE": 0.3336811238045993, "all_peaks_nm": "687.0;693.0;696.0;700.0;705.0;713.0;721.0;727.0;729.0;731.0;733.0;739.0;752.0;813.0;839.0;1375.0;1377.0;1380.0;1383.0;1386.0;1389.0;1392.0;1394.0;1397.0;1400.0;1402.0;1405.0;1407.0;1410.0;1412.0;1415.0;1417.0;1419.0;1422.0;1424.0;1426.0;1428.0;1430.0;1432.0;1434.0;1436.0;1438.0;1440.0;1442.0;1444.0;1447.0;1449.0;1452.0;1454.0;1457.0;1461.0;1466.0;1504.0;1627.0;1668.0", "all_minima_nm": "691.0;695.0;698.0;703.0;709.0;718.0;725.0;728.0;730.0;732.0;734.0;740.0;812.0;830.0;953.0;1376.0;1379.0;1382.0;1385.0;1388.0;1390.0;1393.0;1396.0;1398.0;1401.0;1404.0;1406.0;1409.0;1411.0;1413.0;1416.0;1418.0;1420.0;1423.0;1425.0;1427.0;1429.0;1431.0;1433.0;1435.0;1437.0;1439.0;1441.0;1443.0;1445.0;1448.0;1450.0;1453.0;1456.0;1459.0;1463.0;1469.0;1623.0;1661.0", "topology_json": "[{\"nm\": 687.0, \"local_prominence\": 0.11403746149884095, \"half_prominence_width_nm\": 3.0}, {\"nm\": 693.0, \"local_prominence\": 0.01163993582956166, \"half_prominence_width_nm\": 2.0}, {\"nm\": 696.0, \"local_prominence\": 0.017254671622155937, \"half_prominence_width_nm\": 3.0}, {\"nm\": 700.0, \"local_prominence\": 0.015860127471743368, \"half_prominence_width_nm\": 3.0}, {\"nm\": 705.0, \"local_prominence\": 0.01814734752710026, \"half_prominence_width_nm\": 3.0}, {\"nm\": 713.0, \"local_prominence\": 0.007786381756599375, \"half_prominence_width_nm\": 5.0}, {\"nm\": 721.0, \"local_prominence\": 0.002978248261927108, \"half_prominence_width_nm\": 4.0}, {\"nm\": 727.0, \"local_prominence\": 0.007520120172024247, \"half_prominence_width_nm\": 3.0}, {\"nm\": 729.0, \"local_prominence\": 0.0010021228957121098, \"half_prominence_width_nm\": 2.0}, {\"nm\": 731.0, \"local_prominence\": 1.343184387722629e-05, \"half_prominence_width_nm\": 2.0}, {\"nm\": 733.0, \"local_prominence\": 0.0007701078296708797, \"half_prominence_width_nm\": 2.0}, {\"nm\": 739.0, \"local_prominence\": 0.00019332243867661858, \"half_prominence_width_nm\": 2.0}, {\"nm\": 752.0, \"local_prominence\": 0.30168047746259186, \"half_prominence_width_nm\": 4.0}, {\"nm\": 813.0, \"local_prominence\": 0.0002656363296604722, \"half_prominence_width_nm\": 3.0}, {\"nm\": 839.0, \"local_prominence\": 0.004341562029197846, \"half_prominence_width_nm\": 32.0}, {\"nm\": 1375.0, \"local_prominence\": 0.11399897232258571, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1377.0, \"local_prominence\": 0.007513623142513137, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1380.0, \"local_prominence\": 0.03272719035472882, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1383.0, \"local_prominence\": 0.04203410325723517, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1386.0, \"local_prominence\": 0.044610892076489106, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1389.0, \"local_prominence\": 0.03708256844398511, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1392.0, \"local_prominence\": 0.03342592786324616, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1394.0, \"local_prominence\": 0.04008689705007046, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1397.0, \"local_prominence\": 0.04250207938323125, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1400.0, \"local_prominence\": 0.030102220731302753, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1402.0, \"local_prominence\": 0.034645945767547426, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1405.0, \"local_prominence\": 0.029173577047168275, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1407.0, \"local_prominence\": 0.0300669551275633, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1410.0, \"local_prominence\": 0.02774049771797671, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1412.0, \"local_prominence\": 0.02990991909934526, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1415.0, \"local_prominence\": 0.017688777912058695, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1417.0, \"local_prominence\": 0.03640945029966042, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1419.0, \"local_prominence\": 0.023346911042379737, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1422.0, \"local_prominence\": 0.01141360592573365, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1424.0, \"local_prominence\": 0.025655018320111245, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1426.0, \"local_prominence\": 0.034300460939037325, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1428.0, \"local_prominence\": 0.03085778721760235, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1430.0, \"local_prominence\": 0.023275451066814057, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1432.0, \"local_prominence\": 0.017349830769849084, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1434.0, \"local_prominence\": 0.014316157802489404, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1436.0, \"local_prominence\": 0.013705703026777372, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1438.0, \"local_prominence\": 0.01637898033966434, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1440.0, \"local_prominence\": 0.02107225146625552, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1442.0, \"local_prominence\": 0.024739812953811335, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1444.0, \"local_prominence\": 0.01703907356535289, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1447.0, \"local_prominence\": 0.010368419940260498, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1449.0, \"local_prominence\": 0.019097083384550573, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1452.0, \"local_prominence\": 0.01370333880684893, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1454.0, \"local_prominence\": 0.013415710121412128, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1457.0, \"local_prominence\": 0.011102140386562043, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1461.0, \"local_prominence\": 0.009317389769212647, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1466.0, \"local_prominence\": 0.0022418271226561926, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1504.0, \"local_prominence\": 0.6218000784371565, \"half_prominence_width_nm\": 7.0}, {\"nm\": 1627.0, \"local_prominence\": 0.002928653954421212, \"half_prominence_width_nm\": 11.0}, {\"nm\": 1668.0, \"local_prominence\": 0.003272428361813899, \"half_prominence_width_nm\": 21.0}]"}
```

### TEST 15 — Gamma 0.5 meV Re

- **Question:** Does Gamma 0.5 meV Re explain the paper discrepancy?
- **Method:** Single prescribed Gamma; 2.5 meV tests paper 5 meV as FWHM; 5 meV tests HWHM. Zero Gamma is off-pole sampled diagnostic only.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** RMSE 0.347023; strict feature locations nm: P1=None, Z1=None, P2=731.0, P3=None, Z2=1374.0, P4=1505.0. Full physical reproduction not established.
- **Status:** FAIL
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.34702309380487023, "correlation": 0.3600711004834356, "P1_nm": null, "P1_local_RMSE": 0.1897668596478828, "Z1_nm": null, "Z1_local_RMSE": 0.026075506722430208, "P2_nm": 731.0, "P2_local_RMSE": 0.5158045515108725, "P3_nm": null, "P3_local_RMSE": 0.5747441883208285, "Z2_nm": 1374.0, "Z2_local_RMSE": 0.33020101975801985, "P4_nm": 1505.0, "P4_local_RMSE": 0.3539464705533702, "all_peaks_nm": "687.0;693.0;697.0;701.0;706.0;713.0;725.0;729.0;731.0;811.0;830.0;953.0;1379.0;1382.0;1384.0;1387.0;1390.0;1393.0;1395.0;1398.0;1401.0;1403.0;1406.0;1408.0;1411.0;1413.0;1415.0;1418.0;1420.0;1422.0;1424.0;1427.0;1429.0;1431.0;1433.0;1435.0;1437.0;1439.0;1441.0;1444.0;1446.0;1448.0;1451.0;1454.0;1457.0;1460.0;1465.0;1505.0;1627.0;1668.0", "all_minima_nm": "692.0;695.0;700.0;704.0;711.0;724.0;727.0;730.0;752.0;813.0;839.0;1374.0;1380.0;1383.0;1386.0;1388.0;1391.0;1394.0;1396.0;1399.0;1402.0;1404.0;1407.0;1409.0;1412.0;1414.0;1416.0;1419.0;1421.0;1423.0;1425.0;1428.0;1430.0;1432.0;1434.0;1436.0;1438.0;1440.0;1442.0;1445.0;1447.0;1450.0;1452.0;1455.0;1458.0;1462.0;1467.0;1623.0;1661.0", "topology_json": "[{\"nm\": 687.0, \"local_prominence\": 0.24681519899301946, \"half_prominence_width_nm\": 4.0}, {\"nm\": 693.0, \"local_prominence\": 0.012640016751591321, \"half_prominence_width_nm\": 2.0}, {\"nm\": 697.0, \"local_prominence\": 0.010766144894685276, \"half_prominence_width_nm\": 2.0}, {\"nm\": 701.0, \"local_prominence\": 0.011013212598623826, \"half_prominence_width_nm\": 2.0}, {\"nm\": 706.0, \"local_prominence\": 0.010765859468037334, \"half_prominence_width_nm\": 3.0}, {\"nm\": 713.0, \"local_prominence\": 0.0013319426290699504, \"half_prominence_width_nm\": 3.0}, {\"nm\": 725.0, \"local_prominence\": 0.00302127078755568, \"half_prominence_width_nm\": 2.0}, {\"nm\": 729.0, \"local_prominence\": 0.0027907641335109326, \"half_prominence_width_nm\": 3.0}, {\"nm\": 731.0, \"local_prominence\": 0.003971314428571862, \"half_prominence_width_nm\": 2.0}, {\"nm\": 811.0, \"local_prominence\": 0.0008147357676508843, \"half_prominence_width_nm\": 2.0}, {\"nm\": 830.0, \"local_prominence\": 0.005235695253067475, \"half_prominence_width_nm\": 3.0}, {\"nm\": 953.0, \"local_prominence\": 0.007490630435354362, \"half_prominence_width_nm\": 173.0}, {\"nm\": 1379.0, \"local_prominence\": 0.02734483137687138, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1382.0, \"local_prominence\": 0.027292075971588503, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1384.0, \"local_prominence\": 0.025010785804301272, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1387.0, \"local_prominence\": 0.03523413560852029, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1390.0, \"local_prominence\": 0.046354119922097814, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1393.0, \"local_prominence\": 0.036283851448191184, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1395.0, \"local_prominence\": 0.02469790165373989, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1398.0, \"local_prominence\": 0.04776212679954331, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1401.0, \"local_prominence\": 0.025861278317038217, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1403.0, \"local_prominence\": 0.04039742547800271, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1406.0, \"local_prominence\": 0.029523116083534806, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1408.0, \"local_prominence\": 0.03990513885326169, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1411.0, \"local_prominence\": 0.020424835133585714, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1413.0, \"local_prominence\": 0.0415174563273497, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1415.0, \"local_prominence\": 0.020357408984133185, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1418.0, \"local_prominence\": 0.024563780281182127, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1420.0, \"local_prominence\": 0.03800093939753383, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1422.0, \"local_prominence\": 0.0300645081161523, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1424.0, \"local_prominence\": 0.010202449123050891, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1427.0, \"local_prominence\": 0.010664191532367799, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1429.0, \"local_prominence\": 0.02144179333070019, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1431.0, \"local_prominence\": 0.026097497002227923, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1433.0, \"local_prominence\": 0.026928866794487756, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1435.0, \"local_prominence\": 0.025431838536543204, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1437.0, \"local_prominence\": 0.02158038815108837, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1439.0, \"local_prominence\": 0.013962583797151224, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1441.0, \"local_prominence\": 0.000997414970873075, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1444.0, \"local_prominence\": 0.0159742387630606, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1446.0, \"local_prominence\": 0.021329622329236443, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1448.0, \"local_prominence\": 0.0065592311680026105, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1451.0, \"local_prominence\": 0.0154586313759262, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1454.0, \"local_prominence\": 0.01588607612863137, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1457.0, \"local_prominence\": 0.011760220761123152, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1460.0, \"local_prominence\": 0.00864299225664382, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1465.0, \"local_prominence\": 0.0013592852120905136, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1505.0, \"local_prominence\": 0.9034775209342741, \"half_prominence_width_nm\": 9.0}, {\"nm\": 1627.0, \"local_prominence\": 0.0037103301928014393, \"half_prominence_width_nm\": 11.0}, {\"nm\": 1668.0, \"local_prominence\": 0.0037394074660209026, \"half_prominence_width_nm\": 21.0}]"}
```

### TEST 16 — Gamma 0.5 meV abs_Re

- **Question:** Does Gamma 0.5 meV abs_Re explain the paper discrepancy?
- **Method:** Single prescribed Gamma; 2.5 meV tests paper 5 meV as FWHM; 5 meV tests HWHM. Zero Gamma is off-pole sampled diagnostic only.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** RMSE 0.264477; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=1379.0, P4=1505.0. Full physical reproduction not established.
- **Status:** FAIL
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.26447666664439146, "correlation": 0.2944123926915635, "P1_nm": null, "P1_local_RMSE": 0.1897668596478828, "Z1_nm": null, "Z1_local_RMSE": 0.026075506722430208, "P2_nm": 752.0, "P2_local_RMSE": 0.2978678011364819, "P3_nm": null, "P3_local_RMSE": 0.46425520794125885, "Z2_nm": 1379.0, "Z2_local_RMSE": 0.201777068607951, "P4_nm": 1505.0, "P4_local_RMSE": 0.3539464705533702, "all_peaks_nm": "687.0;693.0;697.0;701.0;706.0;713.0;724.0;727.0;730.0;752.0;813.0;839.0;1374.0;1380.0;1383.0;1386.0;1388.0;1391.0;1394.0;1396.0;1399.0;1402.0;1404.0;1407.0;1409.0;1412.0;1414.0;1416.0;1419.0;1421.0;1423.0;1425.0;1428.0;1430.0;1432.0;1434.0;1436.0;1439.0;1441.0;1444.0;1446.0;1448.0;1451.0;1454.0;1457.0;1460.0;1465.0;1505.0;1627.0;1668.0", "all_minima_nm": "692.0;695.0;700.0;704.0;711.0;715.0;725.0;729.0;731.0;811.0;830.0;953.0;1379.0;1382.0;1384.0;1387.0;1390.0;1393.0;1395.0;1398.0;1401.0;1403.0;1406.0;1408.0;1411.0;1413.0;1415.0;1418.0;1420.0;1422.0;1424.0;1427.0;1429.0;1431.0;1433.0;1435.0;1438.0;1440.0;1442.0;1445.0;1447.0;1450.0;1452.0;1455.0;1458.0;1462.0;1467.0;1623.0;1661.0", "topology_json": "[{\"nm\": 687.0, \"local_prominence\": 0.24681519899301946, \"half_prominence_width_nm\": 4.0}, {\"nm\": 693.0, \"local_prominence\": 0.012640016751591321, \"half_prominence_width_nm\": 2.0}, {\"nm\": 697.0, \"local_prominence\": 0.010766144894685276, \"half_prominence_width_nm\": 2.0}, {\"nm\": 701.0, \"local_prominence\": 0.011013212598623826, \"half_prominence_width_nm\": 2.0}, {\"nm\": 706.0, \"local_prominence\": 0.010765859468037334, \"half_prominence_width_nm\": 3.0}, {\"nm\": 713.0, \"local_prominence\": 0.0013319426290699504, \"half_prominence_width_nm\": 3.0}, {\"nm\": 724.0, \"local_prominence\": 0.00302127078755568, \"half_prominence_width_nm\": 3.0}, {\"nm\": 727.0, \"local_prominence\": 0.0027907641335109326, \"half_prominence_width_nm\": 2.0}, {\"nm\": 730.0, \"local_prominence\": 0.003971314428571862, \"half_prominence_width_nm\": 2.0}, {\"nm\": 752.0, \"local_prominence\": 0.4401365846505758, \"half_prominence_width_nm\": 6.0}, {\"nm\": 813.0, \"local_prominence\": 0.0008147357676508843, \"half_prominence_width_nm\": 4.0}, {\"nm\": 839.0, \"local_prominence\": 0.005235695253067475, \"half_prominence_width_nm\": 33.0}, {\"nm\": 1374.0, \"local_prominence\": 0.37472046424463346, \"half_prominence_width_nm\": 4.0}, {\"nm\": 1380.0, \"local_prominence\": 0.02734483137687138, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1383.0, \"local_prominence\": 0.027292075971588503, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1386.0, \"local_prominence\": 0.025010785804301272, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1388.0, \"local_prominence\": 0.03523413560852029, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1391.0, \"local_prominence\": 0.046354119922097814, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1394.0, \"local_prominence\": 0.036283851448191184, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1396.0, \"local_prominence\": 0.02469790165373989, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1399.0, \"local_prominence\": 0.04752727769593759, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1402.0, \"local_prominence\": 0.025861278317038217, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1404.0, \"local_prominence\": 0.04039742547800271, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1407.0, \"local_prominence\": 0.029523116083534806, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1409.0, \"local_prominence\": 0.03660231687381825, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1412.0, \"local_prominence\": 0.020424835133585714, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1414.0, \"local_prominence\": 0.0415174563273497, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1416.0, \"local_prominence\": 0.020357408984133185, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1419.0, \"local_prominence\": 0.024563780281182127, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1421.0, \"local_prominence\": 0.03800093939753383, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1423.0, \"local_prominence\": 0.029213826212549865, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1425.0, \"local_prominence\": 0.010202449123050891, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1428.0, \"local_prominence\": 0.010664191532367799, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1430.0, \"local_prominence\": 0.02144179333070019, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1432.0, \"local_prominence\": 0.026097497002227923, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1434.0, \"local_prominence\": 0.017116117641267654, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1436.0, \"local_prominence\": 0.008614227307567057, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1439.0, \"local_prominence\": 0.010777987640713981, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1441.0, \"local_prominence\": 0.000997414970873075, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1444.0, \"local_prominence\": 0.0159742387630606, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1446.0, \"local_prominence\": 0.021329622329236443, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1448.0, \"local_prominence\": 0.0065592311680026105, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1451.0, \"local_prominence\": 0.0154586313759262, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1454.0, \"local_prominence\": 0.01588607612863137, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1457.0, \"local_prominence\": 0.011760220761123152, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1460.0, \"local_prominence\": 0.00864299225664382, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1465.0, \"local_prominence\": 0.0013592852120905136, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1505.0, \"local_prominence\": 0.9034775209342741, \"half_prominence_width_nm\": 9.0}, {\"nm\": 1627.0, \"local_prominence\": 0.0037103301928014393, \"half_prominence_width_nm\": 11.0}, {\"nm\": 1668.0, \"local_prominence\": 0.0037394074660209026, \"half_prominence_width_nm\": 21.0}]"}
```

### TEST 17 — Gamma 1 meV magnitude

- **Question:** Does Gamma 1 meV magnitude explain the paper discrepancy?
- **Method:** Single prescribed Gamma; 2.5 meV tests paper 5 meV as FWHM; 5 meV tests HWHM. Zero Gamma is off-pole sampled diagnostic only.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** lower RMSE; reproduction not established
- **Status:** FAIL
- **Improved paper agreement?:** YES
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.25864174937871687, "correlation": 0.24871690828384357, "P1_nm": null, "P1_local_RMSE": 0.18963560288137557, "Z1_nm": null, "Z1_local_RMSE": 0.025837601729266125, "P2_nm": 752.0, "P2_local_RMSE": 0.24157391354662716, "P3_nm": null, "P3_local_RMSE": 0.4635709327482324, "Z2_nm": null, "Z2_local_RMSE": 0.2523084676534063, "P4_nm": 1504.0, "P4_local_RMSE": 0.310249740242679, "all_peaks_nm": "687.0;726.0;752.0;813.0;839.0;1375.0;1440.0;1442.0;1444.0;1447.0;1449.0;1451.0;1504.0;1627.0;1668.0", "all_minima_nm": "720.0;728.0;812.0;830.0;953.0;1439.0;1441.0;1443.0;1445.0;1448.0;1450.0;1456.0;1623.0;1661.0", "topology_json": "[{\"nm\": 687.0, \"local_prominence\": 0.14762124025068746, \"half_prominence_width_nm\": 5.0}, {\"nm\": 726.0, \"local_prominence\": 0.000941128308128647, \"half_prominence_width_nm\": 2.0}, {\"nm\": 752.0, \"local_prominence\": 0.30209411435260225, \"half_prominence_width_nm\": 5.0}, {\"nm\": 813.0, \"local_prominence\": 0.00015422556869526538, \"half_prominence_width_nm\": 2.0}, {\"nm\": 839.0, \"local_prominence\": 0.003790104484503787, \"half_prominence_width_nm\": 27.0}, {\"nm\": 1375.0, \"local_prominence\": 0.35909632470477726, \"half_prominence_width_nm\": 10.0}, {\"nm\": 1440.0, \"local_prominence\": 2.9567820603926265e-05, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1442.0, \"local_prominence\": 0.0001902825424768273, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1444.0, \"local_prominence\": 0.0002313195802902679, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1447.0, \"local_prominence\": 8.767178764113037e-05, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1449.0, \"local_prominence\": 0.00018440426285770695, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1451.0, \"local_prominence\": 0.00029421539149143694, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1504.0, \"local_prominence\": 0.5816869039932719, \"half_prominence_width_nm\": 8.0}, {\"nm\": 1627.0, \"local_prominence\": 0.0014481538272414773, \"half_prominence_width_nm\": 7.0}, {\"nm\": 1668.0, \"local_prominence\": 0.002460471477869014, \"half_prominence_width_nm\": 17.0}]"}
```

### TEST 18 — Gamma 1 meV Re

- **Question:** Does Gamma 1 meV Re explain the paper discrepancy?
- **Method:** Single prescribed Gamma; 2.5 meV tests paper 5 meV as FWHM; 5 meV tests HWHM. Zero Gamma is off-pole sampled diagnostic only.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** RMSE 0.351096; strict feature locations nm: P1=None, Z1=None, P2=812.0, P3=None, Z2=1374.0, P4=1505.0. Full physical reproduction not established.
- **Status:** FAIL
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.3510958136104766, "correlation": 0.36207188547244246, "P1_nm": null, "P1_local_RMSE": 0.18851715501082206, "Z1_nm": null, "Z1_local_RMSE": 0.023994758063198052, "P2_nm": 812.0, "P2_local_RMSE": 0.5285833720481878, "P3_nm": null, "P3_local_RMSE": 0.5814524884866864, "Z2_nm": 1374.0, "Z2_local_RMSE": 0.3570078213912007, "P4_nm": 1505.0, "P4_local_RMSE": 0.3293807747454156, "all_peaks_nm": "687.0;812.0;830.0;953.0;1505.0;1627.0;1668.0", "all_minima_nm": "752.0;813.0;839.0;1374.0;1623.0;1661.0", "topology_json": "[{\"nm\": 687.0, \"local_prominence\": 0.3853445712294275, \"half_prominence_width_nm\": 10.0}, {\"nm\": 812.0, \"local_prominence\": 0.0002606051537849263, \"half_prominence_width_nm\": 2.0}, {\"nm\": 830.0, \"local_prominence\": 0.004435614744167732, \"half_prominence_width_nm\": 3.0}, {\"nm\": 953.0, \"local_prominence\": 0.008392789068613772, \"half_prominence_width_nm\": 173.0}, {\"nm\": 1505.0, \"local_prominence\": 0.9000412730557303, \"half_prominence_width_nm\": 12.0}, {\"nm\": 1627.0, \"local_prominence\": 0.002142851833959597, \"half_prominence_width_nm\": 8.0}, {\"nm\": 1668.0, \"local_prominence\": 0.0027754057346933425, \"half_prominence_width_nm\": 17.0}]"}
```

### TEST 19 — Gamma 1 meV abs_Re

- **Question:** Does Gamma 1 meV abs_Re explain the paper discrepancy?
- **Method:** Single prescribed Gamma; 2.5 meV tests paper 5 meV as FWHM; 5 meV tests HWHM. Zero Gamma is off-pole sampled diagnostic only.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** lower RMSE; reproduction not established
- **Status:** FAIL
- **Improved paper agreement?:** YES
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.2585494749795117, "correlation": 0.2983864239515873, "P1_nm": null, "P1_local_RMSE": 0.18851715501082206, "Z1_nm": null, "Z1_local_RMSE": 0.023994758063198052, "P2_nm": 752.0, "P2_local_RMSE": 0.2853709797710063, "P3_nm": null, "P3_local_RMSE": 0.45773944426477553, "Z2_nm": null, "Z2_local_RMSE": 0.22653717347241328, "P4_nm": 1505.0, "P4_local_RMSE": 0.3293807747454156, "all_peaks_nm": "687.0;752.0;813.0;839.0;1374.0;1505.0;1627.0;1668.0", "all_minima_nm": "714.0;812.0;830.0;953.0;1437.0;1623.0;1661.0", "topology_json": "[{\"nm\": 687.0, \"local_prominence\": 0.3853445712294275, \"half_prominence_width_nm\": 10.0}, {\"nm\": 752.0, \"local_prominence\": 0.4332032172060612, \"half_prominence_width_nm\": 7.0}, {\"nm\": 813.0, \"local_prominence\": 0.0002606051537849263, \"half_prominence_width_nm\": 2.0}, {\"nm\": 839.0, \"local_prominence\": 0.004435614744167732, \"half_prominence_width_nm\": 28.0}, {\"nm\": 1374.0, \"local_prominence\": 0.7609525808020411, \"half_prominence_width_nm\": 17.0}, {\"nm\": 1505.0, \"local_prominence\": 0.9000412730557303, \"half_prominence_width_nm\": 12.0}, {\"nm\": 1627.0, \"local_prominence\": 0.002142851833959597, \"half_prominence_width_nm\": 8.0}, {\"nm\": 1668.0, \"local_prominence\": 0.0027754057346933425, \"half_prominence_width_nm\": 17.0}]"}
```

### TEST 20 — Gamma 2.5 meV magnitude

- **Question:** Does Gamma 2.5 meV magnitude explain the paper discrepancy?
- **Method:** Single prescribed Gamma; 2.5 meV tests paper 5 meV as FWHM; 5 meV tests HWHM. Zero Gamma is off-pole sampled diagnostic only.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** lower RMSE; reproduction not established
- **Status:** FAIL
- **Improved paper agreement?:** YES
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.25701436004928346, "correlation": 0.2486935473866522, "P1_nm": null, "P1_local_RMSE": 0.18669967273769503, "Z1_nm": null, "Z1_local_RMSE": 0.021867185482771563, "P2_nm": 752.0, "P2_local_RMSE": 0.20875644951199107, "P3_nm": null, "P3_local_RMSE": 0.4482653587545177, "Z2_nm": null, "Z2_local_RMSE": 0.3226008088669049, "P4_nm": 1504.0, "P4_local_RMSE": 0.27613042682923794, "all_peaks_nm": "688.0;726.0;752.0;838.0;1375.0;1504.0;1667.0", "all_minima_nm": "720.0;727.0;831.0;953.0;1456.0;1662.0", "topology_json": "[{\"nm\": 688.0, \"local_prominence\": 0.1297576413468784, \"half_prominence_width_nm\": 7.0}, {\"nm\": 726.0, \"local_prominence\": 0.00010021181489516806, \"half_prominence_width_nm\": 2.0}, {\"nm\": 752.0, \"local_prominence\": 0.25007841137753184, \"half_prominence_width_nm\": 7.0}, {\"nm\": 838.0, \"local_prominence\": 0.002346120204489932, \"half_prominence_width_nm\": 18.0}, {\"nm\": 1375.0, \"local_prominence\": 0.3232051572827239, \"half_prominence_width_nm\": 16.0}, {\"nm\": 1504.0, \"local_prominence\": 0.469075820975553, \"half_prominence_width_nm\": 13.0}, {\"nm\": 1667.0, \"local_prominence\": 0.0005244133873093387, \"half_prominence_width_nm\": 8.0}]"}
```

### TEST 21 — Gamma 2.5 meV Re

- **Question:** Does Gamma 2.5 meV Re explain the paper discrepancy?
- **Method:** Single prescribed Gamma; 2.5 meV tests paper 5 meV as FWHM; 5 meV tests HWHM. Zero Gamma is off-pole sampled diagnostic only.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** RMSE 0.364208; strict feature locations nm: P1=None, Z1=None, P2=None, P3=None, Z2=1374.0, P4=1505.0. Full physical reproduction not established.
- **Status:** FAIL
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.36420828596079385, "correlation": 0.36451138753778317, "P1_nm": null, "P1_local_RMSE": 0.18523309850552355, "Z1_nm": null, "Z1_local_RMSE": 0.021128539419001113, "P2_nm": null, "P2_local_RMSE": 0.5611844105535139, "P3_nm": null, "P3_local_RMSE": 0.5991911577585181, "Z2_nm": 1374.0, "Z2_local_RMSE": 0.4256037377946981, "P4_nm": 1505.0, "P4_local_RMSE": 0.2691288769820404, "all_peaks_nm": "687.0;831.0;953.0;1505.0;1667.0", "all_minima_nm": "752.0;838.0;1374.0;1662.0", "topology_json": "[{\"nm\": 687.0, \"local_prominence\": 0.406019617827075, \"half_prominence_width_nm\": 14.0}, {\"nm\": 831.0, \"local_prominence\": 0.002663386751705507, \"half_prominence_width_nm\": 4.0}, {\"nm\": 953.0, \"local_prominence\": 0.010802842439045196, \"half_prominence_width_nm\": 173.0}, {\"nm\": 1505.0, \"local_prominence\": 0.8948969747526825, \"half_prominence_width_nm\": 20.0}, {\"nm\": 1667.0, \"local_prominence\": 0.0006141073752203574, \"half_prominence_width_nm\": 9.0}]"}
```

### TEST 22 — Gamma 2.5 meV abs_Re

- **Question:** Does Gamma 2.5 meV abs_Re explain the paper discrepancy?
- **Method:** Single prescribed Gamma; 2.5 meV tests paper 5 meV as FWHM; 5 meV tests HWHM. Zero Gamma is off-pole sampled diagnostic only.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** lower RMSE; reproduction not established
- **Status:** FAIL
- **Improved paper agreement?:** YES
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.24652177865918046, "correlation": 0.3047884918640022, "P1_nm": null, "P1_local_RMSE": 0.18523309850552355, "Z1_nm": null, "Z1_local_RMSE": 0.021128539419001113, "P2_nm": 752.0, "P2_local_RMSE": 0.25505701681360726, "P3_nm": null, "P3_local_RMSE": 0.4406206944097724, "Z2_nm": null, "Z2_local_RMSE": 0.2914739314972305, "P4_nm": 1505.0, "P4_local_RMSE": 0.2691288769820404, "all_peaks_nm": "687.0;752.0;838.0;1374.0;1505.0;1667.0", "all_minima_nm": "714.0;831.0;953.0;1437.0;1662.0", "topology_json": "[{\"nm\": 687.0, \"local_prominence\": 0.406019617827075, \"half_prominence_width_nm\": 14.0}, {\"nm\": 752.0, \"local_prominence\": 0.43982889880674686, \"half_prominence_width_nm\": 12.0}, {\"nm\": 838.0, \"local_prominence\": 0.002663386751705507, \"half_prominence_width_nm\": 18.0}, {\"nm\": 1374.0, \"local_prominence\": 0.7989184095122263, \"half_prominence_width_nm\": 27.0}, {\"nm\": 1505.0, \"local_prominence\": 0.8948969747526825, \"half_prominence_width_nm\": 20.0}, {\"nm\": 1667.0, \"local_prominence\": 0.0006141073752203574, \"half_prominence_width_nm\": 9.0}]"}
```

### TEST 23 — Gamma 5 meV magnitude

- **Question:** Does Gamma 5 meV magnitude explain the paper discrepancy?
- **Method:** Single prescribed Gamma; 2.5 meV tests paper 5 meV as FWHM; 5 meV tests HWHM. Zero Gamma is off-pole sampled diagnostic only.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** RMSE 0.262391; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=None, P4=1503.0. Full physical reproduction not established.
- **Status:** FAIL
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.26239111786932695, "correlation": 0.24755539373540594, "P1_nm": null, "P1_local_RMSE": 0.18355832245681228, "Z1_nm": null, "Z1_local_RMSE": 0.02149182751741102, "P2_nm": 752.0, "P2_local_RMSE": 0.18300269017624166, "P3_nm": null, "P3_local_RMSE": 0.43189844880285366, "Z2_nm": null, "Z2_local_RMSE": 0.3889313933218363, "P4_nm": 1503.0, "P4_local_RMSE": 0.2637088552636287, "all_peaks_nm": "688.0;752.0;837.0;1376.0;1503.0", "all_minima_nm": "720.0;832.0;953.0;1455.0", "topology_json": "[{\"nm\": 688.0, \"local_prominence\": 0.09763940881279826, \"half_prominence_width_nm\": 10.0}, {\"nm\": 752.0, \"local_prominence\": 0.19711267904504853, \"half_prominence_width_nm\": 11.0}, {\"nm\": 837.0, \"local_prominence\": 0.0006496885138127656, \"half_prominence_width_nm\": 9.0}, {\"nm\": 1376.0, \"local_prominence\": 0.2621557638752432, \"half_prominence_width_nm\": 22.0}, {\"nm\": 1503.0, \"local_prominence\": 0.354655473337367, \"half_prominence_width_nm\": 18.0}]"}
```

### TEST 24 — Gamma 5 meV Re

- **Question:** Does Gamma 5 meV Re explain the paper discrepancy?
- **Method:** Single prescribed Gamma; 2.5 meV tests paper 5 meV as FWHM; 5 meV tests HWHM. Zero Gamma is off-pole sampled diagnostic only.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** RMSE 0.383379; strict feature locations nm: P1=None, Z1=None, P2=None, P3=None, Z2=1374.0, P4=1505.0. Full physical reproduction not established.
- **Status:** FAIL
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.38337877530443165, "correlation": 0.3643059329585638, "P1_nm": null, "P1_local_RMSE": 0.1812118642714305, "Z1_nm": null, "Z1_local_RMSE": 0.024024322877130237, "P2_nm": null, "P2_local_RMSE": 0.5986789881100909, "P3_nm": null, "P3_local_RMSE": 0.6211349283907983, "Z2_nm": 1374.0, "Z2_local_RMSE": 0.5027403667611652, "P4_nm": 1505.0, "P4_local_RMSE": 0.20405132706773954, "all_peaks_nm": "687.0;831.0;953.0;1505.0", "all_minima_nm": "753.0;837.0;1374.0", "topology_json": "[{\"nm\": 687.0, \"local_prominence\": 0.42513774532254006, \"half_prominence_width_nm\": 19.0}, {\"nm\": 831.0, \"local_prominence\": 0.0007812501805682243, \"half_prominence_width_nm\": 4.0}, {\"nm\": 953.0, \"local_prominence\": 0.013939696817684089, \"half_prominence_width_nm\": 175.0}, {\"nm\": 1505.0, \"local_prominence\": 0.9171183458165177, \"half_prominence_width_nm\": 34.0}]"}
```

### TEST 25 — Gamma 5 meV abs_Re

- **Question:** Does Gamma 5 meV abs_Re explain the paper discrepancy?
- **Method:** Single prescribed Gamma; 2.5 meV tests paper 5 meV as FWHM; 5 meV tests HWHM. Zero Gamma is off-pole sampled diagnostic only.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** lower RMSE; reproduction not established
- **Status:** FAIL
- **Improved paper agreement?:** YES
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.23787347931116054, "correlation": 0.3096300795070898, "P1_nm": null, "P1_local_RMSE": 0.1812118642714305, "Z1_nm": null, "Z1_local_RMSE": 0.024024322877130237, "P2_nm": 753.0, "P2_local_RMSE": 0.2212267507487411, "P3_nm": null, "P3_local_RMSE": 0.419675646517712, "Z2_nm": null, "Z2_local_RMSE": 0.36529336340893653, "P4_nm": 1505.0, "P4_local_RMSE": 0.20405132706773954, "all_peaks_nm": "687.0;753.0;837.0;1374.0;1505.0", "all_minima_nm": "714.0;831.0;953.0;1437.0", "topology_json": "[{\"nm\": 687.0, \"local_prominence\": 0.42513774532254006, \"half_prominence_width_nm\": 19.0}, {\"nm\": 753.0, \"local_prominence\": 0.4374506695641285, \"half_prominence_width_nm\": 16.0}, {\"nm\": 837.0, \"local_prominence\": 0.0007812501805682243, \"half_prominence_width_nm\": 10.0}, {\"nm\": 1374.0, \"local_prominence\": 0.8329744491991558, \"half_prominence_width_nm\": 36.0}, {\"nm\": 1505.0, \"local_prominence\": 0.9171183458165177, \"half_prominence_width_nm\": 34.0}]"}
```

### TEST 26 — Gamma 7.5 meV magnitude

- **Question:** Does Gamma 7.5 meV magnitude explain the paper discrepancy?
- **Method:** Single prescribed Gamma; 2.5 meV tests paper 5 meV as FWHM; 5 meV tests HWHM. Zero Gamma is off-pole sampled diagnostic only.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** RMSE 0.269308; strict feature locations nm: P1=None, Z1=None, P2=751.0, P3=None, Z2=None, P4=1502.0. Full physical reproduction not established.
- **Status:** FAIL
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.2693075585629605, "correlation": 0.24605418532249682, "P1_nm": null, "P1_local_RMSE": 0.18121778569840727, "Z1_nm": null, "Z1_local_RMSE": 0.02401486412393711, "P2_nm": 751.0, "P2_local_RMSE": 0.17017642912012715, "P3_nm": null, "P3_local_RMSE": 0.41971644968363964, "Z2_nm": null, "Z2_local_RMSE": 0.4317914044411856, "P4_nm": 1502.0, "P4_local_RMSE": 0.26733719446287935, "all_peaks_nm": "689.0;751.0;1378.0;1502.0", "all_minima_nm": "719.0;953.0;1452.0", "topology_json": "[{\"nm\": 689.0, \"local_prominence\": 0.07323350320166605, \"half_prominence_width_nm\": 12.0}, {\"nm\": 751.0, \"local_prominence\": 0.16221377875336074, \"half_prominence_width_nm\": 12.0}, {\"nm\": 1378.0, \"local_prominence\": 0.2168286786322574, \"half_prominence_width_nm\": 25.0}, {\"nm\": 1502.0, \"local_prominence\": 0.2759099198596029, \"half_prominence_width_nm\": 21.0}]"}
```

### TEST 27 — Gamma 7.5 meV Re

- **Question:** Does Gamma 7.5 meV Re explain the paper discrepancy?
- **Method:** Single prescribed Gamma; 2.5 meV tests paper 5 meV as FWHM; 5 meV tests HWHM. Zero Gamma is off-pole sampled diagnostic only.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** RMSE 0.399482; strict feature locations nm: P1=None, Z1=None, P2=None, P3=None, Z2=1374.0, P4=1506.0. Full physical reproduction not established.
- **Status:** FAIL
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.39948226116954255, "correlation": 0.3617506718033266, "P1_nm": null, "P1_local_RMSE": 0.17809662251167185, "Z1_nm": null, "Z1_local_RMSE": 0.030007778157242856, "P2_nm": null, "P2_local_RMSE": 0.6252218403571429, "P3_nm": null, "P3_local_RMSE": 0.6383107436510842, "Z2_nm": 1374.0, "Z2_local_RMSE": 0.5563404890545637, "P4_nm": 1506.0, "P4_local_RMSE": 0.1618262465129404, "all_peaks_nm": "687.0;953.0;1506.0", "all_minima_nm": "753.0;1374.0", "topology_json": "[{\"nm\": 687.0, \"local_prominence\": 0.4332746765861856, \"half_prominence_width_nm\": 24.0}, {\"nm\": 953.0, \"local_prominence\": 0.44325105363539324, \"half_prominence_width_nm\": 543.0}, {\"nm\": 1506.0, \"local_prominence\": 0.9033145550453849, \"half_prominence_width_nm\": 43.0}]"}
```

### TEST 28 — Gamma 7.5 meV abs_Re

- **Question:** Does Gamma 7.5 meV abs_Re explain the paper discrepancy?
- **Method:** Single prescribed Gamma; 2.5 meV tests paper 5 meV as FWHM; 5 meV tests HWHM. Zero Gamma is off-pole sampled diagnostic only.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** lower RMSE; reproduction not established
- **Status:** FAIL
- **Improved paper agreement?:** YES
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.235070545326637, "correlation": 0.3112137823680091, "P1_nm": null, "P1_local_RMSE": 0.17809662251167185, "Z1_nm": null, "Z1_local_RMSE": 0.030007778157242856, "P2_nm": 753.0, "P2_local_RMSE": 0.1978433393621022, "P3_nm": null, "P3_local_RMSE": 0.4034718738089436, "Z2_nm": null, "Z2_local_RMSE": 0.416730424370305, "P4_nm": 1506.0, "P4_local_RMSE": 0.1618262465129404, "all_peaks_nm": "687.0;753.0;1374.0;1506.0", "all_minima_nm": "714.0;953.0;1438.0", "topology_json": "[{\"nm\": 687.0, \"local_prominence\": 0.4332746765861856, \"half_prominence_width_nm\": 24.0}, {\"nm\": 753.0, \"local_prominence\": 0.44325105363539324, \"half_prominence_width_nm\": 22.0}, {\"nm\": 1374.0, \"local_prominence\": 0.846001988681302, \"half_prominence_width_nm\": 45.0}, {\"nm\": 1506.0, \"local_prominence\": 0.9033145550453849, \"half_prominence_width_nm\": 43.0}]"}
```

### TEST 29 — Gamma 10 meV magnitude

- **Question:** Does Gamma 10 meV magnitude explain the paper discrepancy?
- **Method:** Single prescribed Gamma; 2.5 meV tests paper 5 meV as FWHM; 5 meV tests HWHM. Zero Gamma is off-pole sampled diagnostic only.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** RMSE 0.275894; strict feature locations nm: P1=None, Z1=None, P2=751.0, P3=None, Z2=None, P4=1501.0. Full physical reproduction not established.
- **Status:** FAIL
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.275894384206534, "correlation": 0.24448225766991524, "P1_nm": null, "P1_local_RMSE": 0.17928052614580192, "Z1_nm": null, "Z1_local_RMSE": 0.02746680537953755, "P2_nm": 751.0, "P2_local_RMSE": 0.16317896352026842, "P3_nm": null, "P3_local_RMSE": 0.4096461893035752, "Z2_nm": null, "Z2_local_RMSE": 0.4630094170961708, "P4_nm": 1501.0, "P4_local_RMSE": 0.2755113065028484, "all_peaks_nm": "690.0;751.0;1380.0;1501.0", "all_minima_nm": "719.0;953.0;1450.0", "topology_json": "[{\"nm\": 690.0, \"local_prominence\": 0.053710654349106934, \"half_prominence_width_nm\": 14.0}, {\"nm\": 751.0, \"local_prominence\": 0.13439520524767445, \"half_prominence_width_nm\": 14.0}, {\"nm\": 1380.0, \"local_prominence\": 0.17986112377748587, \"half_prominence_width_nm\": 29.0}, {\"nm\": 1501.0, \"local_prominence\": 0.21596904061023114, \"half_prominence_width_nm\": 24.0}]"}
```

### TEST 30 — Gamma 10 meV Re

- **Question:** Does Gamma 10 meV Re explain the paper discrepancy?
- **Method:** Single prescribed Gamma; 2.5 meV tests paper 5 meV as FWHM; 5 meV tests HWHM. Zero Gamma is off-pole sampled diagnostic only.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** RMSE 0.414332; strict feature locations nm: P1=None, Z1=None, P2=None, P3=None, Z2=1374.0, P4=1507.0. Full physical reproduction not established.
- **Status:** FAIL
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.4143315247694479, "correlation": 0.3579330912176984, "P1_nm": null, "P1_local_RMSE": 0.17532934773453615, "Z1_nm": null, "Z1_local_RMSE": 0.0367647339628934, "P2_nm": null, "P2_local_RMSE": 0.6470724121160073, "P3_nm": null, "P3_local_RMSE": 0.6537029090764295, "Z2_nm": 1374.0, "Z2_local_RMSE": 0.6001155850948345, "P4_nm": 1507.0, "P4_local_RMSE": 0.13261764260821657, "all_peaks_nm": "687.0;953.0;1507.0", "all_minima_nm": "753.0;1374.0", "topology_json": "[{\"nm\": 687.0, \"local_prominence\": 0.43860417922211564, \"half_prominence_width_nm\": 28.0}, {\"nm\": 953.0, \"local_prominence\": 0.4357119476980832, \"half_prominence_width_nm\": 529.0}, {\"nm\": 1507.0, \"local_prominence\": 0.890984751065983, \"half_prominence_width_nm\": 52.0}]"}
```

### TEST 31 — Gamma 10 meV abs_Re

- **Question:** Does Gamma 10 meV abs_Re explain the paper discrepancy?
- **Method:** Single prescribed Gamma; 2.5 meV tests paper 5 meV as FWHM; 5 meV tests HWHM. Zero Gamma is off-pole sampled diagnostic only.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** lower RMSE; reproduction not established
- **Status:** FAIL
- **Improved paper agreement?:** YES
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.2350748069791234, "correlation": 0.3110110113220014, "P1_nm": null, "P1_local_RMSE": 0.17532934773453615, "Z1_nm": null, "Z1_local_RMSE": 0.0367647339628934, "P2_nm": 753.0, "P2_local_RMSE": 0.17926160839675828, "P3_nm": null, "P3_local_RMSE": 0.3891032754879411, "Z2_nm": null, "Z2_local_RMSE": 0.458843753579588, "P4_nm": 1507.0, "P4_local_RMSE": 0.13261764260821657, "all_peaks_nm": "687.0;753.0;1374.0;1507.0", "all_minima_nm": "714.0;953.0;1438.0", "topology_json": "[{\"nm\": 687.0, \"local_prominence\": 0.43860417922211564, \"half_prominence_width_nm\": 28.0}, {\"nm\": 753.0, \"local_prominence\": 0.4357119476980832, \"half_prominence_width_nm\": 26.0}, {\"nm\": 1374.0, \"local_prominence\": 0.8538179251884123, \"half_prominence_width_nm\": 52.0}, {\"nm\": 1507.0, \"local_prominence\": 0.890984751065983, \"half_prominence_width_nm\": 52.0}]"}
```

### TEST 32 — full16

- **Question:** Does full16 explain the paper discrepancy?
- **Method:** Sum named original pathways; all other inputs fixed. DIAGNOSTIC ONLY; terms are not removed from production.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** RMSE 0.262391; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=None, P4=1503.0. Full physical reproduction not established.
- **Status:** FAIL
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.26239111786932695, "correlation": 0.2475553937354057, "P1_nm": null, "P1_local_RMSE": 0.18355832245681228, "Z1_nm": null, "Z1_local_RMSE": 0.02149182751741102, "P2_nm": 752.0, "P2_local_RMSE": 0.1830026901762417, "P3_nm": null, "P3_local_RMSE": 0.4318984488028537, "Z2_nm": null, "Z2_local_RMSE": 0.38893139332183607, "P4_nm": 1503.0, "P4_local_RMSE": 0.26370885526362864, "all_peaks_nm": "688.0;752.0;837.0;1376.0;1503.0", "all_minima_nm": "720.0;832.0;953.0;1455.0", "topology_json": "[{\"nm\": 688.0, \"local_prominence\": 0.09763940881279815, \"half_prominence_width_nm\": 10.0}, {\"nm\": 752.0, \"local_prominence\": 0.19711267904504837, \"half_prominence_width_nm\": 11.0}, {\"nm\": 837.0, \"local_prominence\": 0.0006496885138139175, \"half_prominence_width_nm\": 9.0}, {\"nm\": 1376.0, \"local_prominence\": 0.262155763875242, \"half_prominence_width_nm\": 22.0}, {\"nm\": 1503.0, \"local_prominence\": 0.35465547333736713, \"half_prominence_width_nm\": 18.0}]"}
```

### TEST 33 — electron_diagonal

- **Question:** Does electron_diagonal explain the paper discrepancy?
- **Method:** Sum named original pathways; all other inputs fixed. DIAGNOSTIC ONLY; terms are not removed from production.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** lower RMSE; reproduction not established
- **Status:** FAIL
- **Improved paper agreement?:** YES
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.22875958614116007, "correlation": 0.44144962907421004, "P1_nm": null, "P1_local_RMSE": 0.18242478761253653, "Z1_nm": null, "Z1_local_RMSE": 0.02259287059941943, "P2_nm": 742.0, "P2_local_RMSE": 0.12107066723670727, "P3_nm": null, "P3_local_RMSE": 0.39709204448421315, "Z2_nm": null, "Z2_local_RMSE": 0.2130108686245864, "P4_nm": 1483.0, "P4_local_RMSE": 0.2876245883000571, "all_peaks_nm": "688.0;742.0;829.0;1375.0;1483.0;1657.0", "all_minima_nm": "704.0;770.0;1031.0;1407.0;1557.0", "topology_json": "[{\"nm\": 688.0, \"local_prominence\": 0.020105411557098413, \"half_prominence_width_nm\": 7.0}, {\"nm\": 742.0, \"local_prominence\": 0.10957873139850194, \"half_prominence_width_nm\": 14.0}, {\"nm\": 829.0, \"local_prominence\": 0.09511017642122083, \"half_prominence_width_nm\": 15.0}, {\"nm\": 1375.0, \"local_prominence\": 0.04682165972569785, \"half_prominence_width_nm\": 13.0}, {\"nm\": 1483.0, \"local_prominence\": 0.28481256156440626, \"half_prominence_width_nm\": 28.0}, {\"nm\": 1657.0, \"local_prominence\": 0.10406475029700246, \"half_prominence_width_nm\": 19.0}]"}
```

### TEST 34 — hh_diagonal

- **Question:** Does hh_diagonal explain the paper discrepancy?
- **Method:** Sum named original pathways; all other inputs fixed. DIAGNOSTIC ONLY; terms are not removed from production.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** lower RMSE; reproduction not established
- **Status:** FAIL
- **Improved paper agreement?:** YES
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.22820110076485076, "correlation": 0.4547629075880542, "P1_nm": null, "P1_local_RMSE": 0.18336572951312274, "Z1_nm": null, "Z1_local_RMSE": 0.023170012422798654, "P2_nm": 742.0, "P2_local_RMSE": 0.12291014729695525, "P3_nm": null, "P3_local_RMSE": 0.40147811861032223, "Z2_nm": 1394.0, "Z2_local_RMSE": 0.18758900008904655, "P4_nm": 1483.0, "P4_local_RMSE": 0.2900892861482705, "all_peaks_nm": "688.0;742.0;829.0;1375.0;1483.0;1591.0;1657.0", "all_minima_nm": "697.0;770.0;1034.0;1394.0;1566.0;1604.0", "topology_json": "[{\"nm\": 688.0, \"local_prominence\": 0.010327087751171582, \"half_prominence_width_nm\": 5.0}, {\"nm\": 742.0, \"local_prominence\": 0.10260198907136742, \"half_prominence_width_nm\": 14.0}, {\"nm\": 829.0, \"local_prominence\": 0.09127661136631132, \"half_prominence_width_nm\": 14.0}, {\"nm\": 1375.0, \"local_prominence\": 0.02370380572187042, \"half_prominence_width_nm\": 10.0}, {\"nm\": 1483.0, \"local_prominence\": 0.2726505536254573, \"half_prominence_width_nm\": 27.0}, {\"nm\": 1591.0, \"local_prominence\": 0.0002041382345868703, \"half_prominence_width_nm\": 13.0}, {\"nm\": 1657.0, \"local_prominence\": 0.09820535083344062, \"half_prominence_width_nm\": 18.0}]"}
```

### TEST 35 — both_diagonal

- **Question:** Does both_diagonal explain the paper discrepancy?
- **Method:** Sum named original pathways; all other inputs fixed. DIAGNOSTIC ONLY; terms are not removed from production.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** lower RMSE; reproduction not established
- **Status:** FAIL
- **Improved paper agreement?:** YES
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.2573411097117974, "correlation": 0.24623245899283747, "P1_nm": null, "P1_local_RMSE": 0.18194574247724812, "Z1_nm": null, "Z1_local_RMSE": 0.022632488377727383, "P2_nm": 751.0, "P2_local_RMSE": 0.17500349602108545, "P3_nm": null, "P3_local_RMSE": 0.41937216451680137, "Z2_nm": null, "Z2_local_RMSE": 0.39990052605939963, "P4_nm": 1502.0, "P4_local_RMSE": 0.264039080223265, "all_peaks_nm": "688.0;751.0;829.0;1376.0;1502.0;1657.0", "all_minima_nm": "722.0;823.0;970.0;1450.0;1649.0", "topology_json": "[{\"nm\": 688.0, \"local_prominence\": 0.09652636125859254, \"half_prominence_width_nm\": 10.0}, {\"nm\": 751.0, \"local_prominence\": 0.19650547910890553, \"half_prominence_width_nm\": 11.0}, {\"nm\": 829.0, \"local_prominence\": 0.001233642675011859, \"half_prominence_width_nm\": 5.0}, {\"nm\": 1376.0, \"local_prominence\": 0.2532489862485596, \"half_prominence_width_nm\": 22.0}, {\"nm\": 1502.0, \"local_prominence\": 0.3428399458405561, \"half_prominence_width_nm\": 20.0}, {\"nm\": 1657.0, \"local_prominence\": 0.0010843032892376703, \"half_prominence_width_nm\": 7.0}]"}
```

### TEST 36 — offdiagonal_only

- **Question:** Does offdiagonal_only explain the paper discrepancy?
- **Method:** Sum named original pathways; all other inputs fixed. DIAGNOSTIC ONLY; terms are not removed from production.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** lower RMSE; reproduction not established
- **Status:** FAIL
- **Improved paper agreement?:** YES
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.22149362434378725, "correlation": 0.52660328826202, "P1_nm": null, "P1_local_RMSE": 0.18818085491749945, "Z1_nm": null, "Z1_local_RMSE": 0.03171518883285119, "P2_nm": 755.0, "P2_local_RMSE": 0.08743596043857213, "P3_nm": null, "P3_local_RMSE": 0.4222197714386991, "Z2_nm": 1369.0, "Z2_local_RMSE": 0.1374001400882661, "P4_nm": 1509.0, "P4_local_RMSE": 0.2635064331268461, "all_peaks_nm": "661.0;698.0;741.0;755.0;810.0;829.0;1331.0;1397.0;1482.0;1509.0;1619.0;1657.0", "all_minima_nm": "682.0;705.0;748.0;781.0;817.0;1054.0;1369.0;1415.0;1496.0;1573.0;1637.0", "topology_json": "[{\"nm\": 661.0, \"local_prominence\": 0.020483649225478115, \"half_prominence_width_nm\": 67.0}, {\"nm\": 698.0, \"local_prominence\": 0.020369096038889756, \"half_prominence_width_nm\": 5.0}, {\"nm\": 741.0, \"local_prominence\": 0.048394834355115324, \"half_prominence_width_nm\": 6.0}, {\"nm\": 755.0, \"local_prominence\": 0.07304933420054921, \"half_prominence_width_nm\": 13.0}, {\"nm\": 810.0, \"local_prominence\": 0.015983175800940386, \"half_prominence_width_nm\": 8.0}, {\"nm\": 829.0, \"local_prominence\": 0.037488834838122764, \"half_prominence_width_nm\": 7.0}, {\"nm\": 1331.0, \"local_prominence\": 0.049144778469642464, \"half_prominence_width_nm\": 121.0}, {\"nm\": 1397.0, \"local_prominence\": 0.07627656282960565, \"half_prominence_width_nm\": 11.0}, {\"nm\": 1482.0, \"local_prominence\": 0.08507376742963979, \"half_prominence_width_nm\": 10.0}, {\"nm\": 1509.0, \"local_prominence\": 0.1637099577346387, \"half_prominence_width_nm\": 24.0}, {\"nm\": 1619.0, \"local_prominence\": 0.03374397386333894, \"half_prominence_width_nm\": 18.0}, {\"nm\": 1657.0, \"local_prominence\": 0.04212203043746099, \"half_prominence_width_nm\": 12.0}]"}
```

### TEST 37 — electron_family

- **Question:** Does electron_family explain the paper discrepancy?
- **Method:** Sum named original pathways; all other inputs fixed. DIAGNOSTIC ONLY; terms are not removed from production.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** lower RMSE; reproduction not established
- **Status:** FAIL
- **Improved paper agreement?:** YES
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.22883185024248995, "correlation": 0.4413808638944794, "P1_nm": null, "P1_local_RMSE": 0.1824718973789819, "Z1_nm": null, "Z1_local_RMSE": 0.02260574614143166, "P2_nm": 742.0, "P2_local_RMSE": 0.1217111079361637, "P3_nm": null, "P3_local_RMSE": 0.397355201333614, "Z2_nm": null, "Z2_local_RMSE": 0.21186142425018287, "P4_nm": 1483.0, "P4_local_RMSE": 0.2882071478466437, "all_peaks_nm": "688.0;742.0;829.0;1375.0;1483.0;1657.0", "all_minima_nm": "703.0;768.0;1031.0;1406.0;1557.0", "topology_json": "[{\"nm\": 688.0, \"local_prominence\": 0.021813264477082095, \"half_prominence_width_nm\": 7.0}, {\"nm\": 742.0, \"local_prominence\": 0.10969341136282901, \"half_prominence_width_nm\": 14.0}, {\"nm\": 829.0, \"local_prominence\": 0.09545205812775098, \"half_prominence_width_nm\": 15.0}, {\"nm\": 1375.0, \"local_prominence\": 0.05060216490046082, \"half_prominence_width_nm\": 14.0}, {\"nm\": 1483.0, \"local_prominence\": 0.2835136006940331, \"half_prominence_width_nm\": 27.0}, {\"nm\": 1657.0, \"local_prominence\": 0.10371710076639917, \"half_prominence_width_nm\": 19.0}]"}
```

### TEST 38 — hh_family

- **Question:** Does hh_family explain the paper discrepancy?
- **Method:** Sum named original pathways; all other inputs fixed. DIAGNOSTIC ONLY; terms are not removed from production.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** lower RMSE; reproduction not established
- **Status:** FAIL
- **Improved paper agreement?:** YES
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.22824196774083313, "correlation": 0.4557556985345697, "P1_nm": null, "P1_local_RMSE": 0.1834573834097621, "Z1_nm": null, "Z1_local_RMSE": 0.023245044367487217, "P2_nm": 742.0, "P2_local_RMSE": 0.12325114649042938, "P3_nm": null, "P3_local_RMSE": 0.4019102720768142, "Z2_nm": 1394.0, "Z2_local_RMSE": 0.1852269039093503, "P4_nm": 1483.0, "P4_local_RMSE": 0.290727408812571, "all_peaks_nm": "688.0;742.0;829.0;1375.0;1483.0;1591.0;1657.0", "all_minima_nm": "697.0;770.0;1035.0;1394.0;1567.0;1603.0", "topology_json": "[{\"nm\": 688.0, \"local_prominence\": 0.010454030409475318, \"half_prominence_width_nm\": 5.0}, {\"nm\": 742.0, \"local_prominence\": 0.10198294431294502, \"half_prominence_width_nm\": 14.0}, {\"nm\": 829.0, \"local_prominence\": 0.09081738048369115, \"half_prominence_width_nm\": 14.0}, {\"nm\": 1375.0, \"local_prominence\": 0.02371076222298185, \"half_prominence_width_nm\": 11.0}, {\"nm\": 1483.0, \"local_prominence\": 0.2711014665978151, \"half_prominence_width_nm\": 26.0}, {\"nm\": 1591.0, \"local_prominence\": 0.00016050521652455352, \"half_prominence_width_nm\": 13.0}, {\"nm\": 1657.0, \"local_prominence\": 0.09716112611972705, \"half_prominence_width_nm\": 18.0}]"}
```

### TEST 39 — cancellation P1

- **Question:** Does cancellation P1 explain the paper discrepancy?
- **Method:** Signed electron and hole subtotals at target, ratio |e+h|/(|e|+|h|).
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** see quantitative evidence
- **Status:** PASS
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"feature": "P1", "wavelength_nm": 540.0, "electron_real": 20.946259967172146, "electron_imag": 0.1936972803788714, "signed_hh_real": -19.423724086945004, "signed_hh_imag": -0.17737900225088074, "total_real": 1.5225358802271423, "total_imag": 0.016318278127990665, "phase_difference_deg": -179.99339639245207, "cancellation_ratio": 0.037715125219602436}
- **Physics interpretation:** Destructive interference is present; a small ratio is not an exact complex zero. Dominance table ranks all 16 pathways.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** NO
- **Requires new Pro data?:** NO

### TEST 40 — cancellation Z1

- **Question:** Does cancellation Z1 explain the paper discrepancy?
- **Method:** Signed electron and hole subtotals at target, ratio |e+h|/(|e|+|h|).
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** see quantitative evidence
- **Status:** PASS
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"feature": "Z1", "wavelength_nm": 605.0, "electron_real": 40.3196822311979, "electron_imag": 0.5842110619661846, "signed_hh_real": -37.00782666686283, "signed_hh_imag": -0.5230857941075492, "total_real": 3.311855564335069, "total_imag": 0.06112526785863537, "phase_difference_deg": -179.97966348568096, "cancellation_ratio": 0.042831846478639836}
- **Physics interpretation:** Destructive interference is present; a small ratio is not an exact complex zero. Dominance table ranks all 16 pathways.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** NO
- **Requires new Pro data?:** NO

### TEST 41 — cancellation P2

- **Question:** Does cancellation P2 explain the paper discrepancy?
- **Method:** Signed electron and hole subtotals at target, ratio |e+h|/(|e|+|h|).
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** see quantitative evidence
- **Status:** PASS
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"feature": "P2", "wavelength_nm": 760.0, "electron_real": 27.19496138555708, "electron_imag": 379.4452784199754, "signed_hh_real": -53.20552610789165, "signed_hh_imag": -377.8111817472073, "total_real": -26.01056472233457, "total_imag": 1.6340966727681234, "phase_difference_deg": -176.08339182498176, "cancellation_ratio": 0.034203794281949605}
- **Physics interpretation:** Destructive interference is present; a small ratio is not an exact complex zero. Dominance table ranks all 16 pathways.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** NO
- **Requires new Pro data?:** NO

### TEST 42 — cancellation P3

- **Question:** Does cancellation P3 explain the paper discrepancy?
- **Method:** Signed electron and hole subtotals at target, ratio |e+h|/(|e|+|h|).
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** see quantitative evidence
- **Status:** PASS
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"feature": "P3", "wavelength_nm": 1080.0, "electron_real": -133.86775662498871, "electron_imag": 0.48639554529138834, "signed_hh_real": 126.4625936001835, "signed_hh_imag": -0.4892063110969436, "total_real": -7.405163024805219, "total_imag": -0.002810765805555282, "phase_difference_deg": -179.98653658747452, "cancellation_ratio": 0.028445056451096244}
- **Physics interpretation:** Destructive interference is present; a small ratio is not an exact complex zero. Dominance table ranks all 16 pathways.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** NO
- **Requires new Pro data?:** NO

### TEST 43 — cancellation Z2

- **Question:** Does cancellation Z2 explain the paper discrepancy?
- **Method:** Signed electron and hole subtotals at target, ratio |e+h|/(|e|+|h|).
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** see quantitative evidence
- **Status:** PASS
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"feature": "Z2", "wavelength_nm": 1330.0, "electron_real": -272.12699275049295, "electron_imag": -5.404385104747929, "signed_hh_real": 246.9183456399751, "signed_hh_imag": 4.372553538492792, "total_real": -25.20864711051786, "total_imag": -1.0318315662551374, "phase_difference_deg": -179.87678365259748, "cancellation_ratio": 0.04859935049385214}
- **Physics interpretation:** Destructive interference is present; a small ratio is not an exact complex zero. Dominance table ranks all 16 pathways.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** NO
- **Requires new Pro data?:** NO

### TEST 44 — cancellation P4

- **Question:** Does cancellation P4 explain the paper discrepancy?
- **Method:** Signed electron and hole subtotals at target, ratio |e+h|/(|e|+|h|).
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** see quantitative evidence
- **Status:** PASS
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"feature": "P4", "wavelength_nm": 1520.0, "electron_real": -151.2138085330646, "electron_imag": -758.4581492361423, "signed_hh_real": 196.95155648651635, "signed_hh_imag": 755.4057808663321, "total_real": 45.73774795345176, "total_imag": -3.0523683698102104, "phase_difference_deg": -176.6622170304522, "cancellation_ratio": 0.029496911825835123}
- **Physics interpretation:** Destructive interference is present; a small ratio is not an exact complex zero. Dominance table ranks all 16 pathways.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** NO
- **Requires new Pro data?:** NO

### TEST 45 — production

- **Question:** Does production explain the paper discrepancy?
- **Method:** Existing independent integration convention.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** RMSE 0.262391; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=None, P4=1503.0. Full physical reproduction not established.
- **Status:** PASS
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"max_normalized_shape_difference": 0.0}
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.26239111786932695, "correlation": 0.24755539373540594, "P1_nm": null, "P1_local_RMSE": 0.18355832245681228, "Z1_nm": null, "Z1_local_RMSE": 0.02149182751741102, "P2_nm": 752.0, "P2_local_RMSE": 0.18300269017624166, "P3_nm": null, "P3_local_RMSE": 0.43189844880285366, "Z2_nm": null, "Z2_local_RMSE": 0.3889313933218363, "P4_nm": 1503.0, "P4_local_RMSE": 0.2637088552636287, "all_peaks_nm": "688.0;752.0;837.0;1376.0;1503.0", "all_minima_nm": "720.0;832.0;953.0;1455.0", "topology_json": "[{\"nm\": 688.0, \"local_prominence\": 0.09763940881279826, \"half_prominence_width_nm\": 10.0}, {\"nm\": 752.0, \"local_prominence\": 0.19711267904504853, \"half_prominence_width_nm\": 11.0}, {\"nm\": 837.0, \"local_prominence\": 0.0006496885138127656, \"half_prominence_width_nm\": 9.0}, {\"nm\": 1376.0, \"local_prominence\": 0.2621557638752432, \"half_prominence_width_nm\": 22.0}, {\"nm\": 1503.0, \"local_prominence\": 0.354655473337367, \"half_prominence_width_nm\": 18.0}]"}
```

### TEST 46 — radial_kdk

- **Question:** Does radial_kdk explain the paper discrepancy?
- **Method:** Existing independent integration convention.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** RMSE 0.262391; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=None, P4=1503.0. Full physical reproduction not established.
- **Status:** PASS
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"max_normalized_shape_difference": 1.2503886814840826e-14}
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.2623911178693275, "correlation": 0.2475553937354054, "P1_nm": null, "P1_local_RMSE": 0.1835583224568122, "Z1_nm": null, "Z1_local_RMSE": 0.02149182751741106, "P2_nm": 752.0, "P2_local_RMSE": 0.18300269017624132, "P3_nm": null, "P3_local_RMSE": 0.4318984488028532, "Z2_nm": null, "Z2_local_RMSE": 0.38893139332183885, "P4_nm": 1503.0, "P4_local_RMSE": 0.26370885526362936, "all_peaks_nm": "688.0;752.0;837.0;1376.0;1503.0", "all_minima_nm": "720.0;832.0;953.0;1455.0", "topology_json": "[{\"nm\": 688.0, \"local_prominence\": 0.09763940881279792, \"half_prominence_width_nm\": 10.0}, {\"nm\": 752.0, \"local_prominence\": 0.1971126790450447, \"half_prominence_width_nm\": 11.0}, {\"nm\": 837.0, \"local_prominence\": 0.0006496885138115444, \"half_prominence_width_nm\": 9.0}, {\"nm\": 1376.0, \"local_prominence\": 0.26215576387524464, \"half_prominence_width_nm\": 22.0}, {\"nm\": 1503.0, \"local_prominence\": 0.35465547333736336, \"half_prominence_width_nm\": 18.0}]"}
```

### TEST 47 — bare_2pi_kdk

- **Question:** Does bare_2pi_kdk explain the paper discrepancy?
- **Method:** Existing independent integration convention.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** RMSE 0.262391; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=None, P4=1503.0. Full physical reproduction not established.
- **Status:** PASS
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"max_normalized_shape_difference": 9.2148511043888e-15}
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.2623911178693274, "correlation": 0.2475553937354057, "P1_nm": null, "P1_local_RMSE": 0.18355832245681222, "Z1_nm": null, "Z1_local_RMSE": 0.021491827517411053, "P2_nm": 752.0, "P2_local_RMSE": 0.18300269017624127, "P3_nm": null, "P3_local_RMSE": 0.4318984488028533, "Z2_nm": null, "Z2_local_RMSE": 0.3889313933218386, "P4_nm": 1503.0, "P4_local_RMSE": 0.26370885526362897, "all_peaks_nm": "688.0;752.0;837.0;1376.0;1503.0", "all_minima_nm": "720.0;832.0;953.0;1455.0", "topology_json": "[{\"nm\": 688.0, \"local_prominence\": 0.09763940881279892, \"half_prominence_width_nm\": 10.0}, {\"nm\": 752.0, \"local_prominence\": 0.1971126790450472, \"half_prominence_width_nm\": 11.0}, {\"nm\": 837.0, \"local_prominence\": 0.0006496885138131819, \"half_prominence_width_nm\": 9.0}, {\"nm\": 1376.0, \"local_prominence\": 0.262155763875245, \"half_prominence_width_nm\": 22.0}, {\"nm\": 1503.0, \"local_prominence\": 0.3546554733373638, \"half_prominence_width_nm\": 18.0}]"}
```

### TEST 48 — equal_points

- **Question:** Does equal_points explain the paper discrepancy?
- **Method:** Existing independent integration convention.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** lower RMSE; reproduction not established
- **Status:** FAIL
- **Improved paper agreement?:** YES
- **Quantitative evidence / file:** {"max_normalized_shape_difference": 0.6306803176528296}
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.25156634396657046, "correlation": 0.46087425168917745, "P1_nm": null, "P1_local_RMSE": 0.19303968409874311, "Z1_nm": null, "Z1_local_RMSE": 0.034248571761500105, "P2_nm": 752.0, "P2_local_RMSE": 0.2599384392771152, "P3_nm": null, "P3_local_RMSE": 0.47923359587986075, "Z2_nm": null, "Z2_local_RMSE": 0.10367449102305028, "P4_nm": 1504.0, "P4_local_RMSE": 0.2977460631327455, "all_peaks_nm": "688.0;752.0;847.0;1376.0;1504.0;1678.0", "all_minima_nm": "704.0;833.0;967.0;1411.0;1666.0", "topology_json": "[{\"nm\": 688.0, \"local_prominence\": 0.014939819684746364, \"half_prominence_width_nm\": 6.0}, {\"nm\": 752.0, \"local_prominence\": 0.39593714390557694, \"half_prominence_width_nm\": 10.0}, {\"nm\": 847.0, \"local_prominence\": 0.0033874162573269695, \"half_prominence_width_nm\": 35.0}, {\"nm\": 1376.0, \"local_prominence\": 0.040359731382891895, \"half_prominence_width_nm\": 14.0}, {\"nm\": 1504.0, \"local_prominence\": 0.7628630139524281, \"half_prominence_width_nm\": 19.0}, {\"nm\": 1678.0, \"local_prominence\": 0.0012098525363125195, \"half_prominence_width_nm\": 19.0}]"}
```

### TEST 49 — k0_only

- **Question:** Does k0_only explain the paper discrepancy?
- **Method:** Existing independent integration convention.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** RMSE 0.289887; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=None, P4=1504.0. Full physical reproduction not established.
- **Status:** FAIL
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"max_normalized_shape_difference": 0.8729412027869796}
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.2898866438627277, "correlation": 0.5043311312785315, "P1_nm": null, "P1_local_RMSE": 0.19841040871828147, "Z1_nm": null, "Z1_local_RMSE": 0.047987890392264324, "P2_nm": 752.0, "P2_local_RMSE": 0.3306429334023006, "P3_nm": null, "P3_local_RMSE": 0.5075682210109417, "Z2_nm": null, "Z2_local_RMSE": 0.08098068306823929, "P4_nm": 1504.0, "P4_local_RMSE": 0.39860285058050665, "all_peaks_nm": "752.0;808.0;829.0;860.0;1504.0;1617.0;1657.0;1698.0", "all_minima_nm": "804.0;814.0;836.0;992.0;1608.0;1630.0;1670.0", "topology_json": "[{\"nm\": 752.0, \"local_prominence\": 0.4649791645905631, \"half_prominence_width_nm\": 8.0}, {\"nm\": 808.0, \"local_prominence\": 0.00046683119373309295, \"half_prominence_width_nm\": 4.0}, {\"nm\": 829.0, \"local_prominence\": 0.01156260403428912, \"half_prominence_width_nm\": 7.0}, {\"nm\": 860.0, \"local_prominence\": 0.0018883602561489462, \"half_prominence_width_nm\": 59.0}, {\"nm\": 1504.0, \"local_prominence\": 0.9470581743362351, \"half_prominence_width_nm\": 15.0}, {\"nm\": 1617.0, \"local_prominence\": 0.0014939322139096989, \"half_prominence_width_nm\": 7.0}, {\"nm\": 1657.0, \"local_prominence\": 0.01149084514871545, \"half_prominence_width_nm\": 14.0}, {\"nm\": 1698.0, \"local_prominence\": 0.0033744890701448513, \"half_prominence_width_nm\": 67.0}]"}
```

### TEST 50 — Simpson

- **Question:** Does Simpson explain the paper discrepancy?
- **Method:** Uniform raw grid; Simpson composite 1/3 or diagnostic one-sided endpoints.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** RMSE 0.262396; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=None, P4=1503.0. Full physical reproduction not established.
- **Status:** FAIL
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.2623961024429558, "correlation": 0.24754500297222987, "P1_nm": null, "P1_local_RMSE": 0.18355841396657252, "Z1_nm": null, "Z1_local_RMSE": 0.02149177650653649, "P2_nm": 752.0, "P2_local_RMSE": 0.1830030527016125, "P3_nm": null, "P3_local_RMSE": 0.4318987701866007, "Z2_nm": null, "Z2_local_RMSE": 0.38896016052032695, "P4_nm": 1503.0, "P4_local_RMSE": 0.26370759421326634, "all_peaks_nm": "688.0;752.0;837.0;1376.0;1503.0", "all_minima_nm": "720.0;832.0;953.0;1455.0", "topology_json": "[{\"nm\": 688.0, \"local_prominence\": 0.09793995173303943, \"half_prominence_width_nm\": 9.0}, {\"nm\": 752.0, \"local_prominence\": 0.19711367783520717, \"half_prominence_width_nm\": 11.0}, {\"nm\": 837.0, \"local_prominence\": 0.0006497033787091488, \"half_prominence_width_nm\": 9.0}, {\"nm\": 1376.0, \"local_prominence\": 0.2627618112469008, \"half_prominence_width_nm\": 22.0}, {\"nm\": 1503.0, \"local_prominence\": 0.3546649931644523, \"half_prominence_width_nm\": 18.0}]"}
```

### TEST 51 — left_rectangle

- **Question:** Does left_rectangle explain the paper discrepancy?
- **Method:** Uniform raw grid; Simpson composite 1/3 or diagnostic one-sided endpoints.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** lower RMSE; reproduction not established
- **Status:** FAIL
- **Improved paper agreement?:** YES
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.26227545900689125, "correlation": 0.24861503217988454, "P1_nm": null, "P1_local_RMSE": 0.18361641952968796, "Z1_nm": null, "Z1_local_RMSE": 0.021457265494439708, "P2_nm": 752.0, "P2_local_RMSE": 0.183231479658267, "P3_nm": null, "P3_local_RMSE": 0.43215397230149954, "Z2_nm": null, "Z2_local_RMSE": 0.3872591975767232, "P4_nm": 1503.0, "P4_local_RMSE": 0.2639559433621104, "all_peaks_nm": "689.0;752.0;837.0;1377.0;1503.0", "all_minima_nm": "720.0;832.0;953.0;1455.0", "topology_json": "[{\"nm\": 689.0, \"local_prominence\": 0.09714691552009042, \"half_prominence_width_nm\": 10.0}, {\"nm\": 752.0, \"local_prominence\": 0.19702647860607647, \"half_prominence_width_nm\": 11.0}, {\"nm\": 837.0, \"local_prominence\": 0.0006526586250873989, \"half_prominence_width_nm\": 9.0}, {\"nm\": 1377.0, \"local_prominence\": 0.26228140694471314, \"half_prominence_width_nm\": 22.0}, {\"nm\": 1503.0, \"local_prominence\": 0.3541821913804766, \"half_prominence_width_nm\": 18.0}]"}
```

### TEST 52 — right_rectangle

- **Question:** Does right_rectangle explain the paper discrepancy?
- **Method:** Uniform raw grid; Simpson composite 1/3 or diagnostic one-sided endpoints.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** RMSE 0.262523; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=None, P4=1503.0. Full physical reproduction not established.
- **Status:** FAIL
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.2625233608005383, "correlation": 0.24646092789830493, "P1_nm": null, "P1_local_RMSE": 0.1835002845279234, "Z1_nm": null, "Z1_local_RMSE": 0.02152889655349541, "P2_nm": 752.0, "P2_local_RMSE": 0.1827772340281313, "P3_nm": null, "P3_local_RMSE": 0.4316431869405646, "Z2_nm": null, "Z2_local_RMSE": 0.3906844932230301, "P4_nm": 1503.0, "P4_local_RMSE": 0.2634624819972013, "all_peaks_nm": "688.0;752.0;837.0;1376.0;1503.0", "all_minima_nm": "720.0;832.0;953.0;1454.0", "topology_json": "[{\"nm\": 688.0, \"local_prominence\": 0.09896981906567426, \"half_prominence_width_nm\": 10.0}, {\"nm\": 752.0, \"local_prominence\": 0.1971964575107939, \"half_prominence_width_nm\": 11.0}, {\"nm\": 837.0, \"local_prominence\": 0.0006467199931103479, \"half_prominence_width_nm\": 9.0}, {\"nm\": 1376.0, \"local_prominence\": 0.26467024390354166, \"half_prominence_width_nm\": 22.0}, {\"nm\": 1503.0, \"local_prominence\": 0.3551322525342361, \"half_prominence_width_nm\": 18.0}]"}
```

### TEST 53 — correct truncated trapezoid 0.025

- **Question:** Does correct truncated trapezoid 0.025 explain the paper discrepancy?
- **Method:** Slice existing data first, then recompute half endpoint weights; .025 has 76 points.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** RMSE 0.287111; strict feature locations nm: P1=None, Z1=None, P2=751.0, P3=None, Z2=None, P4=1502.0. Full physical reproduction not established.
- **Status:** FAIL
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"old_mask_RMSE": 0.28700679118009426, "old_mask_vs_correct_max_abs_pm_V": 0.5170220884452614}
- **Physics interpretation:** Earlier masked full-grid truncation retained excess half endpoint weight. This corrects truncated diagnostic only; full production integral unchanged.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.2871114563643196, "correlation": 0.48911898699913886, "P1_nm": null, "P1_local_RMSE": 0.1981473578328865, "Z1_nm": null, "Z1_local_RMSE": 0.04737363152530781, "P2_nm": 751.0, "P2_local_RMSE": 0.323040425631855, "P3_nm": null, "P3_local_RMSE": 0.5060380318125388, "Z2_nm": null, "Z2_local_RMSE": 0.07840713425295426, "P4_nm": 1502.0, "P4_local_RMSE": 0.3927006324634226, "all_peaks_nm": "751.0;805.0;822.0;855.0;1502.0;1611.0;1644.0;1690.0", "all_minima_nm": "802.0;813.0;833.0;991.0;1604.0;1627.0;1665.0", "topology_json": "[{\"nm\": 751.0, \"local_prominence\": 0.46097960330730176, \"half_prominence_width_nm\": 10.0}, {\"nm\": 805.0, \"local_prominence\": 0.0002731873376556268, \"half_prominence_width_nm\": 4.0}, {\"nm\": 822.0, \"local_prominence\": 0.0069902148863979705, \"half_prominence_width_nm\": 7.0}, {\"nm\": 855.0, \"local_prominence\": 0.002375096449097173, \"half_prominence_width_nm\": 58.0}, {\"nm\": 1502.0, \"local_prominence\": 0.9392829995950923, \"half_prominence_width_nm\": 19.0}, {\"nm\": 1611.0, \"local_prominence\": 0.0007633336012772898, \"half_prominence_width_nm\": 6.0}, {\"nm\": 1644.0, \"local_prominence\": 0.007298116334610742, \"half_prominence_width_nm\": 14.0}, {\"nm\": 1690.0, \"local_prominence\": 0.002849175511696656, \"half_prominence_width_nm\": 53.0}]"}
```

### TEST 54 — correct truncated trapezoid 0.05

- **Question:** Does correct truncated trapezoid 0.05 explain the paper discrepancy?
- **Method:** Slice existing data first, then recompute half endpoint weights; .025 has 76 points.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** lower RMSE; reproduction not established
- **Status:** FAIL
- **Improved paper agreement?:** YES
- **Quantitative evidence / file:** {"old_mask_RMSE": 0.2621933617555741, "old_mask_vs_correct_max_abs_pm_V": 1.018898983946231}
- **Physics interpretation:** Earlier masked full-grid truncation retained excess half endpoint weight. This corrects truncated diagnostic only; full production integral unchanged.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.2623385033957173, "correlation": 0.47605937955331307, "P1_nm": null, "P1_local_RMSE": 0.1954515646425465, "Z1_nm": null, "Z1_local_RMSE": 0.0411839438643211, "P2_nm": 751.0, "P2_local_RMSE": 0.25705572368112445, "P3_nm": null, "P3_local_RMSE": 0.4904044727203678, "Z2_nm": null, "Z2_local_RMSE": 0.06143848978859898, "P4_nm": 1502.0, "P4_local_RMSE": 0.34313633528318493, "all_peaks_nm": "751.0;846.0;1502.0;1676.0", "all_minima_nm": "831.0;985.0;1663.0", "topology_json": "[{\"nm\": 751.0, \"local_prominence\": 0.47848553833936885, \"half_prominence_width_nm\": 25.0}, {\"nm\": 846.0, \"local_prominence\": 0.0028863685451716026, \"half_prominence_width_nm\": 34.0}, {\"nm\": 1502.0, \"local_prominence\": 0.9538934228800157, \"half_prominence_width_nm\": 50.0}, {\"nm\": 1676.0, \"local_prominence\": 0.0009770233238663786, \"half_prominence_width_nm\": 18.0}]"}
```

### TEST 55 — correct truncated trapezoid 0.075

- **Question:** Does correct truncated trapezoid 0.075 explain the paper discrepancy?
- **Method:** Slice existing data first, then recompute half endpoint weights; .025 has 76 points.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** lower RMSE; reproduction not established
- **Status:** FAIL
- **Improved paper agreement?:** YES
- **Quantitative evidence / file:** {"old_mask_RMSE": 0.25085930371196563, "old_mask_vs_correct_max_abs_pm_V": 1.483493153991214}
- **Physics interpretation:** Earlier masked full-grid truncation retained excess half endpoint weight. This corrects truncated diagnostic only; full production integral unchanged.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.2508504746544676, "correlation": 0.3988618000253167, "P1_nm": null, "P1_local_RMSE": 0.19075059679499734, "Z1_nm": null, "Z1_local_RMSE": 0.030406057975034838, "P2_nm": 751.0, "P2_local_RMSE": 0.20141961721137386, "P3_nm": null, "P3_local_RMSE": 0.4655378260093468, "Z2_nm": null, "Z2_local_RMSE": 0.10587562883259694, "P4_nm": 1503.0, "P4_local_RMSE": 0.3007893669913237, "all_peaks_nm": "716.0;751.0;840.0;1431.0;1503.0", "all_minima_nm": "730.0;831.0;971.0;1462.0", "topology_json": "[{\"nm\": 716.0, \"local_prominence\": 0.04600278369531352, \"half_prominence_width_nm\": 7.0}, {\"nm\": 751.0, \"local_prominence\": 0.16760299716361327, \"half_prominence_width_nm\": 10.0}, {\"nm\": 840.0, \"local_prominence\": 0.001434808019629391, \"half_prominence_width_nm\": 16.0}, {\"nm\": 1431.0, \"local_prominence\": 0.12822300327804104, \"half_prominence_width_nm\": 15.0}, {\"nm\": 1503.0, \"local_prominence\": 0.302708970948952, \"half_prominence_width_nm\": 16.0}]"}
```

### TEST 56 — correct truncated trapezoid 0.1

- **Question:** Does correct truncated trapezoid 0.1 explain the paper discrepancy?
- **Method:** Slice existing data first, then recompute half endpoint weights; .025 has 76 points.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** RMSE 0.262391; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=None, P4=1503.0. Full physical reproduction not established.
- **Status:** FAIL
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"old_mask_RMSE": 0.26239111786932695, "old_mask_vs_correct_max_abs_pm_V": 0.0}
- **Physics interpretation:** Earlier masked full-grid truncation retained excess half endpoint weight. This corrects truncated diagnostic only; full production integral unchanged.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.26239111786932695, "correlation": 0.24755539373540594, "P1_nm": null, "P1_local_RMSE": 0.18355832245681228, "Z1_nm": null, "Z1_local_RMSE": 0.02149182751741102, "P2_nm": 752.0, "P2_local_RMSE": 0.18300269017624166, "P3_nm": null, "P3_local_RMSE": 0.43189844880285366, "Z2_nm": null, "Z2_local_RMSE": 0.3889313933218363, "P4_nm": 1503.0, "P4_local_RMSE": 0.2637088552636287, "all_peaks_nm": "688.0;752.0;837.0;1376.0;1503.0", "all_minima_nm": "720.0;832.0;953.0;1455.0", "topology_json": "[{\"nm\": 688.0, \"local_prominence\": 0.09763940881279826, \"half_prominence_width_nm\": 10.0}, {\"nm\": 752.0, \"local_prominence\": 0.19711267904504853, \"half_prominence_width_nm\": 11.0}, {\"nm\": 837.0, \"local_prominence\": 0.0006496885138127656, \"half_prominence_width_nm\": 9.0}, {\"nm\": 1376.0, \"local_prominence\": 0.2621557638752432, \"half_prominence_width_nm\": 22.0}, {\"nm\": 1503.0, \"local_prominence\": 0.354655473337367, \"half_prominence_width_nm\": 18.0}]"}
```

### TEST 57 — downsample existing grid stride 2

- **Question:** Does downsample existing grid stride 2 explain the paper discrepancy?
- **Method:** No new physics: retained direct samples only; compare all pathway sums.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** lower RMSE; reproduction not established
- **Status:** FAIL
- **Improved paper agreement?:** YES
- **Quantitative evidence / file:** {"max_pathway_abs_delta_pm_V": 3.071327443250508}
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.2623762218058059, "correlation": 0.24758644927705217, "P1_nm": null, "P1_local_RMSE": 0.18355804794063013, "Z1_nm": null, "Z1_local_RMSE": 0.021491980629300675, "P2_nm": 752.0, "P2_local_RMSE": 0.18300160591912995, "P3_nm": null, "P3_local_RMSE": 0.4318974847258274, "Z2_nm": null, "Z2_local_RMSE": 0.3888454007746872, "P4_nm": 1503.0, "P4_local_RMSE": 0.2637126391316971, "all_peaks_nm": "688.0;752.0;837.0;1377.0;1503.0", "all_minima_nm": "720.0;832.0;953.0;1455.0", "topology_json": "[{\"nm\": 688.0, \"local_prominence\": 0.09673788456180549, \"half_prominence_width_nm\": 10.0}, {\"nm\": 752.0, \"local_prominence\": 0.19710968291407155, \"half_prominence_width_nm\": 11.0}, {\"nm\": 837.0, \"local_prominence\": 0.0006496439137712862, \"half_prominence_width_nm\": 9.0}, {\"nm\": 1377.0, \"local_prominence\": 0.2603704454633038, \"half_prominence_width_nm\": 23.0}, {\"nm\": 1503.0, \"local_prominence\": 0.3546269128255932, \"half_prominence_width_nm\": 18.0}]"}
```

### TEST 58 — linear stride 2

- **Question:** Does linear stride 2 explain the paper discrepancy?
- **Method:** Interpolate downsampled energies strictly inside measured endpoints; compare with retained 301-point data.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** RMSE 0.262394; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=None, P4=1503.0. Full physical reproduction not established.
- **Status:** FAIL
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"max_energy_interpolation_error_eV": 1.9034923495198086e-06}
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.2623936049741089, "correlation": 0.24754826254868753, "P1_nm": null, "P1_local_RMSE": 0.18355802100104238, "Z1_nm": null, "Z1_local_RMSE": 0.02149201264514648, "P2_nm": 752.0, "P2_local_RMSE": 0.1830022356384544, "P3_nm": null, "P3_local_RMSE": 0.43189701178587275, "Z2_nm": null, "Z2_local_RMSE": 0.38894053042461146, "P4_nm": 1503.0, "P4_local_RMSE": 0.2637155628451194, "all_peaks_nm": "688.0;752.0;837.0;1376.0;1503.0", "all_minima_nm": "720.0;832.0;953.0;1455.0", "topology_json": "[{\"nm\": 688.0, \"local_prominence\": 0.09763955360740906, \"half_prominence_width_nm\": 10.0}, {\"nm\": 752.0, \"local_prominence\": 0.19710198753176256, \"half_prominence_width_nm\": 11.0}, {\"nm\": 837.0, \"local_prominence\": 0.0006496614576325943, \"half_prominence_width_nm\": 9.0}, {\"nm\": 1376.0, \"local_prominence\": 0.2621535931938136, \"half_prominence_width_nm\": 22.0}, {\"nm\": 1503.0, \"local_prominence\": 0.35463659671667846, \"half_prominence_width_nm\": 18.0}]"}
```

### TEST 59 — shape_preserving_cubic stride 2

- **Question:** Does shape_preserving_cubic stride 2 explain the paper discrepancy?
- **Method:** Interpolate downsampled energies strictly inside measured endpoints; compare with retained 301-point data.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** lower RMSE; reproduction not established
- **Status:** FAIL
- **Improved paper agreement?:** YES
- **Quantitative evidence / file:** {"max_energy_interpolation_error_eV": 1.4088944801926573e-06}
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.2623910877005231, "correlation": 0.24755546693432004, "P1_nm": null, "P1_local_RMSE": 0.18355832182133672, "Z1_nm": null, "Z1_local_RMSE": 0.02149182786871103, "P2_nm": 752.0, "P2_local_RMSE": 0.18300268165078198, "P3_nm": null, "P3_local_RMSE": 0.4318984460899465, "Z2_nm": null, "Z2_local_RMSE": 0.38893122517626016, "P4_nm": 1503.0, "P4_local_RMSE": 0.26370885493885055, "all_peaks_nm": "688.0;752.0;837.0;1376.0;1503.0", "all_minima_nm": "720.0;832.0;953.0;1455.0", "topology_json": "[{\"nm\": 688.0, \"local_prominence\": 0.09763732244710743, \"half_prominence_width_nm\": 10.0}, {\"nm\": 752.0, \"local_prominence\": 0.19711267981900354, \"half_prominence_width_nm\": 11.0}, {\"nm\": 837.0, \"local_prominence\": 0.0006496882320810998, \"half_prominence_width_nm\": 9.0}, {\"nm\": 1376.0, \"local_prominence\": 0.2621515524429977, \"half_prominence_width_nm\": 22.0}, {\"nm\": 1503.0, \"local_prominence\": 0.35465544584769026, \"half_prominence_width_nm\": 18.0}]"}
```

### TEST 60 — downsample existing grid stride 3

- **Question:** Does downsample existing grid stride 3 explain the paper discrepancy?
- **Method:** No new physics: retained direct samples only; compare all pathway sums.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** lower RMSE; reproduction not established
- **Status:** FAIL
- **Improved paper agreement?:** YES
- **Quantitative evidence / file:** {"max_pathway_abs_delta_pm_V": 8.452649874958762}
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.2623516211977273, "correlation": 0.2476379645852247, "P1_nm": null, "P1_local_RMSE": 0.1835575681177198, "Z1_nm": null, "Z1_local_RMSE": 0.021492249511275024, "P2_nm": 752.0, "P2_local_RMSE": 0.18299953951403605, "P3_nm": null, "P3_local_RMSE": 0.43189576181580885, "Z2_nm": null, "Z2_local_RMSE": 0.3887033092662823, "P4_nm": 1503.0, "P4_local_RMSE": 0.26371902617261955, "all_peaks_nm": "688.0;752.0;837.0;1377.0;1503.0", "all_minima_nm": "720.0;832.0;953.0;1454.0", "topology_json": "[{\"nm\": 688.0, \"local_prominence\": 0.09524010582080378, \"half_prominence_width_nm\": 11.0}, {\"nm\": 752.0, \"local_prominence\": 0.1971050322881553, \"half_prominence_width_nm\": 11.0}, {\"nm\": 837.0, \"local_prominence\": 0.00064957079509953, \"half_prominence_width_nm\": 9.0}, {\"nm\": 1377.0, \"local_prominence\": 0.25837378604523753, \"half_prominence_width_nm\": 23.0}, {\"nm\": 1503.0, \"local_prominence\": 0.3545929211620029, \"half_prominence_width_nm\": 18.0}]"}
```

### TEST 61 — linear stride 3

- **Question:** Does linear stride 3 explain the paper discrepancy?
- **Method:** Interpolate downsampled energies strictly inside measured endpoints; compare with retained 301-point data.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** RMSE 0.262398; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=None, P4=1503.0. Full physical reproduction not established.
- **Status:** FAIL
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"max_energy_interpolation_error_eV": 3.8084292834916766e-06}
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.2623977509187062, "correlation": 0.2475363771761787, "P1_nm": null, "P1_local_RMSE": 0.18355751848830845, "Z1_nm": null, "Z1_local_RMSE": 0.021492321353558788, "P2_nm": 752.0, "P2_local_RMSE": 0.18300147767931652, "P3_nm": null, "P3_local_RMSE": 0.43189461631898435, "Z2_nm": null, "Z2_local_RMSE": 0.3889557615646704, "P4_nm": 1503.0, "P4_local_RMSE": 0.2637267430852839, "all_peaks_nm": "688.0;752.0;837.0;1376.0;1503.0", "all_minima_nm": "720.0;832.0;953.0;1455.0", "topology_json": "[{\"nm\": 688.0, \"local_prominence\": 0.0976396638835913, \"half_prominence_width_nm\": 10.0}, {\"nm\": 752.0, \"local_prominence\": 0.19708416662081563, \"half_prominence_width_nm\": 11.0}, {\"nm\": 837.0, \"local_prominence\": 0.0006496161354241359, \"half_prominence_width_nm\": 9.0}, {\"nm\": 1376.0, \"local_prominence\": 0.26214971262137443, \"half_prominence_width_nm\": 22.0}, {\"nm\": 1503.0, \"local_prominence\": 0.35460513814292316, \"half_prominence_width_nm\": 18.0}]"}
```

### TEST 62 — shape_preserving_cubic stride 3

- **Question:** Does shape_preserving_cubic stride 3 explain the paper discrepancy?
- **Method:** Interpolate downsampled energies strictly inside measured endpoints; compare with retained 301-point data.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** lower RMSE; reproduction not established
- **Status:** FAIL
- **Improved paper agreement?:** YES
- **Quantitative evidence / file:** {"max_energy_interpolation_error_eV": 3.14797194977956e-06}
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.26239099914775416, "correlation": 0.24755568252766633, "P1_nm": null, "P1_local_RMSE": 0.1835583198389187, "Z1_nm": null, "Z1_local_RMSE": 0.021491828971198487, "P2_nm": 752.0, "P2_local_RMSE": 0.18300265124583176, "P3_nm": null, "P3_local_RMSE": 0.4318984375385869, "Z2_nm": null, "Z2_local_RMSE": 0.3889307310879297, "P4_nm": 1503.0, "P4_local_RMSE": 0.2637088551397414, "all_peaks_nm": "688.0;752.0;837.0;1376.0;1503.0", "all_minima_nm": "720.0;832.0;953.0;1455.0", "topology_json": "[{\"nm\": 688.0, \"local_prominence\": 0.09763116498346275, \"half_prominence_width_nm\": 10.0}, {\"nm\": 752.0, \"local_prominence\": 0.1971126846669352, \"half_prominence_width_nm\": 11.0}, {\"nm\": 837.0, \"local_prominence\": 0.0006496880672192534, \"half_prominence_width_nm\": 9.0}, {\"nm\": 1376.0, \"local_prominence\": 0.26213910617528935, \"half_prominence_width_nm\": 22.0}, {\"nm\": 1503.0, \"local_prominence\": 0.35465541381471943, \"half_prominence_width_nm\": 18.0}]"}
```

### TEST 63 — downsample existing grid stride 5

- **Question:** Does downsample existing grid stride 5 explain the paper discrepancy?
- **Method:** No new physics: retained direct samples only; compare all pathway sums.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** lower RMSE; reproduction not established
- **Status:** FAIL
- **Improved paper agreement?:** YES
- **Quantitative evidence / file:** {"max_pathway_abs_delta_pm_V": 28.63600407126851}
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.2622740432052423, "correlation": 0.24780006999078125, "P1_nm": null, "P1_local_RMSE": 0.18355607974238003, "Z1_nm": null, "Z1_local_RMSE": 0.02149308430635302, "P2_nm": 752.0, "P2_local_RMSE": 0.18299201053131164, "P3_nm": null, "P3_local_RMSE": 0.43189049375136884, "Z2_nm": null, "Z2_local_RMSE": 0.38826317340929034, "P4_nm": 1503.0, "P4_local_RMSE": 0.2637392706337251, "all_peaks_nm": "689.0;719.0;752.0;837.0;1377.0;1438.0;1441.0;1444.0;1448.0;1451.0;1454.0;1503.0", "all_minima_nm": "718.0;720.0;832.0;953.0;1437.0;1440.0;1443.0;1446.0;1450.0;1453.0;1455.0", "topology_json": "[{\"nm\": 689.0, \"local_prominence\": 0.09399966377917729, \"half_prominence_width_nm\": 11.0}, {\"nm\": 719.0, \"local_prominence\": 0.0002175263016619411, \"half_prominence_width_nm\": 2.0}, {\"nm\": 752.0, \"local_prominence\": 0.19721838661825414, \"half_prominence_width_nm\": 11.0}, {\"nm\": 837.0, \"local_prominence\": 0.000649337621535559, \"half_prominence_width_nm\": 9.0}, {\"nm\": 1377.0, \"local_prominence\": 0.2492570024162296, \"half_prominence_width_nm\": 23.0}, {\"nm\": 1438.0, \"local_prominence\": 1.7648289653671156e-05, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1441.0, \"local_prominence\": 0.0001560854910930276, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1444.0, \"local_prominence\": 0.00012993101762226456, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1448.0, \"local_prominence\": 0.00019568956761739642, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1451.0, \"local_prominence\": 0.00014092157743439415, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1454.0, \"local_prominence\": 5.400278022726912e-05, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1503.0, \"local_prominence\": 0.35442515290376997, \"half_prominence_width_nm\": 18.0}]"}
```

### TEST 64 — linear stride 5

- **Question:** Does linear stride 5 explain the paper discrepancy?
- **Method:** Interpolate downsampled energies strictly inside measured endpoints; compare with retained 301-point data.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** RMSE 0.262411; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=None, P4=1503.0. Full physical reproduction not established.
- **Status:** FAIL
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"max_energy_interpolation_error_eV": 1.1417763799759229e-05}
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.26241100485219865, "correlation": 0.24749834296818998, "P1_nm": null, "P1_local_RMSE": 0.18355591375833558, "Z1_nm": null, "Z1_local_RMSE": 0.021493308156565544, "P2_nm": 752.0, "P2_local_RMSE": 0.1829990687674462, "P3_nm": null, "P3_local_RMSE": 0.4318869681481332, "Z2_nm": null, "Z2_local_RMSE": 0.3890044113925778, "P4_nm": 1503.0, "P4_local_RMSE": 0.2637624993010936, "all_peaks_nm": "688.0;752.0;837.0;1376.0;1503.0", "all_minima_nm": "720.0;832.0;953.0;1455.0", "topology_json": "[{\"nm\": 688.0, \"local_prominence\": 0.09763756778321209, \"half_prominence_width_nm\": 10.0}, {\"nm\": 752.0, \"local_prominence\": 0.19702736349457994, \"half_prominence_width_nm\": 11.0}, {\"nm\": 837.0, \"local_prominence\": 0.0006494688461765596, \"half_prominence_width_nm\": 9.0}, {\"nm\": 1376.0, \"local_prominence\": 0.26213107113945155, \"half_prominence_width_nm\": 22.0}, {\"nm\": 1503.0, \"local_prominence\": 0.3545040213452566, \"half_prominence_width_nm\": 18.0}]"}
```

### TEST 65 — shape_preserving_cubic stride 5

- **Question:** Does shape_preserving_cubic stride 5 explain the paper discrepancy?
- **Method:** Interpolate downsampled energies strictly inside measured endpoints; compare with retained 301-point data.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** lower RMSE; reproduction not established
- **Status:** FAIL
- **Improved paper agreement?:** YES
- **Quantitative evidence / file:** {"max_energy_interpolation_error_eV": 9.114764504047912e-06}
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.2623905483561866, "correlation": 0.24755678063112835, "P1_nm": null, "P1_local_RMSE": 0.18355830864173253, "Z1_nm": null, "Z1_local_RMSE": 0.021491835253754216, "P2_nm": 752.0, "P2_local_RMSE": 0.1830024294862115, "P3_nm": null, "P3_local_RMSE": 0.431898388499668, "Z2_nm": null, "Z2_local_RMSE": 0.38892822044117, "P4_nm": 1503.0, "P4_local_RMSE": 0.26370885266662614, "all_peaks_nm": "688.0;752.0;837.0;1376.0;1503.0", "all_minima_nm": "720.0;832.0;953.0;1455.0", "topology_json": "[{\"nm\": 688.0, \"local_prominence\": 0.0976032887665767, \"half_prominence_width_nm\": 10.0}, {\"nm\": 752.0, \"local_prominence\": 0.19711275670849543, \"half_prominence_width_nm\": 11.0}, {\"nm\": 837.0, \"local_prominence\": 0.0006496949791357509, \"half_prominence_width_nm\": 9.0}, {\"nm\": 1376.0, \"local_prominence\": 0.2620825083911559, \"half_prominence_width_nm\": 22.0}, {\"nm\": 1503.0, \"local_prominence\": 0.35465563899718566, \"half_prominence_width_nm\": 18.0}]"}
```

### TEST 66 — independent raw grid_y_n101_k0100

- **Question:** Does independent raw grid_y_n101_k0100 explain the paper discrepancy?
- **Method:** Actual separately run Professional dispersion; static adjacent Kramers pair means, same per-state k0 anchoring as production; frozen scalar matrices.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** lower RMSE; reproduction not established
- **Status:** FAIL
- **Improved paper agreement?:** YES
- **Quantitative evidence / file:** {"source": "C:\\code\\nonlinear_photonics\\demo_results\\demo23\\raw\\grid_y_n101_k0100\\grid_y_n101_k0100\\bias_00000\\QuantumDispersions\\acqw\\kp8\\dispersion_Gamma_to_y.dat", "Nk": 101, "kmax_inverse_nm": 0.555714439232, "max_pathway_abs_delta_pm_V": 8.452649878122422}
- **Physics interpretation:** Existing raw output reused, no solver. Comparing cutoff changes tests truncation sensitivity, not convergence with larger physical BZ. Raw finite-k identity uses fixed paired band labels because spinors are absent.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.2623516211977149, "correlation": 0.24763796458524936, "P1_nm": null, "P1_local_RMSE": 0.18355756811772067, "Z1_nm": null, "Z1_local_RMSE": 0.02149224951127451, "P2_nm": 752.0, "P2_local_RMSE": 0.1829995395140669, "P3_nm": null, "P3_local_RMSE": 0.4318957618158139, "Z2_nm": null, "Z2_local_RMSE": 0.38870330926619706, "P4_nm": 1503.0, "P4_local_RMSE": 0.2637190261728122, "all_peaks_nm": "688.0;752.0;837.0;1377.0;1503.0", "all_minima_nm": "720.0;832.0;953.0;1454.0", "topology_json": "[{\"nm\": 688.0, \"local_prominence\": 0.09524010581889669, \"half_prominence_width_nm\": 11.0}, {\"nm\": 752.0, \"local_prominence\": 0.19710503228793796, \"half_prominence_width_nm\": 11.0}, {\"nm\": 837.0, \"local_prominence\": 0.0006495707951000712, \"half_prominence_width_nm\": 9.0}, {\"nm\": 1377.0, \"local_prominence\": 0.2583737860385623, \"half_prominence_width_nm\": 23.0}, {\"nm\": 1503.0, \"local_prominence\": 0.35459292115864416, \"half_prominence_width_nm\": 18.0}]"}
```

### TEST 67 — independent raw grid_y_n201_k0100

- **Question:** Does independent raw grid_y_n201_k0100 explain the paper discrepancy?
- **Method:** Actual separately run Professional dispersion; static adjacent Kramers pair means, same per-state k0 anchoring as production; frozen scalar matrices.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** lower RMSE; reproduction not established
- **Status:** FAIL
- **Improved paper agreement?:** YES
- **Quantitative evidence / file:** {"source": "C:\\code\\nonlinear_photonics\\demo_results\\demo23\\raw\\grid_y_n201_k0100\\grid_y_n201_k0100\\bias_00000\\QuantumDispersions\\acqw\\kp8\\dispersion_Gamma_to_y.dat", "Nk": 201, "kmax_inverse_nm": 0.555714439232, "max_pathway_abs_delta_pm_V": 1.2670362033420677}
- **Physics interpretation:** Existing raw output reused, no solver. Comparing cutoff changes tests truncation sensitivity, not convergence with larger physical BZ. Raw finite-k identity uses fixed paired band labels because spinors are absent.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.26238490477872467, "correlation": 0.24756834598574093, "P1_nm": null, "P1_local_RMSE": 0.1835582080922366, "Z1_nm": null, "Z1_local_RMSE": 0.021491891286971425, "P2_nm": 752.0, "P2_local_RMSE": 0.1830022340867298, "P3_nm": null, "P3_local_RMSE": 0.43189804719257124, "Z2_nm": null, "Z2_local_RMSE": 0.38889552908585273, "P4_nm": 1503.0, "P4_local_RMSE": 0.2637104323061626, "all_peaks_nm": "688.0;752.0;837.0;1376.0;1503.0", "all_minima_nm": "720.0;832.0;953.0;1455.0", "topology_json": "[{\"nm\": 688.0, \"local_prominence\": 0.09726453299602372, \"half_prominence_width_nm\": 10.0}, {\"nm\": 752.0, \"local_prominence\": 0.19711143094740308, \"half_prominence_width_nm\": 11.0}, {\"nm\": 837.0, \"local_prominence\": 0.0006496699155850716, \"half_prominence_width_nm\": 9.0}, {\"nm\": 1376.0, \"local_prominence\": 0.2613998340768302, \"half_prominence_width_nm\": 22.0}, {\"nm\": 1503.0, \"local_prominence\": 0.3546437195046861, \"half_prominence_width_nm\": 18.0}]"}
```

### TEST 68 — independent raw production_y_n301_k0100

- **Question:** Does independent raw production_y_n301_k0100 explain the paper discrepancy?
- **Method:** Actual separately run Professional dispersion; static adjacent Kramers pair means, same per-state k0 anchoring as production; frozen scalar matrices.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** RMSE 0.262391; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=None, P4=1503.0. Full physical reproduction not established.
- **Status:** FAIL
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"source": "C:\\code\\nonlinear_photonics\\demo_results\\demo23\\raw\\production_y_n301_k0100\\production_y_n301_k0100\\bias_00000\\QuantumDispersions\\acqw\\kp8\\dispersion_Gamma_to_y.dat", "Nk": 301, "kmax_inverse_nm": 0.555714439232, "max_pathway_abs_delta_pm_V": 5.158658153835089e-09}
- **Physics interpretation:** Existing raw output reused, no solver. Comparing cutoff changes tests truncation sensitivity, not convergence with larger physical BZ. Raw finite-k identity uses fixed paired band labels because spinors are absent.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.26239111786930097, "correlation": 0.2475553937354378, "P1_nm": null, "P1_local_RMSE": 0.18355832245681467, "Z1_nm": null, "Z1_local_RMSE": 0.021491827517409565, "P2_nm": 752.0, "P2_local_RMSE": 0.18300269017625906, "P3_nm": null, "P3_local_RMSE": 0.43189844880286665, "Z2_nm": null, "Z2_local_RMSE": 0.38893139332166415, "P4_nm": 1503.0, "P4_local_RMSE": 0.2637088552636332, "all_peaks_nm": "688.0;752.0;837.0;1376.0;1503.0", "all_minima_nm": "720.0;832.0;953.0;1455.0", "topology_json": "[{\"nm\": 688.0, \"local_prominence\": 0.09763940881126026, \"half_prominence_width_nm\": 10.0}, {\"nm\": 752.0, \"local_prominence\": 0.19711267904504332, \"half_prominence_width_nm\": 11.0}, {\"nm\": 837.0, \"local_prominence\": 0.0006496885138147362, \"half_prominence_width_nm\": 9.0}, {\"nm\": 1376.0, \"local_prominence\": 0.26215576387245587, \"half_prominence_width_nm\": 22.0}, {\"nm\": 1503.0, \"local_prominence\": 0.354655473337671, \"half_prominence_width_nm\": 18.0}]"}
```

### TEST 69 — independent raw kmax_y_n301_k0050

- **Question:** Does independent raw kmax_y_n301_k0050 explain the paper discrepancy?
- **Method:** Actual separately run Professional dispersion; static adjacent Kramers pair means, same per-state k0 anchoring as production; frozen scalar matrices.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** lower RMSE; reproduction not established
- **Status:** FAIL
- **Improved paper agreement?:** YES
- **Quantitative evidence / file:** {"source": "C:\\code\\nonlinear_photonics\\demo_results\\demo23\\raw\\kmax_y_n301_k0050\\kmax_y_n301_k0050\\bias_00000\\QuantumDispersions\\acqw\\kp8\\dispersion_Gamma_to_y.dat", "Nk": 301, "kmax_inverse_nm": 0.277857219616, "max_pathway_abs_delta_pm_V": 933.4514135252898}
- **Physics interpretation:** Existing raw output reused, no solver. Comparing cutoff changes tests truncation sensitivity, not convergence with larger physical BZ. Raw finite-k identity uses fixed paired band labels because spinors are absent.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.26233970445675503, "correlation": 0.4760553534872637, "P1_nm": null, "P1_local_RMSE": 0.19545160840608441, "Z1_nm": null, "Z1_local_RMSE": 0.04118405559556983, "P2_nm": 751.0, "P2_local_RMSE": 0.25705644532924343, "P3_nm": null, "P3_local_RMSE": 0.4904046908986937, "Z2_nm": null, "Z2_local_RMSE": 0.061438565660618366, "P4_nm": 1502.0, "P4_local_RMSE": 0.34314315818500396, "all_peaks_nm": "751.0;846.0;1502.0;1676.0", "all_minima_nm": "831.0;985.0;1663.0", "topology_json": "[{\"nm\": 751.0, \"local_prominence\": 0.47848606077050737, \"half_prominence_width_nm\": 25.0}, {\"nm\": 846.0, \"local_prominence\": 0.002886308390401233, \"half_prominence_width_nm\": 34.0}, {\"nm\": 1502.0, \"local_prominence\": 0.9538937073027988, \"half_prominence_width_nm\": 50.0}, {\"nm\": 1676.0, \"local_prominence\": 0.0009770021633842552, \"half_prominence_width_nm\": 18.0}]"}
```

### TEST 70 — independent raw kmax_y_n301_k0075

- **Question:** Does independent raw kmax_y_n301_k0075 explain the paper discrepancy?
- **Method:** Actual separately run Professional dispersion; static adjacent Kramers pair means, same per-state k0 anchoring as production; frozen scalar matrices.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** lower RMSE; reproduction not established
- **Status:** FAIL
- **Improved paper agreement?:** YES
- **Quantitative evidence / file:** {"source": "C:\\code\\nonlinear_photonics\\demo_results\\demo23\\raw\\kmax_y_n301_k0075\\kmax_y_n301_k0075\\bias_00000\\QuantumDispersions\\acqw\\kp8\\dispersion_Gamma_to_y.dat", "Nk": 301, "kmax_inverse_nm": 0.416785829424, "max_pathway_abs_delta_pm_V": 807.4126670276478}
- **Physics interpretation:** Existing raw output reused, no solver. Comparing cutoff changes tests truncation sensitivity, not convergence with larger physical BZ. Raw finite-k identity uses fixed paired band labels because spinors are absent.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.25085179224601123, "correlation": 0.3988585286570038, "P1_nm": null, "P1_local_RMSE": 0.19075063024352543, "Z1_nm": null, "Z1_local_RMSE": 0.030406148081624843, "P2_nm": 751.0, "P2_local_RMSE": 0.20142066579105347, "P3_nm": null, "P3_local_RMSE": 0.46553796818810345, "Z2_nm": null, "Z2_local_RMSE": 0.10587431683289479, "P4_nm": 1503.0, "P4_local_RMSE": 0.30078842802807243, "all_peaks_nm": "716.0;751.0;840.0;1431.0;1503.0", "all_minima_nm": "730.0;831.0;971.0;1462.0", "topology_json": "[{\"nm\": 716.0, \"local_prominence\": 0.046046493939078226, \"half_prominence_width_nm\": 7.0}, {\"nm\": 751.0, \"local_prominence\": 0.16760293741026439, \"half_prominence_width_nm\": 10.0}, {\"nm\": 840.0, \"local_prominence\": 0.0014347820563505864, \"half_prominence_width_nm\": 16.0}, {\"nm\": 1431.0, \"local_prominence\": 0.12835520057260308, \"half_prominence_width_nm\": 15.0}, {\"nm\": 1503.0, \"local_prominence\": 0.3027103885273047, \"half_prominence_width_nm\": 16.0}]"}
```

### TEST 71 — independent raw kmax_y_n301_k0125

- **Question:** Does independent raw kmax_y_n301_k0125 explain the paper discrepancy?
- **Method:** Actual separately run Professional dispersion; static adjacent Kramers pair means, same per-state k0 anchoring as production; frozen scalar matrices.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** RMSE 0.279161; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=None, P4=1503.0. Full physical reproduction not established.
- **Status:** FAIL
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"source": "C:\\code\\nonlinear_photonics\\demo_results\\demo23\\raw\\kmax_y_n301_k0125\\kmax_y_n301_k0125\\bias_00000\\QuantumDispersions\\acqw\\kp8\\dispersion_Gamma_to_y.dat", "Nk": 301, "kmax_inverse_nm": 0.69464304904, "max_pathway_abs_delta_pm_V": 842.9587697713271}
- **Physics interpretation:** Existing raw output reused, no solver. Comparing cutoff changes tests truncation sensitivity, not convergence with larger physical BZ. Raw finite-k identity uses fixed paired band labels because spinors are absent.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.27916061074761905, "correlation": 0.11966345291278796, "P1_nm": null, "P1_local_RMSE": 0.17325783629336516, "Z1_nm": null, "Z1_local_RMSE": 0.06496018411644074, "P2_nm": 752.0, "P2_local_RMSE": 0.15708736932089995, "P3_nm": null, "P3_local_RMSE": 0.3899072364366275, "Z2_nm": null, "Z2_local_RMSE": 0.570502958091422, "P4_nm": 1503.0, "P4_local_RMSE": 0.23762212011121558, "all_peaks_nm": "659.0;752.0;836.0;1318.0;1503.0", "all_minima_nm": "712.0;832.0;933.0;1437.0", "topology_json": "[{\"nm\": 659.0, \"local_prominence\": 0.13577531238572077, \"half_prominence_width_nm\": 13.0}, {\"nm\": 752.0, \"local_prominence\": 0.22567454079277605, \"half_prominence_width_nm\": 11.0}, {\"nm\": 836.0, \"local_prominence\": 0.0003337916356009468, \"half_prominence_width_nm\": 6.0}, {\"nm\": 1318.0, \"local_prominence\": 0.3668722527759296, \"half_prominence_width_nm\": 28.0}, {\"nm\": 1503.0, \"local_prominence\": 0.3939882706482807, \"half_prominence_width_nm\": 20.0}]"}
```

### TEST 72 — independent raw isotropy_yz45_n301_k0100

- **Question:** Does independent raw isotropy_yz45_n301_k0100 explain the paper discrepancy?
- **Method:** Actual separately run Professional dispersion; static adjacent Kramers pair means, same per-state k0 anchoring as production; frozen scalar matrices.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** RMSE 0.268200; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=None, P4=1503.0. Full physical reproduction not established.
- **Status:** FAIL
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"source": "C:\\code\\nonlinear_photonics\\demo_results\\demo23\\raw\\isotropy_yz45_n301_k0100\\isotropy_yz45_n301_k0100\\bias_00000\\QuantumDispersions\\acqw\\kp8\\dispersion_Gamma_to_yz45.dat", "Nk": 301, "kmax_inverse_nm": 0.55571443923168, "max_pathway_abs_delta_pm_V": 450.6058686740718}
- **Physics interpretation:** Existing raw output reused, no solver. Comparing cutoff changes tests truncation sensitivity, not convergence with larger physical BZ. Raw finite-k identity uses fixed paired band labels because spinors are absent.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.2681998238337699, "correlation": 0.23593369800491887, "P1_nm": null, "P1_local_RMSE": 0.18322053246215939, "Z1_nm": null, "Z1_local_RMSE": 0.02171839401007456, "P2_nm": 752.0, "P2_local_RMSE": 0.1850188288926625, "P3_nm": null, "P3_local_RMSE": 0.4301596925057339, "Z2_nm": null, "Z2_local_RMSE": 0.40710837563859587, "P4_nm": 1503.0, "P4_local_RMSE": 0.26496302376263786, "all_peaks_nm": "690.0;727.0;752.0;838.0;1379.0;1503.0", "all_minima_nm": "725.0;729.0;831.0;953.0;1461.0", "topology_json": "[{\"nm\": 690.0, \"local_prominence\": 0.10998191279194675, \"half_prominence_width_nm\": 10.0}, {\"nm\": 727.0, \"local_prominence\": 5.359578080305072e-05, \"half_prominence_width_nm\": 3.0}, {\"nm\": 752.0, \"local_prominence\": 0.17950100343794195, \"half_prominence_width_nm\": 9.0}, {\"nm\": 838.0, \"local_prominence\": 0.0008380083017560658, \"half_prominence_width_nm\": 11.0}, {\"nm\": 1379.0, \"local_prominence\": 0.30048369798379004, \"half_prominence_width_nm\": 24.0}, {\"nm\": 1503.0, \"local_prominence\": 0.3256458823557341, \"half_prominence_width_nm\": 17.0}]"}
```

### TEST 73 — existing candidate higher-state raw energy ranges

- **Question:** Does existing candidate higher-state raw energy ranges explain the paper discrepancy?
- **Method:** All 4 CB-candidate pairs versus 3 hole pairs over existing .125 pi/a raw grid; raw energy reference kept separate.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** see quantitative evidence
- **Status:** INCONCLUSIVE
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"table": "numerical_higher_state_ranges.csv"}
- **Physics interpretation:** Energy-only screening; no higher-state chi without valid matrix elements; k0 mixed character cannot certify finite-k identity or boundness.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** YES
- **Requires new Pro data?:** NO

### TEST 74 — projected kp8 branch A

- **Question:** Does projected kp8 branch A explain the paper discrepancy?
- **Method:** Normalize each dominant component separately; rebuild overlap and z; DIAGNOSTIC cross-method mixing with aligned dispersion.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** lower RMSE; reproduction not established
- **Status:** INCONCLUSIVE
- **Improved paper agreement?:** YES
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Not a full multiband optical matrix or equivalent scalar calculation. Large changes prove sensitivity, not a production matrix bug.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** YES
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.24418578432736024, "correlation": 0.4691073069112756, "P1_nm": null, "P1_local_RMSE": 0.1834240850815403, "Z1_nm": null, "Z1_local_RMSE": 0.02375176293181864, "P2_nm": 742.0, "P2_local_RMSE": 0.11066649994006701, "P3_nm": null, "P3_local_RMSE": 0.4001366582259283, "Z2_nm": null, "Z2_local_RMSE": 0.1657532126142505, "P4_nm": 1483.0, "P4_local_RMSE": 0.37399564003463465, "all_peaks_nm": "728.0;742.0;810.0;828.0;1456.0;1483.0;1619.0;1656.0", "all_minima_nm": "732.0;771.0;824.0;1036.0;1465.0;1555.0;1651.0", "topology_json": "[{\"nm\": 728.0, \"local_prominence\": 0.007511445140419459, \"half_prominence_width_nm\": 3.0}, {\"nm\": 742.0, \"local_prominence\": 0.05411036461553648, \"half_prominence_width_nm\": 11.0}, {\"nm\": 810.0, \"local_prominence\": 0.12075499689485708, \"half_prominence_width_nm\": 13.0}, {\"nm\": 828.0, \"local_prominence\": 0.004947441298585764, \"half_prominence_width_nm\": 4.0}, {\"nm\": 1456.0, \"local_prominence\": 0.026234888982209936, \"half_prominence_width_nm\": 7.0}, {\"nm\": 1483.0, \"local_prominence\": 0.1597134803660224, \"half_prominence_width_nm\": 24.0}, {\"nm\": 1619.0, \"local_prominence\": 0.19346597742276583, \"half_prominence_width_nm\": 22.0}, {\"nm\": 1656.0, \"local_prominence\": 0.0021996781964457313, \"half_prominence_width_nm\": 5.0}]"}
```

### TEST 75 — projected kp8 branch B

- **Question:** Does projected kp8 branch B explain the paper discrepancy?
- **Method:** Normalize each dominant component separately; rebuild overlap and z; DIAGNOSTIC cross-method mixing with aligned dispersion.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** lower RMSE; reproduction not established
- **Status:** INCONCLUSIVE
- **Improved paper agreement?:** YES
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Not a full multiband optical matrix or equivalent scalar calculation. Large changes prove sensitivity, not a production matrix bug.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** YES
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.24418578432735974, "correlation": 0.46910730691127495, "P1_nm": null, "P1_local_RMSE": 0.18342408508154034, "Z1_nm": null, "Z1_local_RMSE": 0.023751762931818694, "P2_nm": 742.0, "P2_local_RMSE": 0.11066649994006628, "P3_nm": null, "P3_local_RMSE": 0.4001366582259289, "Z2_nm": null, "Z2_local_RMSE": 0.16575321261424805, "P4_nm": 1483.0, "P4_local_RMSE": 0.37399564003463237, "all_peaks_nm": "728.0;742.0;810.0;828.0;1456.0;1483.0;1619.0;1656.0", "all_minima_nm": "732.0;771.0;824.0;1036.0;1465.0;1555.0;1651.0", "topology_json": "[{\"nm\": 728.0, \"local_prominence\": 0.007511445140421125, \"half_prominence_width_nm\": 3.0}, {\"nm\": 742.0, \"local_prominence\": 0.05411036461553337, \"half_prominence_width_nm\": 11.0}, {\"nm\": 810.0, \"local_prominence\": 0.12075499689485114, \"half_prominence_width_nm\": 13.0}, {\"nm\": 828.0, \"local_prominence\": 0.004947441298587041, \"half_prominence_width_nm\": 4.0}, {\"nm\": 1456.0, \"local_prominence\": 0.026234888982204718, \"half_prominence_width_nm\": 7.0}, {\"nm\": 1483.0, \"local_prominence\": 0.15971348036602595, \"half_prominence_width_nm\": 24.0}, {\"nm\": 1619.0, \"local_prominence\": 0.19346597742276905, \"half_prominence_width_nm\": 22.0}, {\"nm\": 1656.0, \"local_prominence\": 0.002199678196445509, \"half_prominence_width_nm\": 5.0}]"}
```

### TEST 76 — projected branch matrix mean

- **Question:** Does projected branch matrix mean explain the paper discrepancy?
- **Method:** Mean phase-aligned component matrices BEFORE evaluation; diagnostic only, no justified spinor averaging claim.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** lower RMSE; reproduction not established
- **Status:** INCONCLUSIVE
- **Improved paper agreement?:** YES
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** YES
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.24418578432736007, "correlation": 0.46910730691127517, "P1_nm": null, "P1_local_RMSE": 0.18342408508154032, "Z1_nm": null, "Z1_local_RMSE": 0.02375176293181866, "P2_nm": 742.0, "P2_local_RMSE": 0.1106664999400666, "P3_nm": null, "P3_local_RMSE": 0.40013665822592853, "Z2_nm": null, "Z2_local_RMSE": 0.16575321261424938, "P4_nm": 1483.0, "P4_local_RMSE": 0.3739956400346338, "all_peaks_nm": "728.0;742.0;810.0;828.0;1456.0;1483.0;1619.0;1656.0", "all_minima_nm": "732.0;771.0;824.0;1036.0;1465.0;1555.0;1651.0", "topology_json": "[{\"nm\": 728.0, \"local_prominence\": 0.007511445140420403, \"half_prominence_width_nm\": 3.0}, {\"nm\": 742.0, \"local_prominence\": 0.05411036461553487, \"half_prominence_width_nm\": 11.0}, {\"nm\": 810.0, \"local_prominence\": 0.12075499689485425, \"half_prominence_width_nm\": 13.0}, {\"nm\": 828.0, \"local_prominence\": 0.004947441298586097, \"half_prominence_width_nm\": 4.0}, {\"nm\": 1456.0, \"local_prominence\": 0.026234888982207494, \"half_prominence_width_nm\": 7.0}, {\"nm\": 1483.0, \"local_prominence\": 0.1597134803660244, \"half_prominence_width_nm\": 24.0}, {\"nm\": 1619.0, \"local_prominence\": 0.1934659774227665, \"half_prominence_width_nm\": 22.0}, {\"nm\": 1656.0, \"local_prominence\": 0.002199678196445509, \"half_prominence_width_nm\": 5.0}]"}
```

### TEST 77 — four-state resonances across measured k

- **Question:** Does four-state resonances across measured k explain the paper discrepancy?
- **Method:** Every four-state transition and both photon denominators; no inferred pole from an extremum.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** see quantitative evidence
- **Status:** PASS
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"table": "numerical_resonance_across_k.csv"}
- **Physics interpretation:** Pole proximity is necessary for a literal resonance assignment, not proof of a peak or node.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** NO
- **Requires new Pro data?:** NO

### TEST 78 — e1 -5 meV

- **Question:** Does e1 -5 meV explain the paper discrepancy?
- **Method:** Uniform single-subband diagnostic shift over k, frozen numerator; extends Demo24N with strict extrema windows.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** lower RMSE; reproduction not established
- **Status:** FAIL
- **Improved paper agreement?:** YES
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.2623007398752291, "correlation": 0.24843432102164803, "P1_nm": null, "P1_local_RMSE": 0.183573568949724, "Z1_nm": null, "Z1_local_RMSE": 0.02148406050847169, "P2_nm": 752.0, "P2_local_RMSE": 0.18237460810378772, "P3_nm": null, "P3_local_RMSE": 0.43206919752963063, "Z2_nm": null, "Z2_local_RMSE": 0.38831494805587013, "P4_nm": 1503.0, "P4_local_RMSE": 0.2638487873198255, "all_peaks_nm": "688.0;752.0;841.0;1376.0;1503.0", "all_minima_nm": "720.0;834.0;953.0;1447.0", "topology_json": "[{\"nm\": 688.0, \"local_prominence\": 0.09749439644925068, \"half_prominence_width_nm\": 10.0}, {\"nm\": 752.0, \"local_prominence\": 0.1980616299679584, \"half_prominence_width_nm\": 11.0}, {\"nm\": 841.0, \"local_prominence\": 0.0009023756938684874, \"half_prominence_width_nm\": 11.0}, {\"nm\": 1376.0, \"local_prominence\": 0.2604535098247166, \"half_prominence_width_nm\": 21.0}, {\"nm\": 1503.0, \"local_prominence\": 0.35415942361294384, \"half_prominence_width_nm\": 18.0}]"}
```

### TEST 79 — e1 +5 meV

- **Question:** Does e1 +5 meV explain the paper discrepancy?
- **Method:** Uniform single-subband diagnostic shift over k, frozen numerator; extends Demo24N with strict extrema windows.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** RMSE 0.262452; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=None, P4=1503.0. Full physical reproduction not established.
- **Status:** FAIL
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.26245224812004986, "correlation": 0.24675571465476653, "P1_nm": null, "P1_local_RMSE": 0.1835465539115795, "Z1_nm": null, "Z1_local_RMSE": 0.021497520836133415, "P2_nm": 752.0, "P2_local_RMSE": 0.18363389205726854, "P3_nm": null, "P3_local_RMSE": 0.4317479670260896, "Z2_nm": null, "Z2_local_RMSE": 0.3894429944925542, "P4_nm": 1503.0, "P4_local_RMSE": 0.2636031053025801, "all_peaks_nm": "688.0;752.0;834.0;1376.0;1503.0", "all_minima_nm": "720.0;829.0;954.0;1452.0", "topology_json": "[{\"nm\": 688.0, \"local_prominence\": 0.09784433315693225, \"half_prominence_width_nm\": 10.0}, {\"nm\": 752.0, \"local_prominence\": 0.19639775544460952, \"half_prominence_width_nm\": 11.0}, {\"nm\": 834.0, \"local_prominence\": 0.0004619830698445182, \"half_prominence_width_nm\": 8.0}, {\"nm\": 1376.0, \"local_prominence\": 0.2653353444451745, \"half_prominence_width_nm\": 23.0}, {\"nm\": 1503.0, \"local_prominence\": 0.35683718106864026, \"half_prominence_width_nm\": 18.0}]"}
```

### TEST 80 — e2 -5 meV

- **Question:** Does e2 -5 meV explain the paper discrepancy?
- **Method:** Uniform single-subband diagnostic shift over k, frozen numerator; extends Demo24N with strict extrema windows.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** lower RMSE; reproduction not established
- **Status:** FAIL
- **Improved paper agreement?:** YES
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.2570498738578264, "correlation": 0.281603211344861, "P1_nm": null, "P1_local_RMSE": 0.1837538810252912, "Z1_nm": null, "Z1_local_RMSE": 0.021391355367621358, "P2_nm": 754.0, "P2_local_RMSE": 0.1766200553845157, "P3_nm": null, "P3_local_RMSE": 0.431944446514341, "Z2_nm": null, "Z2_local_RMSE": 0.37592660701334757, "P4_nm": 1508.0, "P4_local_RMSE": 0.23580842141485908, "all_peaks_nm": "690.0;754.0;837.0;1380.0;1508.0", "all_minima_nm": "722.0;832.0;957.0;1457.0", "topology_json": "[{\"nm\": 690.0, \"local_prominence\": 0.09824579218689072, \"half_prominence_width_nm\": 10.0}, {\"nm\": 754.0, \"local_prominence\": 0.1984559340433143, \"half_prominence_width_nm\": 10.0}, {\"nm\": 837.0, \"local_prominence\": 0.0004569749528556405, \"half_prominence_width_nm\": 8.0}, {\"nm\": 1380.0, \"local_prominence\": 0.2660744313540456, \"half_prominence_width_nm\": 22.0}, {\"nm\": 1508.0, \"local_prominence\": 0.35624876134084194, \"half_prominence_width_nm\": 18.0}]"}
```

### TEST 81 — e2 +5 meV

- **Question:** Does e2 +5 meV explain the paper discrepancy?
- **Method:** Uniform single-subband diagnostic shift over k, frozen numerator; extends Demo24N with strict extrema windows.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** RMSE 0.267797; strict feature locations nm: P1=None, Z1=None, P2=749.0, P3=None, Z2=None, P4=1498.0. Full physical reproduction not established.
- **Status:** FAIL
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.2677972348201573, "correlation": 0.21334012627212146, "P1_nm": null, "P1_local_RMSE": 0.1833242903957209, "Z1_nm": null, "Z1_local_RMSE": 0.021713095158616448, "P2_nm": 749.0, "P2_local_RMSE": 0.1894446881246102, "P3_nm": null, "P3_local_RMSE": 0.43165911871734874, "Z2_nm": null, "Z2_local_RMSE": 0.40178507885779685, "P4_nm": 1498.0, "P4_local_RMSE": 0.2891051662540788, "all_peaks_nm": "686.0;749.0;838.0;1373.0;1498.0", "all_minima_nm": "717.0;831.0;950.0;1443.0", "topology_json": "[{\"nm\": 686.0, \"local_prominence\": 0.0971089183619479, \"half_prominence_width_nm\": 10.0}, {\"nm\": 749.0, \"local_prominence\": 0.198691482428626, \"half_prominence_width_nm\": 10.0}, {\"nm\": 838.0, \"local_prominence\": 0.0008657173844089788, \"half_prominence_width_nm\": 11.0}, {\"nm\": 1373.0, \"local_prominence\": 0.26085127903804617, \"half_prominence_width_nm\": 21.0}, {\"nm\": 1498.0, \"local_prominence\": 0.35327935293417345, \"half_prominence_width_nm\": 18.0}]"}
```

### TEST 82 — hh1 -5 meV

- **Question:** Does hh1 -5 meV explain the paper discrepancy?
- **Method:** Uniform single-subband diagnostic shift over k, frozen numerator; extends Demo24N with strict extrema windows.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** RMSE 0.262426; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=None, P4=1503.0. Full physical reproduction not established.
- **Status:** FAIL
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.26242580804753907, "correlation": 0.24694148987218656, "P1_nm": null, "P1_local_RMSE": 0.18353656888467465, "Z1_nm": null, "Z1_local_RMSE": 0.02150439802492447, "P2_nm": 752.0, "P2_local_RMSE": 0.18348739001023, "P3_nm": null, "P3_local_RMSE": 0.43174941442802106, "Z2_nm": null, "Z2_local_RMSE": 0.38920283682574336, "P4_nm": 1503.0, "P4_local_RMSE": 0.26364598025550323, "all_peaks_nm": "688.0;752.0;834.0;1376.0;1503.0", "all_minima_nm": "720.0;829.0;954.0;1455.0", "topology_json": "[{\"nm\": 688.0, \"local_prominence\": 0.09789695327685255, \"half_prominence_width_nm\": 10.0}, {\"nm\": 752.0, \"local_prominence\": 0.19658501551668323, \"half_prominence_width_nm\": 11.0}, {\"nm\": 834.0, \"local_prominence\": 0.000537704203869907, \"half_prominence_width_nm\": 8.0}, {\"nm\": 1376.0, \"local_prominence\": 0.26206312545184085, \"half_prominence_width_nm\": 22.0}, {\"nm\": 1503.0, \"local_prominence\": 0.3537666597626403, \"half_prominence_width_nm\": 18.0}]"}
```

### TEST 83 — hh1 +5 meV

- **Question:** Does hh1 +5 meV explain the paper discrepancy?
- **Method:** Uniform single-subband diagnostic shift over k, frozen numerator; extends Demo24N with strict extrema windows.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** lower RMSE; reproduction not established
- **Status:** FAIL
- **Improved paper agreement?:** YES
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.2623323873205052, "correlation": 0.2482566432619931, "P1_nm": null, "P1_local_RMSE": 0.18358364484716055, "Z1_nm": null, "Z1_local_RMSE": 0.021477322979311722, "P2_nm": 752.0, "P2_local_RMSE": 0.1825575838153113, "P3_nm": null, "P3_local_RMSE": 0.43206621399225725, "Z2_nm": null, "Z2_local_RMSE": 0.3885380858527731, "P4_nm": 1503.0, "P4_local_RMSE": 0.2636815630179054, "all_peaks_nm": "688.0;752.0;841.0;1376.0;1503.0", "all_minima_nm": "720.0;834.0;953.0;1455.0", "topology_json": "[{\"nm\": 688.0, \"local_prominence\": 0.09739684181111552, \"half_prominence_width_nm\": 9.0}, {\"nm\": 752.0, \"local_prominence\": 0.19776907725710535, \"half_prominence_width_nm\": 11.0}, {\"nm\": 841.0, \"local_prominence\": 0.0008177412913606824, \"half_prominence_width_nm\": 11.0}, {\"nm\": 1376.0, \"local_prominence\": 0.26216194101416024, \"half_prominence_width_nm\": 22.0}, {\"nm\": 1503.0, \"local_prominence\": 0.3557052668513311, \"half_prominence_width_nm\": 18.0}]"}
```

### TEST 84 — hh2 -5 meV

- **Question:** Does hh2 -5 meV explain the paper discrepancy?
- **Method:** Uniform single-subband diagnostic shift over k, frozen numerator; extends Demo24N with strict extrema windows.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** RMSE 0.267830; strict feature locations nm: P1=None, Z1=None, P2=749.0, P3=None, Z2=None, P4=1498.0. Full physical reproduction not established.
- **Status:** FAIL
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.2678297674611655, "correlation": 0.21315019716924993, "P1_nm": null, "P1_local_RMSE": 0.18333434961759645, "Z1_nm": null, "Z1_local_RMSE": 0.021703326480925083, "P2_nm": 749.0, "P2_local_RMSE": 0.18960129876237328, "P3_nm": null, "P3_local_RMSE": 0.4316556527407031, "Z2_nm": null, "Z2_local_RMSE": 0.40204472534699465, "P4_nm": 1498.0, "P4_local_RMSE": 0.28905544482941226, "all_peaks_nm": "686.0;749.0;838.0;1373.0;1498.0", "all_minima_nm": "718.0;832.0;950.0;1450.0", "topology_json": "[{\"nm\": 686.0, \"local_prominence\": 0.09700656055707207, \"half_prominence_width_nm\": 10.0}, {\"nm\": 749.0, \"local_prominence\": 0.19842623383495828, \"half_prominence_width_nm\": 10.0}, {\"nm\": 838.0, \"local_prominence\": 0.000790834007757299, \"half_prominence_width_nm\": 11.0}, {\"nm\": 1373.0, \"local_prominence\": 0.2625625265737518, \"half_prominence_width_nm\": 22.0}, {\"nm\": 1498.0, \"local_prominence\": 0.3548114219680819, \"half_prominence_width_nm\": 18.0}]"}
```

### TEST 85 — hh2 +5 meV

- **Question:** Does hh2 +5 meV explain the paper discrepancy?
- **Method:** Uniform single-subband diagnostic shift over k, frozen numerator; extends Demo24N with strict extrema windows.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** lower RMSE; reproduction not established
- **Status:** FAIL
- **Improved paper agreement?:** YES
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.2570242390113656, "correlation": 0.28177774427394375, "P1_nm": null, "P1_local_RMSE": 0.18374383980332618, "Z1_nm": null, "Z1_local_RMSE": 0.0213956344607477, "P2_nm": 754.0, "P2_local_RMSE": 0.17645016908195985, "P3_nm": null, "P3_local_RMSE": 0.4319453175936664, "Z2_nm": null, "Z2_local_RMSE": 0.3757177441855095, "P4_nm": 1508.0, "P4_local_RMSE": 0.23598154323944448, "all_peaks_nm": "690.0;754.0;837.0;1380.0;1508.0", "all_minima_nm": "722.0;832.0;956.0;1459.0", "topology_json": "[{\"nm\": 690.0, \"local_prominence\": 0.0983062477267635, \"half_prominence_width_nm\": 11.0}, {\"nm\": 754.0, \"local_prominence\": 0.1986384832489067, \"half_prominence_width_nm\": 10.0}, {\"nm\": 837.0, \"local_prominence\": 0.0005313666056143279, \"half_prominence_width_nm\": 8.0}, {\"nm\": 1380.0, \"local_prominence\": 0.2627915714460235, \"half_prominence_width_nm\": 22.0}, {\"nm\": 1508.0, \"local_prominence\": 0.3531620122307245, \"half_prominence_width_nm\": 18.0}]"}
```

### TEST 86 — C_m1_n1_l1 numerator -10%

- **Question:** Does C_m1_n1_l1 numerator -10% explain the paper discrepancy?
- **Method:** Change exactly one dominant pathway numerator ±10%; diagnostic only. No claim of achievable physical matrix perturbation.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** lower RMSE; reproduction not established
- **Status:** FAIL
- **Improved paper agreement?:** YES
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.24273286515183914, "correlation": 0.487053291241273, "P1_nm": 496.0, "P1_local_RMSE": 0.1995390059216608, "Z1_nm": null, "Z1_local_RMSE": 0.04611174993209181, "P2_nm": 753.0, "P2_local_RMSE": 0.08687812029035603, "P3_nm": null, "P3_local_RMSE": 0.48967091229607673, "Z2_nm": 1282.0, "Z2_local_RMSE": 0.16933745616154966, "P4_nm": 1506.0, "P4_local_RMSE": 0.2482251138420896, "all_peaks_nm": "496.0;689.0;740.0;753.0;828.0;1379.0;1479.0;1506.0;1656.0", "all_minima_nm": "573.0;697.0;746.0;814.0;1282.0;1393.0;1492.0;1630.0", "topology_json": "[{\"nm\": 496.0, \"local_prominence\": 0.00032114966658210447, \"half_prominence_width_nm\": 98.0}, {\"nm\": 689.0, \"local_prominence\": 0.010689313342844842, \"half_prominence_width_nm\": 6.0}, {\"nm\": 740.0, \"local_prominence\": 0.0659161480180343, \"half_prominence_width_nm\": 7.0}, {\"nm\": 753.0, \"local_prominence\": 0.10090477640017309, \"half_prominence_width_nm\": 8.0}, {\"nm\": 828.0, \"local_prominence\": 0.027535756557195312, \"half_prominence_width_nm\": 8.0}, {\"nm\": 1379.0, \"local_prominence\": 0.010168463245548875, \"half_prominence_width_nm\": 8.0}, {\"nm\": 1479.0, \"local_prominence\": 0.13238101276118874, \"half_prominence_width_nm\": 11.0}, {\"nm\": 1506.0, \"local_prominence\": 0.2027687491566672, \"half_prominence_width_nm\": 16.0}, {\"nm\": 1656.0, \"local_prominence\": 0.045173357020616645, \"half_prominence_width_nm\": 14.0}]"}
```

### TEST 87 — C_m1_n1_l1 numerator +10%

- **Question:** Does C_m1_n1_l1 numerator +10% explain the paper discrepancy?
- **Method:** Change exactly one dominant pathway numerator ±10%; diagnostic only. No claim of achievable physical matrix perturbation.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** lower RMSE; reproduction not established
- **Status:** FAIL
- **Improved paper agreement?:** YES
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.23697645412214335, "correlation": 0.3469955991365986, "P1_nm": null, "P1_local_RMSE": 0.1784955329836502, "Z1_nm": null, "Z1_local_RMSE": 0.02514061758669675, "P2_nm": 749.0, "P2_local_RMSE": 0.1185852206605279, "P3_nm": null, "P3_local_RMSE": 0.382335509362561, "Z2_nm": null, "Z2_local_RMSE": 0.3498202745303156, "P4_nm": 1495.0, "P4_local_RMSE": 0.26910366923279744, "all_peaks_nm": "688.0;749.0;829.0;1376.0;1495.0;1658.0", "all_minima_nm": "719.0;771.0;1013.0;1438.0;1537.0", "topology_json": "[{\"nm\": 688.0, \"local_prominence\": 0.08901785472793233, \"half_prominence_width_nm\": 11.0}, {\"nm\": 749.0, \"local_prominence\": 0.1887047031906553, \"half_prominence_width_nm\": 15.0}, {\"nm\": 829.0, \"local_prominence\": 0.09409910506347241, \"half_prominence_width_nm\": 17.0}, {\"nm\": 1376.0, \"local_prominence\": 0.21765889013872464, \"half_prominence_width_nm\": 22.0}, {\"nm\": 1495.0, \"local_prominence\": 0.4062823746514269, \"half_prominence_width_nm\": 31.0}, {\"nm\": 1658.0, \"local_prominence\": 0.12151937052836281, \"half_prominence_width_nm\": 24.0}]"}
```

### TEST 88 — C_m2_n2_l2 numerator -10%

- **Question:** Does C_m2_n2_l2 numerator -10% explain the paper discrepancy?
- **Method:** Change exactly one dominant pathway numerator ±10%; diagnostic only. No claim of achievable physical matrix perturbation.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** RMSE 0.263119; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=None, P4=1503.0. Full physical reproduction not established.
- **Status:** FAIL
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.2631191018149962, "correlation": 0.24894003973089773, "P1_nm": null, "P1_local_RMSE": 0.18377778798337865, "Z1_nm": null, "Z1_local_RMSE": 0.021383312339445827, "P2_nm": 752.0, "P2_local_RMSE": 0.1828141067492924, "P3_nm": null, "P3_local_RMSE": 0.4337869277374821, "Z2_nm": null, "Z2_local_RMSE": 0.3871818894902471, "P4_nm": 1503.0, "P4_local_RMSE": 0.2625069683183107, "all_peaks_nm": "688.0;752.0;843.0;1376.0;1503.0;1669.0", "all_minima_nm": "719.0;831.0;949.0;1456.0;1665.0", "topology_json": "[{\"nm\": 688.0, \"local_prominence\": 0.09525395350563581, \"half_prominence_width_nm\": 9.0}, {\"nm\": 752.0, \"local_prominence\": 0.1967150346408974, \"half_prominence_width_nm\": 10.0}, {\"nm\": 843.0, \"local_prominence\": 0.002812178852272834, \"half_prominence_width_nm\": 24.0}, {\"nm\": 1376.0, \"local_prominence\": 0.2625949379732905, \"half_prominence_width_nm\": 21.0}, {\"nm\": 1503.0, \"local_prominence\": 0.356462667879449, \"half_prominence_width_nm\": 18.0}, {\"nm\": 1669.0, \"local_prominence\": 7.390849391047949e-05, \"half_prominence_width_nm\": 5.0}]"}
```

### TEST 89 — C_m2_n2_l2 numerator +10%

- **Question:** Does C_m2_n2_l2 numerator +10% explain the paper discrepancy?
- **Method:** Change exactly one dominant pathway numerator ±10%; diagnostic only. No claim of achievable physical matrix perturbation.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** lower RMSE; reproduction not established
- **Status:** FAIL
- **Improved paper agreement?:** YES
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.26198864915712455, "correlation": 0.2469249255538752, "P1_nm": null, "P1_local_RMSE": 0.18344180973449356, "Z1_nm": null, "Z1_local_RMSE": 0.02155324364883328, "P2_nm": 752.0, "P2_local_RMSE": 0.18301569949097968, "P3_nm": null, "P3_local_RMSE": 0.4308903357384155, "Z2_nm": null, "Z2_local_RMSE": 0.3898376861463017, "P4_nm": 1503.0, "P4_local_RMSE": 0.26426748591682203, "all_peaks_nm": "688.0;752.0;834.0;1376.0;1503.0", "all_minima_nm": "720.0;833.0;955.0;1453.0", "topology_json": "[{\"nm\": 688.0, \"local_prominence\": 0.09892298729063798, \"half_prominence_width_nm\": 11.0}, {\"nm\": 752.0, \"local_prominence\": 0.19736876446140034, \"half_prominence_width_nm\": 11.0}, {\"nm\": 834.0, \"local_prominence\": 1.9671563903950195e-05, \"half_prominence_width_nm\": 3.0}, {\"nm\": 1376.0, \"local_prominence\": 0.2619681240004712, \"half_prominence_width_nm\": 22.0}, {\"nm\": 1503.0, \"local_prominence\": 0.3538199947589913, \"half_prominence_width_nm\": 18.0}]"}
```

### TEST 90 — V_m1_n1_l1 numerator -10%

- **Question:** Does V_m1_n1_l1 numerator -10% explain the paper discrepancy?
- **Method:** Change exactly one dominant pathway numerator ±10%; diagnostic only. No claim of achievable physical matrix perturbation.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** lower RMSE; reproduction not established
- **Status:** FAIL
- **Improved paper agreement?:** YES
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.2370073006179098, "correlation": 0.34635858886003107, "P1_nm": null, "P1_local_RMSE": 0.1784862087817371, "Z1_nm": null, "Z1_local_RMSE": 0.02516130624720498, "P2_nm": 749.0, "P2_local_RMSE": 0.11869547678976305, "P3_nm": null, "P3_local_RMSE": 0.3823419309179655, "Z2_nm": null, "Z2_local_RMSE": 0.35045301084866615, "P4_nm": 1495.0, "P4_local_RMSE": 0.2688856453861891, "all_peaks_nm": "688.0;749.0;829.0;1376.0;1495.0;1658.0", "all_minima_nm": "719.0;771.0;1012.0;1438.0;1537.0", "topology_json": "[{\"nm\": 688.0, \"local_prominence\": 0.08933980970367511, \"half_prominence_width_nm\": 11.0}, {\"nm\": 749.0, \"local_prominence\": 0.1893571882044488, \"half_prominence_width_nm\": 15.0}, {\"nm\": 829.0, \"local_prominence\": 0.09389250165665008, \"half_prominence_width_nm\": 17.0}, {\"nm\": 1376.0, \"local_prominence\": 0.21852751564664075, \"half_prominence_width_nm\": 22.0}, {\"nm\": 1495.0, \"local_prominence\": 0.4073983618186994, \"half_prominence_width_nm\": 31.0}, {\"nm\": 1658.0, \"local_prominence\": 0.1213503241544297, \"half_prominence_width_nm\": 24.0}]"}
```

### TEST 91 — V_m1_n1_l1 numerator +10%

- **Question:** Does V_m1_n1_l1 numerator +10% explain the paper discrepancy?
- **Method:** Change exactly one dominant pathway numerator ±10%; diagnostic only. No claim of achievable physical matrix perturbation.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** lower RMSE; reproduction not established
- **Status:** FAIL
- **Improved paper agreement?:** YES
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.24285787453095334, "correlation": 0.4862282813256227, "P1_nm": 493.0, "P1_local_RMSE": 0.19959894853431462, "Z1_nm": null, "Z1_local_RMSE": 0.04594780152875723, "P2_nm": 753.0, "P2_local_RMSE": 0.08710065011647682, "P3_nm": null, "P3_local_RMSE": 0.49009021094942523, "Z2_nm": 1280.0, "Z2_local_RMSE": 0.17027545606284486, "P4_nm": 1506.0, "P4_local_RMSE": 0.24752137230976032, "all_peaks_nm": "493.0;689.0;740.0;753.0;828.0;1379.0;1479.0;1506.0;1656.0", "all_minima_nm": "570.0;697.0;746.0;814.0;1280.0;1393.0;1492.0;1630.0", "topology_json": "[{\"nm\": 493.0, \"local_prominence\": 0.000293573346809386, \"half_prominence_width_nm\": 96.0}, {\"nm\": 689.0, \"local_prominence\": 0.010933798216625157, \"half_prominence_width_nm\": 6.0}, {\"nm\": 740.0, \"local_prominence\": 0.06574170848600913, \"half_prominence_width_nm\": 7.0}, {\"nm\": 753.0, \"local_prominence\": 0.1012908374858642, \"half_prominence_width_nm\": 8.0}, {\"nm\": 828.0, \"local_prominence\": 0.02732633870860751, \"half_prominence_width_nm\": 8.0}, {\"nm\": 1379.0, \"local_prominence\": 0.010770617349239564, \"half_prominence_width_nm\": 9.0}, {\"nm\": 1479.0, \"local_prominence\": 0.13208210376307428, \"half_prominence_width_nm\": 11.0}, {\"nm\": 1506.0, \"local_prominence\": 0.20357583150284386, \"half_prominence_width_nm\": 16.0}, {\"nm\": 1656.0, \"local_prominence\": 0.04488525451509573, \"half_prominence_width_nm\": 14.0}]"}
```

### TEST 92 — global transition offset -0.1 eV

- **Question:** Does global transition offset -0.1 eV explain the paper discrepancy?
- **Method:** NONPHYSICAL SENSITIVITY DIAGNOSTIC: same offset to all four transition energies, no peak-specific fit.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** lower RMSE; reproduction not established
- **Status:** FAIL
- **Improved paper agreement?:** YES
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.22680031673520687, "correlation": 0.4612696447825143, "P1_nm": null, "P1_local_RMSE": 0.18734691997159597, "Z1_nm": null, "Z1_local_RMSE": 0.027008696055553748, "P2_nm": 729.0, "P2_local_RMSE": 0.13562276273947807, "P3_nm": null, "P3_local_RMSE": 0.4349940403531789, "Z2_nm": null, "Z2_local_RMSE": 0.12019402340189622, "P4_nm": 1457.0, "P4_local_RMSE": 0.34635094326996885, "all_peaks_nm": "729.0;800.0;899.0;1457.0;1600.0", "all_minima_nm": "764.0;891.0;1011.0;1545.0", "topology_json": "[{\"nm\": 729.0, \"local_prominence\": 0.09653673159322834, \"half_prominence_width_nm\": 11.0}, {\"nm\": 800.0, \"local_prominence\": 0.20084008197674336, \"half_prominence_width_nm\": 12.0}, {\"nm\": 899.0, \"local_prominence\": 0.0008359774663574959, \"half_prominence_width_nm\": 12.0}, {\"nm\": 1457.0, \"local_prominence\": 0.2626703097261248, \"half_prominence_width_nm\": 24.0}, {\"nm\": 1600.0, \"local_prominence\": 0.3554727050494436, \"half_prominence_width_nm\": 21.0}]"}
```

### TEST 93 — global transition offset -0.05 eV

- **Question:** Does global transition offset -0.05 eV explain the paper discrepancy?
- **Method:** NONPHYSICAL SENSITIVITY DIAGNOSTIC: same offset to all four transition energies, no peak-specific fit.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** lower RMSE; reproduction not established
- **Status:** FAIL
- **Improved paper agreement?:** YES
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.23097687704184305, "correlation": 0.43624686954765385, "P1_nm": null, "P1_local_RMSE": 0.18561857952280633, "Z1_nm": null, "Z1_local_RMSE": 0.023165374601895636, "P2_nm": 775.0, "P2_local_RMSE": 0.1288288182917951, "P3_nm": null, "P3_local_RMSE": 0.43411150859721537, "Z2_nm": null, "Z2_local_RMSE": 0.19065828971627674, "P4_nm": 1550.0, "P4_local_RMSE": 0.1973044838039741, "all_peaks_nm": "708.0;775.0;867.0;1416.0;1550.0", "all_minima_nm": "741.0;860.0;981.0;1499.0", "topology_json": "[{\"nm\": 708.0, \"local_prominence\": 0.09764041094384768, \"half_prominence_width_nm\": 10.0}, {\"nm\": 775.0, \"local_prominence\": 0.19982536050671768, \"half_prominence_width_nm\": 10.0}, {\"nm\": 867.0, \"local_prominence\": 0.0007333557977466792, \"half_prominence_width_nm\": 11.0}, {\"nm\": 1416.0, \"local_prominence\": 0.2625592580882703, \"half_prominence_width_nm\": 24.0}, {\"nm\": 1550.0, \"local_prominence\": 0.35504914830230827, \"half_prominence_width_nm\": 19.0}]"}
```

### TEST 94 — global transition offset -0.02 eV

- **Question:** Does global transition offset -0.02 eV explain the paper discrepancy?
- **Method:** NONPHYSICAL SENSITIVITY DIAGNOSTIC: same offset to all four transition energies, no peak-specific fit.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** lower RMSE; reproduction not established
- **Status:** FAIL
- **Improved paper agreement?:** YES
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.2423379659705207, "correlation": 0.371489507159509, "P1_nm": null, "P1_local_RMSE": 0.18440973879333208, "Z1_nm": null, "Z1_local_RMSE": 0.021535779676221625, "P2_nm": 761.0, "P2_local_RMSE": 0.15378303093997026, "P3_nm": null, "P3_local_RMSE": 0.43284932325720665, "Z2_nm": null, "Z2_local_RMSE": 0.3243951317861156, "P4_nm": 1521.0, "P4_local_RMSE": 0.15524502521536548, "all_peaks_nm": "696.0;761.0;849.0;1392.0;1521.0", "all_minima_nm": "728.0;843.0;964.0;1472.0", "topology_json": "[{\"nm\": 696.0, \"local_prominence\": 0.09824279185083862, \"half_prominence_width_nm\": 10.0}, {\"nm\": 761.0, \"local_prominence\": 0.19931664746280725, \"half_prominence_width_nm\": 10.0}, {\"nm\": 849.0, \"local_prominence\": 0.0007060360764990226, \"half_prominence_width_nm\": 9.0}, {\"nm\": 1392.0, \"local_prominence\": 0.2630788624553202, \"half_prominence_width_nm\": 22.0}, {\"nm\": 1521.0, \"local_prominence\": 0.3540769945449527, \"half_prominence_width_nm\": 18.0}]"}
```

### TEST 95 — global transition offset 0 eV

- **Question:** Does global transition offset 0 eV explain the paper discrepancy?
- **Method:** NONPHYSICAL SENSITIVITY DIAGNOSTIC: same offset to all four transition energies, no peak-specific fit.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** RMSE 0.262391; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=None, P4=1503.0. Full physical reproduction not established.
- **Status:** FAIL
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.26239111786932695, "correlation": 0.24755539373540594, "P1_nm": null, "P1_local_RMSE": 0.18355832245681228, "Z1_nm": null, "Z1_local_RMSE": 0.02149182751741102, "P2_nm": 752.0, "P2_local_RMSE": 0.18300269017624166, "P3_nm": null, "P3_local_RMSE": 0.43189844880285366, "Z2_nm": null, "Z2_local_RMSE": 0.3889313933218363, "P4_nm": 1503.0, "P4_local_RMSE": 0.2637088552636287, "all_peaks_nm": "688.0;752.0;837.0;1376.0;1503.0", "all_minima_nm": "720.0;832.0;953.0;1455.0", "topology_json": "[{\"nm\": 688.0, \"local_prominence\": 0.09763940881279826, \"half_prominence_width_nm\": 10.0}, {\"nm\": 752.0, \"local_prominence\": 0.19711267904504853, \"half_prominence_width_nm\": 11.0}, {\"nm\": 837.0, \"local_prominence\": 0.0006496885138127656, \"half_prominence_width_nm\": 9.0}, {\"nm\": 1376.0, \"local_prominence\": 0.2621557638752432, \"half_prominence_width_nm\": 22.0}, {\"nm\": 1503.0, \"local_prominence\": 0.354655473337367, \"half_prominence_width_nm\": 18.0}]"}
```

### TEST 96 — global transition offset 0.02 eV

- **Question:** Does global transition offset 0.02 eV explain the paper discrepancy?
- **Method:** NONPHYSICAL SENSITIVITY DIAGNOSTIC: same offset to all four transition energies, no peak-specific fit.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** RMSE 0.282658; strict feature locations nm: P1=None, Z1=None, P2=743.0, P3=None, Z2=None, P4=1485.0. Full physical reproduction not established.
- **Status:** FAIL
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.28265763762084767, "correlation": 0.11126363502487761, "P1_nm": null, "P1_local_RMSE": 0.18262057022095093, "Z1_nm": null, "Z1_local_RMSE": 0.02311036960881525, "P2_nm": 743.0, "P2_local_RMSE": 0.21229749734986644, "P3_nm": null, "P3_local_RMSE": 0.43062155735102337, "Z2_nm": null, "Z2_local_RMSE": 0.435905917685689, "P4_nm": 1485.0, "P4_local_RMSE": 0.348983521240087, "all_peaks_nm": "681.0;743.0;826.0;1361.0;1485.0", "all_minima_nm": "711.0;821.0;942.0;1438.0", "topology_json": "[{\"nm\": 681.0, \"local_prominence\": 0.09847308161691842, \"half_prominence_width_nm\": 10.0}, {\"nm\": 743.0, \"local_prominence\": 0.1966021398512457, \"half_prominence_width_nm\": 10.0}, {\"nm\": 826.0, \"local_prominence\": 0.0006252220162269867, \"half_prominence_width_nm\": 9.0}, {\"nm\": 1361.0, \"local_prominence\": 0.26244925025274857, \"half_prominence_width_nm\": 22.0}, {\"nm\": 1485.0, \"local_prominence\": 0.3545115817997908, \"half_prominence_width_nm\": 18.0}]"}
```

### TEST 97 — global transition offset 0.05 eV

- **Question:** Does global transition offset 0.05 eV explain the paper discrepancy?
- **Method:** NONPHYSICAL SENSITIVITY DIAGNOSTIC: same offset to all four transition energies, no peak-specific fit.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** RMSE 0.305674; strict feature locations nm: P1=None, Z1=None, P2=729.0, P3=None, Z2=None, P4=1459.0. Full physical reproduction not established.
- **Status:** FAIL
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.30567362782736, "correlation": -0.0583794853222935, "P1_nm": null, "P1_local_RMSE": 0.18106396055418458, "Z1_nm": null, "Z1_local_RMSE": 0.0308457771925403, "P2_nm": 729.0, "P2_local_RMSE": 0.251030727408757, "P3_nm": null, "P3_local_RMSE": 0.42822826994768587, "Z2_nm": null, "Z2_local_RMSE": 0.48952031100271454, "P4_nm": 1459.0, "P4_local_RMSE": 0.40830527111006387, "all_peaks_nm": "670.0;729.0;810.0;1339.0;1459.0", "all_minima_nm": "699.0;805.0;927.0;1413.0", "topology_json": "[{\"nm\": 670.0, \"local_prominence\": 0.09884124862362925, \"half_prominence_width_nm\": 10.0}, {\"nm\": 729.0, \"local_prominence\": 0.19491927733138237, \"half_prominence_width_nm\": 9.0}, {\"nm\": 810.0, \"local_prominence\": 0.000590054995146666, \"half_prominence_width_nm\": 8.0}, {\"nm\": 1339.0, \"local_prominence\": 0.2625881996720224, \"half_prominence_width_nm\": 20.0}, {\"nm\": 1459.0, \"local_prominence\": 0.3541396797656674, \"half_prominence_width_nm\": 17.0}]"}
```

### TEST 98 — global transition offset 0.1 eV

- **Question:** Does global transition offset 0.1 eV explain the paper discrepancy?
- **Method:** NONPHYSICAL SENSITIVITY DIAGNOSTIC: same offset to all four transition energies, no peak-specific fit.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** RMSE 0.328127; strict feature locations nm: P1=None, Z1=None, P2=784.0, P3=None, Z2=1374.0, P4=None. Full physical reproduction not established.
- **Status:** FAIL
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.3281271322128667, "correlation": -0.24230305213971548, "P1_nm": null, "P1_local_RMSE": 0.1780077192283964, "Z1_nm": null, "Z1_local_RMSE": 0.08336073864531834, "P2_nm": 784.0, "P2_local_RMSE": 0.2945915778030651, "P3_nm": null, "P3_local_RMSE": 0.42289909640181694, "Z2_nm": 1374.0, "Z2_local_RMSE": 0.5518234430975213, "P4_nm": null, "P4_local_RMSE": 0.4323691280371833, "all_peaks_nm": "652.0;709.0;784.0;1304.0;1417.0", "all_minima_nm": "680.0;779.0;902.0;1374.0", "topology_json": "[{\"nm\": 652.0, \"local_prominence\": 0.09992792970199094, \"half_prominence_width_nm\": 9.0}, {\"nm\": 709.0, \"local_prominence\": 0.19530887860831914, \"half_prominence_width_nm\": 9.0}, {\"nm\": 784.0, \"local_prominence\": 0.0005260282049222992, \"half_prominence_width_nm\": 7.0}, {\"nm\": 1304.0, \"local_prominence\": 0.2627677477027982, \"half_prominence_width_nm\": 19.0}, {\"nm\": 1417.0, \"local_prominence\": 0.3538704674081111, \"half_prominence_width_nm\": 16.0}]"}
```

### TEST 99 — global transition scale 0.9

- **Question:** Does global transition scale 0.9 explain the paper discrepancy?
- **Method:** NONPHYSICAL SENSITIVITY DIAGNOSTIC: scale all energies and hence all differences; Gamma fixed.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** lower RMSE; reproduction not established
- **Status:** FAIL
- **Improved paper agreement?:** YES
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.2395079794787299, "correlation": 0.41549730805706836, "P1_nm": null, "P1_local_RMSE": 0.19016129506155519, "Z1_nm": null, "Z1_local_RMSE": 0.03333669293761542, "P2_nm": 765.0, "P2_local_RMSE": 0.20685969533427684, "P3_nm": null, "P3_local_RMSE": 0.4394244325348911, "Z2_nm": null, "Z2_local_RMSE": 0.07598631094868402, "P4_nm": 1530.0, "P4_local_RMSE": 0.23326494580060456, "all_peaks_nm": "765.0;835.0;930.0;1530.0;1670.0", "all_minima_nm": "799.0;924.0;1059.0;1616.0", "topology_json": "[{\"nm\": 765.0, \"local_prominence\": 0.09230597182517081, \"half_prominence_width_nm\": 11.0}, {\"nm\": 835.0, \"local_prominence\": 0.18989927311267302, \"half_prominence_width_nm\": 12.0}, {\"nm\": 930.0, \"local_prominence\": 0.00039909253991131377, \"half_prominence_width_nm\": 8.0}, {\"nm\": 1530.0, \"local_prominence\": 0.2513746475845777, \"half_prominence_width_nm\": 25.0}, {\"nm\": 1670.0, \"local_prominence\": 0.3348478285093256, \"half_prominence_width_nm\": 21.0}]"}
```

### TEST 100 — global transition scale 0.95

- **Question:** Does global transition scale 0.95 explain the paper discrepancy?
- **Method:** NONPHYSICAL SENSITIVITY DIAGNOSTIC: scale all energies and hence all differences; Gamma fixed.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** lower RMSE; reproduction not established
- **Status:** FAIL
- **Improved paper agreement?:** YES
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.22669446060378268, "correlation": 0.46793880711194574, "P1_nm": null, "P1_local_RMSE": 0.18736542440608359, "Z1_nm": null, "Z1_local_RMSE": 0.026594098274901473, "P2_nm": 791.0, "P2_local_RMSE": 0.12971503446459248, "P3_nm": null, "P3_local_RMSE": 0.4376711163198677, "Z2_nm": null, "Z2_local_RMSE": 0.12559694366607466, "P4_nm": 1582.0, "P4_local_RMSE": 0.32077272125200085, "all_peaks_nm": "725.0;791.0;881.0;1449.0;1582.0", "all_minima_nm": "757.0;876.0;1003.0;1531.0", "topology_json": "[{\"nm\": 725.0, \"local_prominence\": 0.09490329854929225, \"half_prominence_width_nm\": 10.0}, {\"nm\": 791.0, \"local_prominence\": 0.19440410187028523, \"half_prominence_width_nm\": 10.0}, {\"nm\": 881.0, \"local_prominence\": 0.0005211951110285218, \"half_prominence_width_nm\": 9.0}, {\"nm\": 1449.0, \"local_prominence\": 0.25742503195905786, \"half_prominence_width_nm\": 23.0}, {\"nm\": 1582.0, \"local_prominence\": 0.3451356932989581, \"half_prominence_width_nm\": 19.0}]"}
```

### TEST 101 — global transition scale 1

- **Question:** Does global transition scale 1 explain the paper discrepancy?
- **Method:** NONPHYSICAL SENSITIVITY DIAGNOSTIC: scale all energies and hence all differences; Gamma fixed.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** RMSE 0.262391; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=None, P4=1503.0. Full physical reproduction not established.
- **Status:** FAIL
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.26239111786932695, "correlation": 0.24755539373540594, "P1_nm": null, "P1_local_RMSE": 0.18355832245681228, "Z1_nm": null, "Z1_local_RMSE": 0.02149182751741102, "P2_nm": 752.0, "P2_local_RMSE": 0.18300269017624166, "P3_nm": null, "P3_local_RMSE": 0.43189844880285366, "Z2_nm": null, "Z2_local_RMSE": 0.3889313933218363, "P4_nm": 1503.0, "P4_local_RMSE": 0.2637088552636287, "all_peaks_nm": "688.0;752.0;837.0;1376.0;1503.0", "all_minima_nm": "720.0;832.0;953.0;1455.0", "topology_json": "[{\"nm\": 688.0, \"local_prominence\": 0.09763940881279826, \"half_prominence_width_nm\": 10.0}, {\"nm\": 752.0, \"local_prominence\": 0.19711267904504853, \"half_prominence_width_nm\": 11.0}, {\"nm\": 837.0, \"local_prominence\": 0.0006496885138127656, \"half_prominence_width_nm\": 9.0}, {\"nm\": 1376.0, \"local_prominence\": 0.2621557638752432, \"half_prominence_width_nm\": 22.0}, {\"nm\": 1503.0, \"local_prominence\": 0.354655473337367, \"half_prominence_width_nm\": 18.0}]"}
```

### TEST 102 — global transition scale 1.05

- **Question:** Does global transition scale 1.05 explain the paper discrepancy?
- **Method:** NONPHYSICAL SENSITIVITY DIAGNOSTIC: scale all energies and hence all differences; Gamma fixed.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** RMSE 0.321493; strict feature locations nm: P1=None, Z1=None, P2=798.0, P3=None, Z2=1386.0, P4=None. Full physical reproduction not established.
- **Status:** FAIL
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.32149331255278507, "correlation": -0.1921295346342955, "P1_nm": null, "P1_local_RMSE": 0.17814391726977907, "Z1_nm": null, "Z1_local_RMSE": 0.06380366354103416, "P2_nm": 798.0, "P2_local_RMSE": 0.27904600061114593, "P3_nm": null, "P3_local_RMSE": 0.4212710347305241, "Z2_nm": 1386.0, "Z2_local_RMSE": 0.5357858699692586, "P4_nm": null, "P4_local_RMSE": 0.40921613738649115, "all_peaks_nm": "656.0;716.0;798.0;1311.0;1432.0", "all_minima_nm": "685.0;792.0;908.0;1386.0", "topology_json": "[{\"nm\": 656.0, \"local_prominence\": 0.09961498459282081, \"half_prominence_width_nm\": 9.0}, {\"nm\": 716.0, \"local_prominence\": 0.20313708333599922, \"half_prominence_width_nm\": 10.0}, {\"nm\": 798.0, \"local_prominence\": 0.0008009968822254715, \"half_prominence_width_nm\": 10.0}, {\"nm\": 1311.0, \"local_prominence\": 0.267969744244287, \"half_prominence_width_nm\": 21.0}, {\"nm\": 1432.0, \"local_prominence\": 0.3625411189629061, \"half_prominence_width_nm\": 17.0}]"}
```

### TEST 103 — global transition scale 1.1

- **Question:** Does global transition scale 1.1 explain the paper discrepancy?
- **Method:** NONPHYSICAL SENSITIVITY DIAGNOSTIC: scale all energies and hence all differences; Gamma fixed.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** RMSE 0.336100; strict feature locations nm: P1=None, Z1=None, P2=762.0, P3=None, Z2=1323.0, P4=None. Full physical reproduction not established.
- **Status:** FAIL
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** numerical_metrics.csv; numerical_spectra.csv (matching variant row/column)
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.33610004902988266, "correlation": -0.3302556754399759, "P1_nm": null, "P1_local_RMSE": 0.17015519087049982, "Z1_nm": null, "Z1_local_RMSE": 0.20162269178555667, "P2_nm": 762.0, "P2_local_RMSE": 0.3109640171874084, "P3_nm": null, "P3_local_RMSE": 0.40379090794715766, "Z2_nm": 1323.0, "Z2_local_RMSE": 0.6151224152368356, "P4_nm": null, "P4_local_RMSE": 0.47497367768620274, "all_peaks_nm": "626.0;683.0;762.0;1251.0;1367.0", "all_minima_nm": "654.0;756.0;867.0;1323.0", "topology_json": "[{\"nm\": 626.0, \"local_prominence\": 0.10288225861622707, \"half_prominence_width_nm\": 9.0}, {\"nm\": 683.0, \"local_prominence\": 0.20538566235073086, \"half_prominence_width_nm\": 9.0}, {\"nm\": 762.0, \"local_prominence\": 0.0009123404061840007, \"half_prominence_width_nm\": 10.0}, {\"nm\": 1251.0, \"local_prominence\": 0.27306237739121975, \"half_prominence_width_nm\": 19.0}, {\"nm\": 1367.0, \"local_prominence\": 0.37074694789885376, \"half_prominence_width_nm\": 15.0}]"}
```

### TEST 104 — lambda_half

- **Question:** Does lambda_half explain the paper discrepancy?
- **Method:** Final-axis diagnostic; compare shared support only; original full-grid normalization preserved. NO extrapolation.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** see quantitative evidence
- **Status:** FAIL
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"shared_min_nm": 400.0, "shared_max_nm": 925.0, "common_domain_RMSE": 0.20195708521532124, "baseline_same_domain_RMSE": 0.15156792892746582}
- **Physics interpretation:** Common-domain metric is not ranked against full-domain baseline; coordinate remapping cannot invent additional extrema.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

### TEST 105 — lambda_double

- **Question:** Does lambda_double explain the paper discrepancy?
- **Method:** Final-axis diagnostic; compare shared support only; original full-grid normalization preserved. NO extrapolation.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** see quantitative evidence
- **Status:** FAIL
- **Improved paper agreement?:** YES
- **Quantitative evidence / file:** {"shared_min_nm": 800.0, "shared_max_nm": 1850.0, "common_domain_RMSE": 0.29549043953772336, "baseline_same_domain_RMSE": 0.2972182680546098}
- **Physics interpretation:** Common-domain metric is not ranked against full-domain baseline; coordinate remapping cannot invent additional extrema.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

### TEST 106 — wavelength shift -100

- **Question:** Does wavelength shift -100 explain the paper discrepancy?
- **Method:** Final-axis diagnostic; compare shared support only; original full-grid normalization preserved. NO extrapolation.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** see quantitative evidence
- **Status:** FAIL
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"shared_min_nm": 400.0, "shared_max_nm": 1750.0, "common_domain_RMSE": 0.3505781640739972, "baseline_same_domain_RMSE": 0.270245209351212}
- **Physics interpretation:** Common-domain metric is not ranked against full-domain baseline; coordinate remapping cannot invent additional extrema.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

### TEST 107 — wavelength shift -50

- **Question:** Does wavelength shift -50 explain the paper discrepancy?
- **Method:** Final-axis diagnostic; compare shared support only; original full-grid normalization preserved. NO extrapolation.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** see quantitative evidence
- **Status:** FAIL
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"shared_min_nm": 400.0, "shared_max_nm": 1800.0, "common_domain_RMSE": 0.32134897724225353, "baseline_same_domain_RMSE": 0.26627114166549865}
- **Physics interpretation:** Common-domain metric is not ranked against full-domain baseline; coordinate remapping cannot invent additional extrema.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

### TEST 108 — wavelength shift 50

- **Question:** Does wavelength shift 50 explain the paper discrepancy?
- **Method:** Final-axis diagnostic; compare shared support only; original full-grid normalization preserved. NO extrapolation.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** see quantitative evidence
- **Status:** FAIL
- **Improved paper agreement?:** YES
- **Quantitative evidence / file:** {"shared_min_nm": 450.0, "shared_max_nm": 1850.0, "common_domain_RMSE": 0.23195457072875103, "baseline_same_domain_RMSE": 0.2669742096986616}
- **Physics interpretation:** Common-domain metric is not ranked against full-domain baseline; coordinate remapping cannot invent additional extrema.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

### TEST 109 — wavelength shift 100

- **Question:** Does wavelength shift 100 explain the paper discrepancy?
- **Method:** Final-axis diagnostic; compare shared support only; original full-grid normalization preserved. NO extrapolation.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** see quantitative evidence
- **Status:** FAIL
- **Improved paper agreement?:** YES
- **Quantitative evidence / file:** {"shared_min_nm": 500.0, "shared_max_nm": 1850.0, "common_domain_RMSE": 0.23915598824559967, "baseline_same_domain_RMSE": 0.2715204028022945}
- **Physics interpretation:** Common-domain metric is not ranked against full-domain baseline; coordinate remapping cannot invent additional extrema.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

### TEST 110 — wavelength scale 0.9

- **Question:** Does wavelength scale 0.9 explain the paper discrepancy?
- **Method:** Final-axis diagnostic; compare shared support only; original full-grid normalization preserved. NO extrapolation.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** see quantitative evidence
- **Status:** FAIL
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"shared_min_nm": 400.0, "shared_max_nm": 1665.0, "common_domain_RMSE": 0.3568057870812557, "baseline_same_domain_RMSE": 0.2771168081777994}
- **Physics interpretation:** Common-domain metric is not ranked against full-domain baseline; coordinate remapping cannot invent additional extrema.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

### TEST 111 — wavelength scale 0.95

- **Question:** Does wavelength scale 0.95 explain the paper discrepancy?
- **Method:** Final-axis diagnostic; compare shared support only; original full-grid normalization preserved. NO extrapolation.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** see quantitative evidence
- **Status:** FAIL
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"shared_min_nm": 400.0, "shared_max_nm": 1757.0, "common_domain_RMSE": 0.33316660839281487, "baseline_same_domain_RMSE": 0.26968751971972105}
- **Physics interpretation:** Common-domain metric is not ranked against full-domain baseline; coordinate remapping cannot invent additional extrema.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

### TEST 112 — wavelength scale 1.05

- **Question:** Does wavelength scale 1.05 explain the paper discrepancy?
- **Method:** Final-axis diagnostic; compare shared support only; original full-grid normalization preserved. NO extrapolation.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** see quantitative evidence
- **Status:** FAIL
- **Improved paper agreement?:** YES
- **Quantitative evidence / file:** {"shared_min_nm": 420.0, "shared_max_nm": 1850.0, "common_domain_RMSE": 0.2283714623054726, "baseline_same_domain_RMSE": 0.26420327737680044}
- **Physics interpretation:** Common-domain metric is not ranked against full-domain baseline; coordinate remapping cannot invent additional extrema.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

### TEST 113 — wavelength scale 1.1

- **Question:** Does wavelength scale 1.1 explain the paper discrepancy?
- **Method:** Final-axis diagnostic; compare shared support only; original full-grid normalization preserved. NO extrapolation.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** see quantitative evidence
- **Status:** FAIL
- **Improved paper agreement?:** YES
- **Quantitative evidence / file:** {"shared_min_nm": 441.0, "shared_max_nm": 1850.0, "common_domain_RMSE": 0.23013831787165226, "baseline_same_domain_RMSE": 0.26613646410913955}
- **Physics interpretation:** Common-domain metric is not ranked against full-domain baseline; coordinate remapping cannot invent additional extrema.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** Not sufficient as a sole explanation in this tested variant; contribution not excluded
- **Requires new Pro data?:** NO

### TEST 114 — paper linear

- **Question:** Does paper linear explain the paper discrepancy?
- **Method:** Interpolation-method robustness, not experimental error bars.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** RMSE 0.262391; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=None, P4=1503.0. Full physical reproduction not established.
- **Status:** PASS
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"paper_feature_metrics": {"normalized_RMSE": 0.0, "correlation": 1.0, "P1_nm": 540.0, "P1_norm": 0.3189873417721519, "P1_local_RMSE": 0.0, "P1_at_target_norm": 0.3189873417721519, "Z1_nm": 605.0, "Z1_norm": 0.0, "Z1_local_RMSE": 0.0, "Z1_at_target_norm": 0.0, "P2_nm": 760.0, "P2_norm": 0.620253164556962, "P2_local_RMSE": 0.0, "P2_at_target_norm": 0.620253164556962, "P3_nm": 1080.0, "P3_norm": 0.8227848101265823, "P3_local_RMSE": 0.0, "P3_at_target_norm": 0.8227848101265823, "Z2_nm": 1330.0, "Z2_norm": 0.0, "Z2_local_RMSE": 0.0, "Z2_at_target_norm": 0.0, "P4_nm": 1520.0, "P4_norm": 1.0, "P4_local_RMSE": 0.0, "P4_at_target_norm": 1.0, "all_peaks_nm": "540.0;760.0;1080.0;1175.0;1520.0", "all_minima_nm": "605.0;850.0;1150.0;1225.0;1275.0;1330.0", "peak_count": 5, "minimum_count": 6, "derivative_sign_changes": 11, "topology_json": "[{\"nm\": 540.0, \"local_prominence\": 0.2936708860759493, \"half_prominence_width_nm\": 49.0}, {\"nm\": 760.0, \"local_prominence\": 0.34177215189873417, \"half_prominence_width_nm\": 41.0}, {\"nm\": 1080.0, \"local_prominence\": 0.5316455696202532, \"half_prominence_width_nm\": 55.0}, {\"nm\": 1175.0, \"local_prominence\": 0.0075949367088607445, \"half_prominence_width_nm\": 16.0}, {\"nm\": 1520.0, \"local_prominence\": 0.8227848101265822, \"half_prominence_width_nm\": 60.0}]"}}
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** NO
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.26239111786932695, "correlation": 0.24755539373540594, "P1_nm": null, "P1_local_RMSE": 0.18355832245681228, "Z1_nm": null, "Z1_local_RMSE": 0.02149182751741102, "P2_nm": 752.0, "P2_local_RMSE": 0.18300269017624166, "P3_nm": null, "P3_local_RMSE": 0.43189844880285366, "Z2_nm": null, "Z2_local_RMSE": 0.3889313933218363, "P4_nm": 1503.0, "P4_local_RMSE": 0.2637088552636287, "all_peaks_nm": "688.0;752.0;837.0;1376.0;1503.0", "all_minima_nm": "720.0;832.0;953.0;1455.0", "topology_json": "[{\"nm\": 688.0, \"local_prominence\": 0.09763940881279826, \"half_prominence_width_nm\": 10.0}, {\"nm\": 752.0, \"local_prominence\": 0.19711267904504853, \"half_prominence_width_nm\": 11.0}, {\"nm\": 837.0, \"local_prominence\": 0.0006496885138127656, \"half_prominence_width_nm\": 9.0}, {\"nm\": 1376.0, \"local_prominence\": 0.2621557638752432, \"half_prominence_width_nm\": 22.0}, {\"nm\": 1503.0, \"local_prominence\": 0.354655473337367, \"half_prominence_width_nm\": 18.0}]"}
```

### TEST 115 — paper shape_preserving_cubic

- **Question:** Does paper shape_preserving_cubic explain the paper discrepancy?
- **Method:** Interpolation-method robustness, not experimental error bars.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** RMSE 0.265058; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=None, P4=1503.0. Full physical reproduction not established.
- **Status:** PASS
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"paper_feature_metrics": {"normalized_RMSE": 0.0, "correlation": 1.0, "P1_nm": 540.0, "P1_norm": 0.3189873417721519, "P1_local_RMSE": 0.0, "P1_at_target_norm": 0.3189873417721519, "Z1_nm": 605.0, "Z1_norm": 0.0, "Z1_local_RMSE": 0.0, "Z1_at_target_norm": 0.0, "P2_nm": 760.0, "P2_norm": 0.620253164556962, "P2_local_RMSE": 0.0, "P2_at_target_norm": 0.620253164556962, "P3_nm": 1080.0, "P3_norm": 0.8227848101265823, "P3_local_RMSE": 0.0, "P3_at_target_norm": 0.8227848101265823, "Z2_nm": 1330.0, "Z2_norm": 0.0, "Z2_local_RMSE": 0.0, "Z2_at_target_norm": 0.0, "P4_nm": 1520.0, "P4_norm": 1.0, "P4_local_RMSE": 0.0, "P4_at_target_norm": 1.0, "all_peaks_nm": "540.0;760.0;1080.0;1175.0;1231.0;1520.0", "all_minima_nm": "605.0;850.0;1150.0;1225.0;1232.0;1275.0;1330.0", "peak_count": 6, "minimum_count": 7, "derivative_sign_changes": 13, "topology_json": "[{\"nm\": 540.0, \"local_prominence\": 0.2936708860759493, \"half_prominence_width_nm\": 48.0}, {\"nm\": 760.0, \"local_prominence\": 0.34177215189873417, \"half_prominence_width_nm\": 41.0}, {\"nm\": 1080.0, \"local_prominence\": 0.5316455696202532, \"half_prominence_width_nm\": 53.0}, {\"nm\": 1175.0, \"local_prominence\": 0.0075949367088607445, \"half_prominence_width_nm\": 21.0}, {\"nm\": 1231.0, \"local_prominence\": 2.7755575615628914e-17, \"half_prominence_width_nm\": 2.0}, {\"nm\": 1520.0, \"local_prominence\": 0.8227848101265822, \"half_prominence_width_nm\": 58.0}]"}}
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** NO
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.26505755572383854, "correlation": 0.24296759901016113, "P1_nm": null, "P1_local_RMSE": 0.19103839336452727, "Z1_nm": null, "Z1_local_RMSE": 0.023999747237175982, "P2_nm": 752.0, "P2_local_RMSE": 0.18624629718417168, "P3_nm": null, "P3_local_RMSE": 0.43687727364594425, "Z2_nm": null, "Z2_local_RMSE": 0.39101640286287165, "P4_nm": 1503.0, "P4_local_RMSE": 0.2718263097565085, "all_peaks_nm": "688.0;752.0;837.0;1376.0;1503.0", "all_minima_nm": "720.0;832.0;953.0;1455.0", "topology_json": "[{\"nm\": 688.0, \"local_prominence\": 0.09763940881279826, \"half_prominence_width_nm\": 10.0}, {\"nm\": 752.0, \"local_prominence\": 0.19711267904504853, \"half_prominence_width_nm\": 11.0}, {\"nm\": 837.0, \"local_prominence\": 0.0006496885138127656, \"half_prominence_width_nm\": 9.0}, {\"nm\": 1376.0, \"local_prominence\": 0.2621557638752432, \"half_prominence_width_nm\": 22.0}, {\"nm\": 1503.0, \"local_prominence\": 0.354655473337367, \"half_prominence_width_nm\": 18.0}]"}
```

### TEST 116 — direct_paper_points

- **Question:** Does direct_paper_points explain the paper discrepancy?
- **Method:** Sample model at digitized points; original model normalization. Distinct sampling measure.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv; C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\tables\tracked_dispersions_and_fits.csv; C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** see quantitative evidence
- **Status:** PASS
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"direct_point_RMSE": 0.26229509805952295, "point_count": 45}
- **Physics interpretation:** Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- **Reason it worked or failed:** Changed poles, cancellation or display can reduce aggregate error without matching topology.
- **Hypothesis remains plausible?:** NO
- **Requires new Pro data?:** NO

### TEST 117 — Independent engine isolation

- **Question:** Does the independent evaluator call the production engine?
- **Method:** Inspect AST calls of independent_eq2 and source imports.
- **Input data:** Existing Demo23D inputs and Demo26 extended artifacts
- **Result:** No production evaluator called
- **Status:** PASS
- **Improved paper agreement?:** N/A
- **Quantitative evidence / file:** ["integration_weights", "np.zeros", "np.zeros_like", "prefactor", "range", "Evaluation", "np.asarray", "np.asarray", "np.asarray", "len", "range", "range", "range", "np.conj", "np.conj"]
- **Physics interpretation:** Genuinely separate evaluation, but shared input values can still be wrong.
- **Reason it worked or failed:** Genuinely separate evaluation, but shared input values can still be wrong.
- **Hypothesis remains plausible?:** NO
- **Requires new Pro data?:** NO

### TEST 118 — Direct pathway and subtotal comparison

- **Question:** Do independent and production real-input pathways agree?
- **Method:** Execute both engines and compare all 16 pathways and both subtotals.
- **Input data:** Existing Demo23D inputs and Demo26 extended artifacts
- **Result:** Pathway max 4.687e-13; electron subtotal 4.099e-13; HH 4.764e-13 pm/V
- **Status:** PASS
- **Improved paper agreement?:** N/A
- **Quantitative evidence / file:** DIRECT_ENGINE_PATHWAY_COMPARISON.csv; engine_verification.json
- **Physics interpretation:** Ordinary arithmetic/transcription error strongly disfavored for real frozen baseline.
- **Reason it worked or failed:** Ordinary arithmetic/transcription error strongly disfavored for real frozen baseline.
- **Hypothesis remains plausible?:** NO
- **Requires new Pro data?:** NO

### TEST 119 — Direct denominator comparison

- **Question:** Do both executed engines construct identical denominators?
- **Method:** Trace production d1/d2 at each pathway and compare every wavelength and k against independent arrays.
- **Input data:** Existing Demo23D inputs and Demo26 extended artifacts
- **Result:** Maximum error 0.0 eV
- **Status:** PASS
- **Improved paper agreement?:** N/A
- **Quantitative evidence / file:** DIRECT_ENGINE_DENOMINATOR_COMPARISON.csv; 16 pathways, 1451 wavelengths, 301 k points, both denominators
- **Physics interpretation:** This replaces the previous finiteness-only denominator evidence with a numerical comparison.
- **Reason it worked or failed:** This replaces the previous finiteness-only denominator evidence with a numerical comparison.
- **Hypothesis remains plausible?:** NO
- **Requires new Pro data?:** NO

### TEST 120 — Final complex comparison

- **Question:** Do final spectra agree with each other and preserved CSV?
- **Method:** Compare full complex arrays.
- **Input data:** Existing Demo23D inputs and Demo26 extended artifacts
- **Result:** Live engines 8.765e-13; stored CSV 5.326e-10 pm/V
- **Status:** PASS
- **Improved paper agreement?:** N/A
- **Quantitative evidence / file:** engine_verification.json
- **Physics interpretation:** Roundoff-scale differences cannot explain spectral mismatch.
- **Reason it worked or failed:** Roundoff-scale differences cannot explain spectral mismatch.
- **Hypothesis remains plausible?:** NO
- **Requires new Pro data?:** NO

### TEST 121 — Literal printed Eq2

- **Question:** Are printed indices, signs, conjugates and permutation implemented?
- **Method:** Inspect local source PDF equation, production and independent source.
- **Input data:** Existing Demo23D inputs and Demo26 extended artifacts
- **Result:** Independent matches bra/ket expression; production omits conjugation for complex inputs; real baseline unaffected.
- **Status:** INCONCLUSIVE
- **Improved paper agreement?:** N/A
- **Quantitative evidence / file:** EQ2_LITERAL_AUDIT.md
- **Physics interpretation:** Do not extend real-input agreement to general complex matrices.
- **Reason it worked or failed:** Do not extend real-input agreement to general complex matrices.
- **Hypothesis remains plausible?:** YES
- **Requires new Pro data?:** NO

### TEST 122 — All scalar sign combinations

- **Question:** Are arbitrary real wavefunction signs irrelevant?
- **Method:** Reuse 16-combination table; re-run original sign gate.
- **Input data:** Existing Demo23D inputs and Demo26 extended artifacts
- **Result:** All 16 combinations give zero change in saved audit.
- **Status:** PASS
- **Improved paper agreement?:** N/A
- **Quantitative evidence / file:** ../EXTENDED_IMPLEMENTATION_AUDIT/WAVEFUNCTION_GAUGE_INVARIANCE.csv
- **Physics interpretation:** Real sign invariance is necessary but weaker than continuous complex phase invariance.
- **Reason it worked or failed:** Real sign invariance is necessary but weaker than continuous complex phase invariance.
- **Hypothesis remains plausible?:** NO
- **Requires new Pro data?:** NO

### TEST 123 — Continuous complex gauge production

- **Question:** Can production accept arbitrary complex wavefunction phases?
- **Method:** Transform O, ze, zh consistently for five phase vectors; execute production.
- **Input data:** Existing Demo23D inputs and Demo26 extended artifacts
- **Result:** Maximum magnitude change 4.51817 pm/V
- **Status:** FAIL
- **Improved paper agreement?:** N/A
- **Quantitative evidence / file:** CONTINUOUS_COMPLEX_GAUGE_AUDIT.csv
- **Physics interpretation:** Confirmed latent conjugation bug. It cannot explain current real frozen inputs; do not use this adapter with arbitrary complex inputs unchanged.
- **Reason it worked or failed:** Confirmed latent conjugation bug. It cannot explain current real frozen inputs; do not use this adapter with arbitrary complex inputs unchanged.
- **Hypothesis remains plausible?:** YES
- **Requires new Pro data?:** NO

### TEST 124 — Continuous complex gauge independent

- **Question:** Does the conjugated independent engine pass complex gauge checks?
- **Method:** Use the same five phase transformations.
- **Input data:** Existing Demo23D inputs and Demo26 extended artifacts
- **Result:** Max change 4.58286e-13 pm/V
- **Status:** PASS
- **Improved paper agreement?:** N/A
- **Quantitative evidence / file:** CONTINUOUS_COMPLEX_GAUGE_AUDIT.csv
- **Physics interpretation:** The audit uses this engine for matrix variants; production source preserved.
- **Reason it worked or failed:** The audit uses this engine for matrix variants; production source preserved.
- **Hypothesis remains plausible?:** NO
- **Requires new Pro data?:** NO

### TEST 125 — Coordinate origin

- **Question:** Does translating z change susceptibility?
- **Method:** Reuse shifts -15,-5,0,+5,+15 nm and rerun original gate.
- **Input data:** Existing Demo23D inputs and Demo26 extended artifacts
- **Result:** Maximum 1.62e-12 pm/V; relative 1.98e-14.
- **Status:** PASS
- **Improved paper agreement?:** N/A
- **Quantitative evidence / file:** ../EXTENDED_IMPLEMENTATION_AUDIT/Z_ORIGIN_INVARIANCE.csv
- **Physics interpretation:** Identity shifts cancel in the orthonormal frozen scalar formulation. This does not prove dominant-component projected states form an orthonormal basis.
- **Reason it worked or failed:** Identity shifts cancel in the orthonormal frozen scalar formulation. This does not prove dominant-component projected states form an orthonormal basis.
- **Hypothesis remains plausible?:** NO
- **Requires new Pro data?:** NO

### TEST 126 — Time convention

- **Question:** Does reversing iGamma conjugate chi without changing magnitude?
- **Method:** Reuse +/-Gamma table and re-run original gate.
- **Input data:** Existing Demo23D inputs and Demo26 extended artifacts
- **Result:** Expected conjugation and magnitude invariance pass.
- **Status:** PASS
- **Improved paper agreement?:** N/A
- **Quantitative evidence / file:** ../EXTENDED_IMPLEMENTATION_AUDIT/IGAMMA_TIME_CONVENTION.csv
- **Physics interpretation:** Consistent time-convention reversal cannot fix magnitude shape.
- **Reason it worked or failed:** Consistent time-convention reversal cannot fix magnitude shape.
- **Hypothesis remains plausible?:** NO
- **Requires new Pro data?:** NO

### TEST 127 — Global phase scan

- **Question:** Can global complex phase improve projected real shape?
- **Method:** Reuse full 0-360-degree signed/absolute-real scan.
- **Input data:** Existing Demo23D inputs and Demo26 extended artifacts
- **Result:** Best abs_Re phase 161 degrees RMSE 0.22969981149055052
- **Status:** FAIL
- **Improved paper agreement?:** YES
- **Quantitative evidence / file:** ../EXTENDED_IMPLEMENTATION_AUDIT/GLOBAL_PHASE_DIAGNOSTIC.csv
- **Physics interpretation:** Fitted projection can improve error but cannot explain a magnitude-labeled curve.
- **Reason it worked or failed:** Fitted projection can improve error but cannot explain a magnitude-labeled curve.
- **Hypothesis remains plausible?:** NO
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.22969981149055052}
```

### TEST 128 — Units and dimensional normalization

- **Question:** Are denominator units and overall susceptibility units consistent?
- **Method:** Audit eV/meV, hc/lambda, angular frequency, nm/m, radial measure and density prefactor.
- **Input data:** Existing Demo23D inputs and Demo26 extended artifacts
- **Result:** Denominator conversions consistent; paper-version Nz prose ambiguous for absolute normalization.
- **Status:** INCONCLUSIVE
- **Improved paper agreement?:** N/A
- **Quantitative evidence / file:** UNITS_AUDIT.md
- **Physics interpretation:** Overall factors disappear after normalization; paper-version ambiguity matters for absolute response, not baseline normalized mismatch.
- **Reason it worked or failed:** Overall factors disappear after normalization; paper-version ambiguity matters for absolute response, not baseline normalized mismatch.
- **Hypothesis remains plausible?:** YES
- **Requires new Pro data?:** NO

### TEST 129 — 2.296eV resonance inference

- **Question:** Do 540/1080 extrema prove one missing state?
- **Method:** Reassess explicit paper assignment, approximate digitization and interference.
- **Input data:** Existing Demo23D inputs and Demo26 extended artifacts
- **Result:** Weak as a unique assignment; plausible energy-only clue, not invalid arithmetic.
- **Status:** INCONCLUSIVE
- **Improved paper agreement?:** N/A
- **Quantitative evidence / file:** EQ2_LITERAL_AUDIT.md; ../EXTENDED_IMPLEMENTATION_AUDIT/P1_P3_2296EV_REASSESSMENT.md
- **Physics interpretation:** Coherent extrema need not equal poles. No author assignment of both peaks to one transition.
- **Reason it worked or failed:** Coherent extrema need not equal poles. No author assignment of both peaks to one transition.
- **Hypothesis remains plausible?:** YES
- **Requires new Pro data?:** NO

### TEST 130 — Original artifact hashes

- **Question:** Were Demo23/24/original26 preserved?
- **Method:** Reconstruct original filtered fingerprints; added audit files excluded.
- **Input data:** Existing Demo23D inputs and Demo26 extended artifacts
- **Result:** True
- **Status:** PASS
- **Improved paper agreement?:** N/A
- **Quantitative evidence / file:** ORIGINAL_ARTIFACT_PRESERVATION.csv
- **Physics interpretation:** Additive audit does not overwrite previous results.
- **Reason it worked or failed:** Additive audit does not overwrite previous results.
- **Hypothesis remains plausible?:** NO
- **Requires new Pro data?:** NO

### TEST 131 — No solver execution

- **Question:** Was the audit restricted to existing outputs?
- **Method:** Read audit source and invoked commands; numerical modules load CSV/raw arrays only.
- **Input data:** Existing Demo23D inputs and Demo26 extended artifacts
- **Result:** Only Python postprocessing and read-only inspections were run.
- **Status:** PASS
- **Improved paper agreement?:** N/A
- **Quantitative evidence / file:** verify_home_engines.py; numerical_home_audit.py; verification log
- **Physics interpretation:** No new eigenstates or solver output generated.
- **Reason it worked or failed:** No new eigenstates or solver output generated.
- **Hypothesis remains plausible?:** NO
- **Requires new Pro data?:** NO

### TEST 132 — HWHM versus FWHM

- **Question:** Could quoted 5 meV represent FWHM?
- **Method:** Compare denominator Gamma=2.5 versus5 meV in saved gamma sweep.
- **Input data:** Existing Demo23D inputs and Demo26 extended artifacts
- **Result:** Magnitude RMSE0.257014 versus0.262391; no recovered full topology.
- **Status:** INCONCLUSIVE
- **Improved paper agreement?:** N/A
- **Quantitative evidence / file:** EXISTING_REUSABLE_DATA_INVENTORY.md; EXISTING_RAW_DATA_INVENTORY.json
- **Physics interpretation:** A factor two changes width but does not explain missing peaks.
- **Reason it worked or failed:** A factor two changes width but does not explain missing peaks.
- **Hypothesis remains plausible?:** YES
- **Requires new Pro data?:** NO

### TEST 133 — BZ definition

- **Question:** Is pi/a the paper BZ radius?
- **Method:** Read printed statement and FCC lattice geometry.
- **Input data:** Existing Demo23D inputs and Demo26 extended artifacts
- **Result:** Gamma-X is2pi/a; phrase0.1BZ does not uniquely identify integration bounds.
- **Status:** INCONCLUSIVE
- **Improved paper agreement?:** N/A
- **Quantitative evidence / file:** EXISTING_REUSABLE_DATA_INVENTORY.md; EXISTING_RAW_DATA_INVENTORY.json
- **Physics interpretation:** Different radius remains plausible; exact author/friend convention needed.
- **Reason it worked or failed:** Different radius remains plausible; exact author/friend convention needed.
- **Hypothesis remains plausible?:** YES
- **Requires new Pro data?:** NO

### TEST 134 — 0.20pi/a candidate

- **Question:** Can the alternative cutoff be tested from available output?
- **Method:** Search every raw dispersion tree.
- **Input data:** Existing Demo23D inputs and Demo26 extended artifacts
- **Result:** Largest available cutoff0.125pi/a, not0.20.
- **Status:** NOT TESTABLE
- **Improved paper agreement?:** N/A
- **Quantitative evidence / file:** EXISTING_REUSABLE_DATA_INVENTORY.md; EXISTING_RAW_DATA_INVENTORY.json
- **Physics interpretation:** No extrapolation permitted; request missing output or new same-geometry solve.
- **Reason it worked or failed:** No extrapolation permitted; request missing output or new same-geometry solve.
- **Hypothesis remains plausible?:** YES
- **Requires new Pro data?:** YES

### TEST 135 — Matrix reconstruction provenance

- **Question:** Are scalar and projected kp8 matrices physically equivalent?
- **Method:** Compare raw projected branch audit with frozen scalar values.
- **Input data:** Existing Demo23D inputs and Demo26 extended artifacts
- **Result:** O12 differs0.01540 to0.99895; hole z12 differs1.4324 to12.5114nm.
- **Status:** INCONCLUSIVE
- **Improved paper agreement?:** N/A
- **Quantitative evidence / file:** EXISTING_REUSABLE_DATA_INVENTORY.md; EXISTING_RAW_DATA_INVENTORY.json
- **Physics interpretation:** Different component/state constructions: discrepancy is not proof of a same-method integration error.
- **Reason it worked or failed:** Different component/state constructions: discrepancy is not proof of a same-method integration error.
- **Hypothesis remains plausible?:** YES
- **Requires new Pro data?:** NO

### TEST 136 — Raw state character

- **Question:** Is tracked hh2 heavy-hole-like?
- **Method:** Read k0 raw spinor weights and adjacent-pair means.
- **Input data:** Existing Demo23D inputs and Demo26 extended artifacts
- **Result:** hh2 has0%HH and97.5757%LH; alternate pair1+2 is100%HH.
- **Status:** FAIL
- **Improved paper agreement?:** N/A
- **Quantitative evidence / file:** EXISTING_REUSABLE_DATA_INVENTORY.md; EXISTING_RAW_DATA_INVENTORY.json
- **Physics interpretation:** The baseline label is not supported by k0 character. Matrix and energy sources must be reconciled.
- **Reason it worked or failed:** The baseline label is not supported by k0 character. Matrix and energy sources must be reconciled.
- **Hypothesis remains plausible?:** YES
- **Requires new Pro data?:** NO

### TEST 137 — Finite-k character tracking

- **Question:** Can state identity be certified through avoided crossings?
- **Method:** Search nonzero-k spinors/envelopes; inspect fixed energy columns.
- **Input data:** Existing Demo23D inputs and Demo26 extended artifacts
- **Result:** Energy columns exist; nonzero-k character/overlap exports absent.
- **Status:** NOT TESTABLE
- **Improved paper agreement?:** N/A
- **Quantitative evidence / file:** EXISTING_REUSABLE_DATA_INVENTORY.md; EXISTING_RAW_DATA_INVENTORY.json
- **Physics interpretation:** Energy continuity is not wavefunction continuity. Export finite-k characters or overlaps.
- **Reason it worked or failed:** Energy continuity is not wavefunction continuity. Export finite-k characters or overlaps.
- **Hypothesis remains plausible?:** YES
- **Requires new Pro data?:** YES

### TEST 138 — Exact structure match

- **Question:** Is Demo23 the exact paper ideal structure?
- **Method:** Compare actual ternary_linear layers with ideal paper and table metadata.
- **Input data:** Existing Demo23D inputs and Demo26 extended artifacts
- **Result:** Demo23 has1nm grading; ideal paper appears abrupt.
- **Status:** FAIL
- **Improved paper agreement?:** N/A
- **Quantitative evidence / file:** EXISTING_REUSABLE_DATA_INVENTORY.md; EXISTING_RAW_DATA_INVENTORY.json
- **Physics interpretation:** Geometry mismatch established at interfaces; causality of missing features is not established.
- **Reason it worked or failed:** Geometry mismatch established at interfaces; causality of missing features is not established.
- **Hypothesis remains plausible?:** YES
- **Requires new Pro data?:** NO

### TEST 139 — Equivalent abrupt kp8

- **Question:** Does an already-run matching abrupt kp8 result exist?
- **Method:** Search Demo19-26, raw and fixtures.
- **Input data:** Existing Demo23D inputs and Demo26 extended artifacts
- **Result:** Abrupt scalar and coarse Free fixtures exist; matching converged abrupt kp8 dispersion absent.
- **Status:** NOT TESTABLE
- **Improved paper agreement?:** N/A
- **Quantitative evidence / file:** EXISTING_REUSABLE_DATA_INVENTORY.md; EXISTING_RAW_DATA_INVENTORY.json
- **Physics interpretation:** Scalar diagnostic is available separately, but exact abrupt E(k) needs new output.
- **Reason it worked or failed:** Scalar diagnostic is available separately, but exact abrupt E(k) needs new output.
- **Hypothesis remains plausible?:** YES
- **Requires new Pro data?:** YES

### TEST 140 — Poisson setup match

- **Question:** Is production demonstrably paper-equivalent self-consistent Poisson?
- **Method:** Inspect run block, density flags, charge output and fixture provenance.
- **Input data:** Existing Demo23D inputs and Demo26 extended artifacts
- **Result:** run quantum only, no Poisson loop; nonzero hole charge output means zero fixed charge is not zero occupation.
- **Status:** INCONCLUSIVE
- **Improved paper agreement?:** N/A
- **Quantitative evidence / file:** EXISTING_REUSABLE_DATA_INVENTORY.md; EXISTING_RAW_DATA_INVENTORY.json
- **Physics interpretation:** Paper/friend electrostatics and carrier conditions unspecified.
- **Reason it worked or failed:** Paper/friend electrostatics and carrier conditions unspecified.
- **Hypothesis remains plausible?:** YES
- **Requires new Pro data?:** NO

### TEST 141 — Matching Poisson alternative

- **Question:** Can a matching self-consistent spectrum be reused?
- **Method:** Search completed Poisson raw results.
- **Input data:** Existing Demo23D inputs and Demo26 extended artifacts
- **Result:** Different coarse doped fixture exists; matching converged paper-geometry Poisson absent.
- **Status:** NOT TESTABLE
- **Improved paper agreement?:** N/A
- **Quantitative evidence / file:** EXISTING_REUSABLE_DATA_INVENTORY.md; EXISTING_RAW_DATA_INVENTORY.json
- **Physics interpretation:** Need exact electrostatic conditions first, then matching solve if files unavailable.
- **Reason it worked or failed:** Need exact electrostatic conditions first, then matching solve if files unavailable.
- **Hypothesis remains plausible?:** YES
- **Requires new Pro data?:** YES

### TEST 142 — Finite-k matrix physics

- **Question:** Can physical M(k) replace M(0) using available files?
- **Method:** Search all seven raw datasets for nonzero-k envelope/matrix exports.
- **Input data:** Existing Demo23D inputs and Demo26 extended artifacts
- **Result:** Only k00000 matrices/envelopes found.
- **Status:** NOT TESTABLE
- **Improved paper agreement?:** N/A
- **Quantitative evidence / file:** EXISTING_REUSABLE_DATA_INVENTORY.md; EXISTING_RAW_DATA_INVENTORY.json
- **Physics interpretation:** No fabricated matrices; finite-k physics useful but necessity for paper reproduction unproved.
- **Reason it worked or failed:** No fabricated matrices; finite-k physics useful but necessity for paper reproduction unproved.
- **Hypothesis remains plausible?:** YES
- **Requires new Pro data?:** YES

### TEST 143 — Temperature or database changes

- **Question:** Can a different temperature/material database be solved from current data?
- **Method:** Search alternate run provenance.
- **Input data:** Existing Demo23D inputs and Demo26 extended artifacts
- **Result:** No certified same-geometry controlled alternate temperature/database eigenstates.
- **Status:** NOT TESTABLE
- **Improved paper agreement?:** N/A
- **Quantitative evidence / file:** EXISTING_REUSABLE_DATA_INVENTORY.md; EXISTING_RAW_DATA_INVENTORY.json
- **Physics interpretation:** Friend version/database can settle settings; changed eigenstates require output.
- **Reason it worked or failed:** Friend version/database can settle settings; changed eigenstates require output.
- **Hypothesis remains plausible?:** YES
- **Requires new Pro data?:** YES

### TEST 144 — Exact zero and digitization robustness

- **Question:** Do digitized baseline contacts prove exact chi zeros?
- **Method:** Inspect nonnegative45point simulation trace and interpolation spread.
- **Input data:** Existing Demo23D inputs and Demo26 extended artifacts
- **Result:** No signed or author uncertainty information; exact zeros not established.
- **Status:** INCONCLUSIVE
- **Improved paper agreement?:** N/A
- **Quantitative evidence / file:** EXISTING_REUSABLE_DATA_INVENTORY.md; EXISTING_RAW_DATA_INVENTORY.json
- **Physics interpretation:** Use apparent deep minima, not exact analytic nodes. No experimental error bars invented.
- **Reason it worked or failed:** Use apparent deep minima, not exact analytic nodes. No experimental error bars invented.
- **Hypothesis remains plausible?:** YES
- **Requires new Pro data?:** NO

### TEST 145 — Topology versus fit

- **Question:** Can lower RMSE alone establish reproduction?
- **Method:** Require genuine interior extrema in separate target windows; inspect full ordered extrema and local prominence.
- **Input data:** Existing Demo23D inputs and Demo26 extended artifacts
- **Result:** Baseline P1/P3 and Z1/Z2 strict extrema absent; P2=752,P4=1503nm.
- **Status:** PASS
- **Improved paper agreement?:** N/A
- **Quantitative evidence / file:** EXISTING_REUSABLE_DATA_INVENTORY.md; EXISTING_RAW_DATA_INVENTORY.json
- **Physics interpretation:** Numerical best fits still require physical validity and matching topology.
- **Reason it worked or failed:** Numerical best fits still require physical validity and matching topology.
- **Hypothesis remains plausible?:** NO
- **Requires new Pro data?:** NO

### TEST 146 — consistent scalar Abrupt reference production

- **Question:** Can this existing-data alternative explain the discrepancy?
- **Method:** Same-case scalar energies and matrices; parabolic me=.067, mhh=.112 m0 from Demo20; k cutoff retained for matched comparison.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** method-limited diagnostic; paper reproduction not established
- **Status:** INCONCLUSIVE
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"source": "C:\\code\\nonlinear_photonics\\demo_results\\demo19\\tables\\demo19_master_results.csv", "case_id": "00", "source_physical_valid": "False", "source_failure": "Demo 11/14 physical QC did not pass", "geometry": "Abrupt reference", "mass_reference": "Demo21 demo20_math_physics_reference.py lines375-390"}
- **Physics interpretation:** No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- **Reason it worked or failed:** Changes in poles and numerator cancellation
- **Hypothesis remains plausible?:** YES
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.2799316178610753, "correlation": 0.18851315000978097, "P1_nm": null, "P1_local_RMSE": 0.16679370126230117, "Z1_nm": null, "Z1_local_RMSE": 0.12719113632663298, "P2_nm": 759.0, "P2_local_RMSE": 0.11064252539255333, "P3_nm": null, "P3_local_RMSE": 0.3606877241003134, "Z2_nm": null, "Z2_local_RMSE": 0.6153296013894644, "P4_nm": 1517.0, "P4_local_RMSE": 0.19360279340949996, "all_peaks_nm": "649.0;698.0;759.0;839.0;1298.0;1517.0", "all_minima_nm": "690.0;703.0;834.0;933.0;1407.0", "topology_json": "[{\"nm\": 649.0, \"local_prominence\": 0.10262534477935542, \"half_prominence_width_nm\": 10.0}, {\"nm\": 698.0, \"local_prominence\": 0.0023599884555706163, \"half_prominence_width_nm\": 7.0}, {\"nm\": 759.0, \"local_prominence\": 0.21225699944434379, \"half_prominence_width_nm\": 18.0}, {\"nm\": 839.0, \"local_prominence\": 0.0006509539958012844, \"half_prominence_width_nm\": 8.0}, {\"nm\": 1298.0, \"local_prominence\": 0.3022822218599537, \"half_prominence_width_nm\": 23.0}, {\"nm\": 1517.0, \"local_prominence\": 0.3301615782738465, \"half_prominence_width_nm\": 29.0}]"}
```

### TEST 147 — consistent scalar Abrupt reference k0_only

- **Question:** Can this existing-data alternative explain the discrepancy?
- **Method:** Same-case scalar energies and matrices; parabolic me=.067, mhh=.112 m0 from Demo20; k cutoff retained for matched comparison.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** method-limited diagnostic; paper reproduction not established
- **Status:** INCONCLUSIVE
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"source": "C:\\code\\nonlinear_photonics\\demo_results\\demo19\\tables\\demo19_master_results.csv", "case_id": "00", "source_physical_valid": "False", "source_failure": "Demo 11/14 physical QC did not pass", "geometry": "Abrupt reference", "mass_reference": "Demo21 demo20_math_physics_reference.py lines375-390"}
- **Physics interpretation:** No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- **Reason it worked or failed:** Changes in poles and numerator cancellation
- **Hypothesis remains plausible?:** YES
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.28291843600711225, "correlation": 0.6040358265512747, "P1_nm": null, "P1_local_RMSE": 0.19847560217763663, "Z1_nm": null, "Z1_local_RMSE": 0.04824442149896626, "P2_nm": 760.0, "P2_local_RMSE": 0.327434963946918, "P3_nm": null, "P3_local_RMSE": 0.5074764889939425, "Z2_nm": null, "Z2_local_RMSE": 0.08197343816423058, "P4_nm": 1519.0, "P4_local_RMSE": 0.35477624123709023, "all_peaks_nm": "760.0;811.0;831.0;857.0;1519.0;1623.0;1661.0;1699.0", "all_minima_nm": "808.0;818.0;837.0;1005.0;1616.0;1636.0;1674.0", "topology_json": "[{\"nm\": 760.0, \"local_prominence\": 0.45416019204452174, \"half_prominence_width_nm\": 9.0}, {\"nm\": 811.0, \"local_prominence\": 0.00022321235957006164, \"half_prominence_width_nm\": 3.0}, {\"nm\": 831.0, \"local_prominence\": 0.008741494474281616, \"half_prominence_width_nm\": 7.0}, {\"nm\": 857.0, \"local_prominence\": 0.0028155223325285472, \"half_prominence_width_nm\": 59.0}, {\"nm\": 1519.0, \"local_prominence\": 0.9409944221896026, \"half_prominence_width_nm\": 16.0}, {\"nm\": 1623.0, \"local_prominence\": 0.0010460621814045445, \"half_prominence_width_nm\": 6.0}, {\"nm\": 1661.0, \"local_prominence\": 0.010271613683316007, \"half_prominence_width_nm\": 14.0}, {\"nm\": 1699.0, \"local_prominence\": 0.0030303573340591666, \"half_prominence_width_nm\": 54.0}]"}
```

### TEST 148 — consistent scalar Linear 0.2 nm production

- **Question:** Can this existing-data alternative explain the discrepancy?
- **Method:** Same-case scalar energies and matrices; parabolic me=.067, mhh=.112 m0 from Demo20; k cutoff retained for matched comparison.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** method-limited diagnostic; paper reproduction not established
- **Status:** INCONCLUSIVE
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"source": "C:\\code\\nonlinear_photonics\\demo_results\\demo19\\tables\\demo19_master_results.csv", "case_id": "01", "source_physical_valid": "False", "source_failure": "Demo 11/14 physical QC did not pass", "geometry": "Linear 0.2 nm", "mass_reference": "Demo21 demo20_math_physics_reference.py lines375-390"}
- **Physics interpretation:** No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- **Reason it worked or failed:** Changes in poles and numerator cancellation
- **Hypothesis remains plausible?:** YES
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.2810891459847216, "correlation": 0.18104448968627626, "P1_nm": null, "P1_local_RMSE": 0.1666213284253091, "Z1_nm": null, "Z1_local_RMSE": 0.13117215109749317, "P2_nm": 758.0, "P2_local_RMSE": 0.11345261266697529, "P3_nm": null, "P3_local_RMSE": 0.3604508021051539, "Z2_nm": null, "Z2_local_RMSE": 0.6166211652722686, "P4_nm": 1515.0, "P4_local_RMSE": 0.20100912949679292, "all_peaks_nm": "649.0;698.0;758.0;839.0;1297.0;1515.0", "all_minima_nm": "690.0;703.0;834.0;932.0;1407.0", "topology_json": "[{\"nm\": 649.0, \"local_prominence\": 0.10063741525585879, \"half_prominence_width_nm\": 9.0}, {\"nm\": 698.0, \"local_prominence\": 0.002586305437935088, \"half_prominence_width_nm\": 7.0}, {\"nm\": 758.0, \"local_prominence\": 0.21255290807147903, \"half_prominence_width_nm\": 17.0}, {\"nm\": 839.0, \"local_prominence\": 0.0006999609761492442, \"half_prominence_width_nm\": 8.0}, {\"nm\": 1297.0, \"local_prominence\": 0.3016481420591929, \"half_prominence_width_nm\": 24.0}, {\"nm\": 1515.0, \"local_prominence\": 0.3297827835075946, \"half_prominence_width_nm\": 29.0}]"}
```

### TEST 149 — consistent scalar Linear 0.2 nm k0_only

- **Question:** Can this existing-data alternative explain the discrepancy?
- **Method:** Same-case scalar energies and matrices; parabolic me=.067, mhh=.112 m0 from Demo20; k cutoff retained for matched comparison.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** method-limited diagnostic; paper reproduction not established
- **Status:** INCONCLUSIVE
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"source": "C:\\code\\nonlinear_photonics\\demo_results\\demo19\\tables\\demo19_master_results.csv", "case_id": "01", "source_physical_valid": "False", "source_failure": "Demo 11/14 physical QC did not pass", "geometry": "Linear 0.2 nm", "mass_reference": "Demo21 demo20_math_physics_reference.py lines375-390"}
- **Physics interpretation:** No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- **Reason it worked or failed:** Changes in poles and numerator cancellation
- **Hypothesis remains plausible?:** YES
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.28313359670591953, "correlation": 0.5991447446265149, "P1_nm": null, "P1_local_RMSE": 0.1984604447806438, "Z1_nm": null, "Z1_local_RMSE": 0.04819979604164657, "P2_nm": 759.0, "P2_local_RMSE": 0.3272276406379354, "P3_nm": null, "P3_local_RMSE": 0.5074326815115463, "Z2_nm": null, "Z2_local_RMSE": 0.08179237788878617, "P4_nm": 1517.0, "P4_local_RMSE": 0.35654845110232763, "all_peaks_nm": "759.0;811.0;830.0;857.0;1517.0;1623.0;1660.0;1698.0", "all_minima_nm": "808.0;817.0;837.0;1003.0;1615.0;1635.0;1674.0", "topology_json": "[{\"nm\": 759.0, \"local_prominence\": 0.4619940488409092, \"half_prominence_width_nm\": 8.0}, {\"nm\": 811.0, \"local_prominence\": 0.0002789292341836905, \"half_prominence_width_nm\": 3.0}, {\"nm\": 830.0, \"local_prominence\": 0.008833728029372764, \"half_prominence_width_nm\": 7.0}, {\"nm\": 857.0, \"local_prominence\": 0.002739410183384125, \"half_prominence_width_nm\": 59.0}, {\"nm\": 1517.0, \"local_prominence\": 0.9415496084570749, \"half_prominence_width_nm\": 16.0}, {\"nm\": 1623.0, \"local_prominence\": 0.0011173970812602546, \"half_prominence_width_nm\": 6.0}, {\"nm\": 1660.0, \"local_prominence\": 0.010258470571568624, \"half_prominence_width_nm\": 14.0}, {\"nm\": 1698.0, \"local_prominence\": 0.0030428386975475744, \"half_prominence_width_nm\": 55.0}]"}
```

### TEST 150 — consistent scalar Linear 0.4 nm production

- **Question:** Can this existing-data alternative explain the discrepancy?
- **Method:** Same-case scalar energies and matrices; parabolic me=.067, mhh=.112 m0 from Demo20; k cutoff retained for matched comparison.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** method-limited diagnostic; paper reproduction not established
- **Status:** INCONCLUSIVE
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"source": "C:\\code\\nonlinear_photonics\\demo_results\\demo19\\tables\\demo19_master_results.csv", "case_id": "02", "source_physical_valid": "False", "source_failure": "Demo 11/14 physical QC did not pass", "geometry": "Linear 0.4 nm", "mass_reference": "Demo21 demo20_math_physics_reference.py lines375-390"}
- **Physics interpretation:** No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- **Reason it worked or failed:** Changes in poles and numerator cancellation
- **Hypothesis remains plausible?:** YES
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.28272548330335706, "correlation": 0.1698030329473754, "P1_nm": null, "P1_local_RMSE": 0.16639827532980145, "Z1_nm": null, "Z1_local_RMSE": 0.13637592608901802, "P2_nm": 757.0, "P2_local_RMSE": 0.11766341705945638, "P3_nm": null, "P3_local_RMSE": 0.3602722409691857, "Z2_nm": null, "Z2_local_RMSE": 0.6180134082643334, "P4_nm": 1513.0, "P4_local_RMSE": 0.21196613674282586, "all_peaks_nm": "648.0;698.0;757.0;839.0;1295.0;1513.0", "all_minima_nm": "689.0;702.0;833.0;930.0;1406.0", "topology_json": "[{\"nm\": 648.0, \"local_prominence\": 0.10153702642153684, \"half_prominence_width_nm\": 9.0}, {\"nm\": 698.0, \"local_prominence\": 0.00292745166715197, \"half_prominence_width_nm\": 8.0}, {\"nm\": 757.0, \"local_prominence\": 0.21133169335939128, \"half_prominence_width_nm\": 17.0}, {\"nm\": 839.0, \"local_prominence\": 0.0009091289184711693, \"half_prominence_width_nm\": 9.0}, {\"nm\": 1295.0, \"local_prominence\": 0.30226645897603843, \"half_prominence_width_nm\": 23.0}, {\"nm\": 1513.0, \"local_prominence\": 0.32985982451970397, \"half_prominence_width_nm\": 29.0}]"}
```

### TEST 151 — consistent scalar Linear 0.4 nm k0_only

- **Question:** Can this existing-data alternative explain the discrepancy?
- **Method:** Same-case scalar energies and matrices; parabolic me=.067, mhh=.112 m0 from Demo20; k cutoff retained for matched comparison.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** method-limited diagnostic; paper reproduction not established
- **Status:** INCONCLUSIVE
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"source": "C:\\code\\nonlinear_photonics\\demo_results\\demo19\\tables\\demo19_master_results.csv", "case_id": "02", "source_physical_valid": "False", "source_failure": "Demo 11/14 physical QC did not pass", "geometry": "Linear 0.4 nm", "mass_reference": "Demo21 demo20_math_physics_reference.py lines375-390"}
- **Physics interpretation:** No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- **Reason it worked or failed:** Changes in poles and numerator cancellation
- **Hypothesis remains plausible?:** YES
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.28412959099840224, "correlation": 0.5882477646247567, "P1_nm": null, "P1_local_RMSE": 0.19845941851506904, "Z1_nm": null, "Z1_local_RMSE": 0.0481805337982178, "P2_nm": 758.0, "P2_local_RMSE": 0.32781653916329795, "P3_nm": null, "P3_local_RMSE": 0.5075064715099615, "Z2_nm": null, "Z2_local_RMSE": 0.08173134355806279, "P4_nm": 1515.0, "P4_local_RMSE": 0.36252615445436037, "all_peaks_nm": "758.0;811.0;830.0;857.0;1515.0;1622.0;1660.0;1698.0", "all_minima_nm": "807.0;817.0;837.0;1001.0;1614.0;1635.0;1673.0", "topology_json": "[{\"nm\": 758.0, \"local_prominence\": 0.4557005505134621, \"half_prominence_width_nm\": 9.0}, {\"nm\": 811.0, \"local_prominence\": 0.0003307546901032063, \"half_prominence_width_nm\": 3.0}, {\"nm\": 830.0, \"local_prominence\": 0.009430446399377408, \"half_prominence_width_nm\": 7.0}, {\"nm\": 857.0, \"local_prominence\": 0.002561858294410937, \"half_prominence_width_nm\": 58.0}, {\"nm\": 1515.0, \"local_prominence\": 0.9427857802958045, \"half_prominence_width_nm\": 16.0}, {\"nm\": 1622.0, \"local_prominence\": 0.0012422302904558369, \"half_prominence_width_nm\": 6.0}, {\"nm\": 1660.0, \"local_prominence\": 0.010492133508385834, \"half_prominence_width_nm\": 14.0}, {\"nm\": 1698.0, \"local_prominence\": 0.003095102145174212, \"half_prominence_width_nm\": 56.0}]"}
```

### TEST 152 — consistent scalar Linear 0.7 nm production

- **Question:** Can this existing-data alternative explain the discrepancy?
- **Method:** Same-case scalar energies and matrices; parabolic me=.067, mhh=.112 m0 from Demo20; k cutoff retained for matched comparison.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** method-limited diagnostic; paper reproduction not established
- **Status:** INCONCLUSIVE
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"source": "C:\\code\\nonlinear_photonics\\demo_results\\demo19\\tables\\demo19_master_results.csv", "case_id": "03", "source_physical_valid": "False", "source_failure": "Demo 11/14 physical QC did not pass", "geometry": "Linear 0.7 nm", "mass_reference": "Demo21 demo20_math_physics_reference.py lines375-390"}
- **Physics interpretation:** No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- **Reason it worked or failed:** Changes in poles and numerator cancellation
- **Hypothesis remains plausible?:** YES
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.2864211861380991, "correlation": 0.1450445016142571, "P1_nm": null, "P1_local_RMSE": 0.16592078167468718, "Z1_nm": null, "Z1_local_RMSE": 0.1460585134054834, "P2_nm": 754.0, "P2_local_RMSE": 0.12657086729410127, "P3_nm": null, "P3_local_RMSE": 0.35983634731721115, "Z2_nm": null, "Z2_local_RMSE": 0.6210603686978493, "P4_nm": 1508.0, "P4_local_RMSE": 0.23563744793855657, "all_peaks_nm": "646.0;697.0;754.0;840.0;1292.0;1508.0", "all_minima_nm": "688.0;702.0;832.0;926.0;1405.0", "topology_json": "[{\"nm\": 646.0, \"local_prominence\": 0.1024545250181686, \"half_prominence_width_nm\": 9.0}, {\"nm\": 697.0, \"local_prominence\": 0.0032357016762180613, \"half_prominence_width_nm\": 7.0}, {\"nm\": 754.0, \"local_prominence\": 0.21059616064092435, \"half_prominence_width_nm\": 16.0}, {\"nm\": 840.0, \"local_prominence\": 0.0013847394221809806, \"half_prominence_width_nm\": 13.0}, {\"nm\": 1292.0, \"local_prominence\": 0.3017318562052105, \"half_prominence_width_nm\": 23.0}, {\"nm\": 1508.0, \"local_prominence\": 0.329599935158175, \"half_prominence_width_nm\": 28.0}]"}
```

### TEST 153 — consistent scalar Linear 0.7 nm k0_only

- **Question:** Can this existing-data alternative explain the discrepancy?
- **Method:** Same-case scalar energies and matrices; parabolic me=.067, mhh=.112 m0 from Demo20; k cutoff retained for matched comparison.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** method-limited diagnostic; paper reproduction not established
- **Status:** INCONCLUSIVE
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"source": "C:\\code\\nonlinear_photonics\\demo_results\\demo19\\tables\\demo19_master_results.csv", "case_id": "03", "source_physical_valid": "False", "source_failure": "Demo 11/14 physical QC did not pass", "geometry": "Linear 0.7 nm", "mass_reference": "Demo21 demo20_math_physics_reference.py lines375-390"}
- **Physics interpretation:** No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- **Reason it worked or failed:** Changes in poles and numerator cancellation
- **Hypothesis remains plausible?:** YES
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.28630717503155767, "correlation": 0.5560081057745877, "P1_nm": null, "P1_local_RMSE": 0.19843520175386584, "Z1_nm": null, "Z1_local_RMSE": 0.048091120116091436, "P2_nm": 755.0, "P2_local_RMSE": 0.3286537781694563, "P3_nm": null, "P3_local_RMSE": 0.5075185895315594, "Z2_nm": null, "Z2_local_RMSE": 0.08138673518475134, "P4_nm": 1510.0, "P4_local_RMSE": 0.376610920683349, "all_peaks_nm": "755.0;810.0;830.0;858.0;1510.0;1620.0;1659.0;1698.0", "all_minima_nm": "806.0;816.0;836.0;997.0;1611.0;1632.0;1672.0", "topology_json": "[{\"nm\": 755.0, \"local_prominence\": 0.46394195824450624, \"half_prominence_width_nm\": 8.0}, {\"nm\": 810.0, \"local_prominence\": 0.0004502273638329682, \"half_prominence_width_nm\": 3.0}, {\"nm\": 830.0, \"local_prominence\": 0.010274017921323774, \"half_prominence_width_nm\": 7.0}, {\"nm\": 858.0, \"local_prominence\": 0.0022380931881532187, \"half_prominence_width_nm\": 59.0}, {\"nm\": 1510.0, \"local_prominence\": 0.9445638286579181, \"half_prominence_width_nm\": 15.0}, {\"nm\": 1620.0, \"local_prominence\": 0.001444852559511739, \"half_prominence_width_nm\": 6.0}, {\"nm\": 1659.0, \"local_prominence\": 0.01096342996777698, \"half_prominence_width_nm\": 14.0}, {\"nm\": 1698.0, \"local_prominence\": 0.003228831245495733, \"half_prominence_width_nm\": 61.0}]"}
```

### TEST 154 — consistent scalar Linear 1.0 nm production

- **Question:** Can this existing-data alternative explain the discrepancy?
- **Method:** Same-case scalar energies and matrices; parabolic me=.067, mhh=.112 m0 from Demo20; k cutoff retained for matched comparison.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** method-limited diagnostic; paper reproduction not established
- **Status:** INCONCLUSIVE
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"source": "C:\\code\\nonlinear_photonics\\demo_results\\demo19\\tables\\demo19_master_results.csv", "case_id": "04", "source_physical_valid": "False", "source_failure": "Demo 11/14 physical QC did not pass", "geometry": "Linear 1.0 nm", "mass_reference": "Demo21 demo20_math_physics_reference.py lines375-390"}
- **Physics interpretation:** No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- **Reason it worked or failed:** Changes in poles and numerator cancellation
- **Hypothesis remains plausible?:** YES
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.2913604332515152, "correlation": 0.11151253082245843, "P1_nm": null, "P1_local_RMSE": 0.16529232334223762, "Z1_nm": null, "Z1_local_RMSE": 0.15690980882676597, "P2_nm": 751.0, "P2_local_RMSE": 0.13823954873141514, "P3_nm": null, "P3_local_RMSE": 0.3591724927135305, "Z2_nm": 1385.0, "Z2_local_RMSE": 0.6247400791477273, "P4_nm": 1502.0, "P4_local_RMSE": 0.26519070739378875, "all_peaks_nm": "644.0;683.0;697.0;751.0;840.0;1287.0;1389.0;1502.0", "all_minima_nm": "678.0;687.0;701.0;831.0;922.0;1385.0;1403.0", "topology_json": "[{\"nm\": 644.0, \"local_prominence\": 0.10092327695336273, \"half_prominence_width_nm\": 9.0}, {\"nm\": 683.0, \"local_prominence\": 0.0002579943102889448, \"half_prominence_width_nm\": 5.0}, {\"nm\": 697.0, \"local_prominence\": 0.003255817518619475, \"half_prominence_width_nm\": 7.0}, {\"nm\": 751.0, \"local_prominence\": 0.2086939697544568, \"half_prominence_width_nm\": 16.0}, {\"nm\": 840.0, \"local_prominence\": 0.002032236942714455, \"half_prominence_width_nm\": 16.0}, {\"nm\": 1287.0, \"local_prominence\": 0.2959528722741821, \"half_prominence_width_nm\": 22.0}, {\"nm\": 1389.0, \"local_prominence\": 4.634209348663987e-05, \"half_prominence_width_nm\": 5.0}, {\"nm\": 1502.0, \"local_prominence\": 0.3287414201156379, \"half_prominence_width_nm\": 28.0}]"}
```

### TEST 155 — consistent scalar Linear 1.0 nm k0_only

- **Question:** Can this existing-data alternative explain the discrepancy?
- **Method:** Same-case scalar energies and matrices; parabolic me=.067, mhh=.112 m0 from Demo20; k cutoff retained for matched comparison.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** method-limited diagnostic; paper reproduction not established
- **Status:** INCONCLUSIVE
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"source": "C:\\code\\nonlinear_photonics\\demo_results\\demo19\\tables\\demo19_master_results.csv", "case_id": "04", "source_physical_valid": "False", "source_failure": "Demo 11/14 physical QC did not pass", "geometry": "Linear 1.0 nm", "mass_reference": "Demo21 demo20_math_physics_reference.py lines375-390"}
- **Physics interpretation:** No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- **Reason it worked or failed:** Changes in poles and numerator cancellation
- **Hypothesis remains plausible?:** YES
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.28988664386272744, "correlation": 0.5043311312785336, "P1_nm": null, "P1_local_RMSE": 0.19841040871828144, "Z1_nm": null, "Z1_local_RMSE": 0.04798789039226431, "P2_nm": 752.0, "P2_local_RMSE": 0.3306429334023003, "P3_nm": null, "P3_local_RMSE": 0.5075682210109416, "Z2_nm": null, "Z2_local_RMSE": 0.08098068306823923, "P4_nm": 1504.0, "P4_local_RMSE": 0.3986028505805053, "all_peaks_nm": "752.0;808.0;829.0;860.0;1504.0;1617.0;1657.0;1698.0", "all_minima_nm": "804.0;814.0;836.0;992.0;1608.0;1630.0;1670.0", "topology_json": "[{\"nm\": 752.0, \"local_prominence\": 0.46497916459056204, \"half_prominence_width_nm\": 8.0}, {\"nm\": 808.0, \"local_prominence\": 0.0004668311937327044, \"half_prominence_width_nm\": 4.0}, {\"nm\": 829.0, \"local_prominence\": 0.011562604034289846, \"half_prominence_width_nm\": 7.0}, {\"nm\": 860.0, \"local_prominence\": 0.0018883602561490988, \"half_prominence_width_nm\": 59.0}, {\"nm\": 1504.0, \"local_prominence\": 0.9470581743362336, \"half_prominence_width_nm\": 15.0}, {\"nm\": 1617.0, \"local_prominence\": 0.0014939322139093103, \"half_prominence_width_nm\": 7.0}, {\"nm\": 1657.0, \"local_prominence\": 0.011490845148714138, \"half_prominence_width_nm\": 14.0}, {\"nm\": 1698.0, \"local_prominence\": 0.0033744890701438244, \"half_prominence_width_nm\": 67.0}]"}
```

### TEST 156 — consistent scalar Linear 1.4 nm production

- **Question:** Can this existing-data alternative explain the discrepancy?
- **Method:** Same-case scalar energies and matrices; parabolic me=.067, mhh=.112 m0 from Demo20; k cutoff retained for matched comparison.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** method-limited diagnostic; paper reproduction not established
- **Status:** INCONCLUSIVE
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"source": "C:\\code\\nonlinear_photonics\\demo_results\\demo19\\tables\\demo19_master_results.csv", "case_id": "05", "source_physical_valid": "False", "source_failure": "Demo 11/14 physical QC did not pass", "geometry": "Linear 1.4 nm", "mass_reference": "Demo21 demo20_math_physics_reference.py lines375-390"}
- **Physics interpretation:** No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- **Reason it worked or failed:** Changes in poles and numerator cancellation
- **Hypothesis remains plausible?:** YES
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.2991186383255225, "correlation": 0.05763716151931968, "P1_nm": null, "P1_local_RMSE": 0.16423579271043584, "Z1_nm": null, "Z1_local_RMSE": 0.17196449170306413, "P2_nm": 747.0, "P2_local_RMSE": 0.1566672277677808, "P3_nm": null, "P3_local_RMSE": 0.35783496546599003, "Z2_nm": 1376.0, "Z2_local_RMSE": 0.6302536233030838, "P4_nm": 1493.0, "P4_local_RMSE": 0.3057354670189173, "all_peaks_nm": "640.0;682.0;696.0;747.0;841.0;1280.0;1390.0;1493.0", "all_minima_nm": "674.0;685.0;700.0;830.0;915.0;1376.0;1400.0", "topology_json": "[{\"nm\": 640.0, \"local_prominence\": 0.10195975503654015, \"half_prominence_width_nm\": 9.0}, {\"nm\": 682.0, \"local_prominence\": 0.0002216286406960255, \"half_prominence_width_nm\": 3.0}, {\"nm\": 696.0, \"local_prominence\": 0.003040500879102792, \"half_prominence_width_nm\": 6.0}, {\"nm\": 747.0, \"local_prominence\": 0.2041568857344367, \"half_prominence_width_nm\": 16.0}, {\"nm\": 841.0, \"local_prominence\": 0.002939113967686091, \"half_prominence_width_nm\": 23.0}, {\"nm\": 1280.0, \"local_prominence\": 0.296405569788894, \"half_prominence_width_nm\": 22.0}, {\"nm\": 1390.0, \"local_prominence\": 0.0015726296394085182, \"half_prominence_width_nm\": 11.0}, {\"nm\": 1493.0, \"local_prominence\": 0.32604412117365444, \"half_prominence_width_nm\": 27.0}]"}
```

### TEST 157 — consistent scalar Linear 1.4 nm k0_only

- **Question:** Can this existing-data alternative explain the discrepancy?
- **Method:** Same-case scalar energies and matrices; parabolic me=.067, mhh=.112 m0 from Demo20; k cutoff retained for matched comparison.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** method-limited diagnostic; paper reproduction not established
- **Status:** INCONCLUSIVE
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"source": "C:\\code\\nonlinear_photonics\\demo_results\\demo19\\tables\\demo19_master_results.csv", "case_id": "05", "source_physical_valid": "False", "source_failure": "Demo 11/14 physical QC did not pass", "geometry": "Linear 1.4 nm", "mass_reference": "Demo21 demo20_math_physics_reference.py lines375-390"}
- **Physics interpretation:** No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- **Reason it worked or failed:** Changes in poles and numerator cancellation
- **Hypothesis remains plausible?:** YES
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.2958334943339873, "correlation": 0.4177479720034203, "P1_nm": null, "P1_local_RMSE": 0.19837498635347664, "Z1_nm": null, "Z1_local_RMSE": 0.047825698221387644, "P2_nm": 747.0, "P2_local_RMSE": 0.33494131711198705, "P3_nm": null, "P3_local_RMSE": 0.5076625374508742, "Z2_nm": null, "Z2_local_RMSE": 0.08030382267342996, "P4_nm": 1495.0, "P4_local_RMSE": 0.43286867105532495, "all_peaks_nm": "747.0;806.0;827.0;861.0;1495.0;1613.0;1654.0;1697.0", "all_minima_nm": "802.0;812.0;835.0;984.0;1603.0;1625.0;1667.0", "topology_json": "[{\"nm\": 747.0, \"local_prominence\": 0.45750570689931747, \"half_prominence_width_nm\": 9.0}, {\"nm\": 806.0, \"local_prominence\": 0.0004721157161131466, \"half_prominence_width_nm\": 4.0}, {\"nm\": 827.0, \"local_prominence\": 0.012793106003840739, \"half_prominence_width_nm\": 7.0}, {\"nm\": 861.0, \"local_prominence\": 0.0014614128650860918, \"half_prominence_width_nm\": 58.0}, {\"nm\": 1495.0, \"local_prominence\": 0.9510239295465776, \"half_prominence_width_nm\": 16.0}, {\"nm\": 1613.0, \"local_prominence\": 0.0013521253407823633, \"half_prominence_width_nm\": 6.0}, {\"nm\": 1654.0, \"local_prominence\": 0.011962187431957188, \"half_prominence_width_nm\": 14.0}, {\"nm\": 1697.0, \"local_prominence\": 0.0035262909612135806, \"half_prominence_width_nm\": 74.0}]"}
```

### TEST 158 — consistent scalar Asymmetric inner grading A production

- **Question:** Can this existing-data alternative explain the discrepancy?
- **Method:** Same-case scalar energies and matrices; parabolic me=.067, mhh=.112 m0 from Demo20; k cutoff retained for matched comparison.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** method-limited diagnostic; paper reproduction not established
- **Status:** INCONCLUSIVE
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"source": "C:\\code\\nonlinear_photonics\\demo_results\\demo19\\tables\\demo19_master_results.csv", "case_id": "06", "source_physical_valid": "False", "source_failure": "Demo 11/14 physical QC did not pass", "geometry": "Asymmetric inner grading A", "mass_reference": "Demo21 demo20_math_physics_reference.py lines375-390"}
- **Physics interpretation:** No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- **Reason it worked or failed:** Changes in poles and numerator cancellation
- **Hypothesis remains plausible?:** YES
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.28321742388980836, "correlation": 0.1659977511603256, "P1_nm": null, "P1_local_RMSE": 0.16636323615393545, "Z1_nm": null, "Z1_local_RMSE": 0.1380790614168753, "P2_nm": 756.0, "P2_local_RMSE": 0.11906998608972008, "P3_nm": null, "P3_local_RMSE": 0.36061672109666154, "Z2_nm": null, "Z2_local_RMSE": 0.6180060790000838, "P4_nm": 1512.0, "P4_local_RMSE": 0.21518409555251297, "all_peaks_nm": "647.0;698.0;756.0;841.0;1294.0;1512.0", "all_minima_nm": "689.0;703.0;833.0;929.0;1407.0", "topology_json": "[{\"nm\": 647.0, \"local_prominence\": 0.10132206561879187, \"half_prominence_width_nm\": 9.0}, {\"nm\": 698.0, \"local_prominence\": 0.0031281029398095295, \"half_prominence_width_nm\": 8.0}, {\"nm\": 756.0, \"local_prominence\": 0.21198935167153465, \"half_prominence_width_nm\": 18.0}, {\"nm\": 841.0, \"local_prominence\": 0.0014776694415642444, \"half_prominence_width_nm\": 13.0}, {\"nm\": 1294.0, \"local_prominence\": 0.3028891330054674, \"half_prominence_width_nm\": 23.0}, {\"nm\": 1512.0, \"local_prominence\": 0.33093027708233613, \"half_prominence_width_nm\": 28.0}]"}
```

### TEST 159 — consistent scalar Asymmetric inner grading A k0_only

- **Question:** Can this existing-data alternative explain the discrepancy?
- **Method:** Same-case scalar energies and matrices; parabolic me=.067, mhh=.112 m0 from Demo20; k cutoff retained for matched comparison.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** method-limited diagnostic; paper reproduction not established
- **Status:** INCONCLUSIVE
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"source": "C:\\code\\nonlinear_photonics\\demo_results\\demo19\\tables\\demo19_master_results.csv", "case_id": "06", "source_physical_valid": "False", "source_failure": "Demo 11/14 physical QC did not pass", "geometry": "Asymmetric inner grading A", "mass_reference": "Demo21 demo20_math_physics_reference.py lines375-390"}
- **Physics interpretation:** No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- **Reason it worked or failed:** Changes in poles and numerator cancellation
- **Hypothesis remains plausible?:** YES
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.28435051305572967, "correlation": 0.5841616925309752, "P1_nm": null, "P1_local_RMSE": 0.19845790117940662, "Z1_nm": null, "Z1_local_RMSE": 0.04816972618350343, "P2_nm": 757.0, "P2_local_RMSE": 0.3277071004372912, "P3_nm": null, "P3_local_RMSE": 0.5075458526199965, "Z2_nm": null, "Z2_local_RMSE": 0.0817109811034614, "P4_nm": 1514.0, "P4_local_RMSE": 0.36405843637596647, "all_peaks_nm": "757.0;811.0;830.0;859.0;1514.0;1623.0;1661.0;1701.0", "all_minima_nm": "808.0;817.0;838.0;1000.0;1615.0;1635.0;1674.0", "topology_json": "[{\"nm\": 757.0, \"local_prominence\": 0.46367197507717633, \"half_prominence_width_nm\": 8.0}, {\"nm\": 811.0, \"local_prominence\": 0.0003343236340409214, \"half_prominence_width_nm\": 3.0}, {\"nm\": 830.0, \"local_prominence\": 0.010530010318391646, \"half_prominence_width_nm\": 7.0}, {\"nm\": 859.0, \"local_prominence\": 0.002298854652511135, \"half_prominence_width_nm\": 59.0}, {\"nm\": 1514.0, \"local_prominence\": 0.943876233480037, \"half_prominence_width_nm\": 16.0}, {\"nm\": 1623.0, \"local_prominence\": 0.0010577363859622033, \"half_prominence_width_nm\": 6.0}, {\"nm\": 1661.0, \"local_prominence\": 0.011695909650368035, \"half_prominence_width_nm\": 14.0}, {\"nm\": 1701.0, \"local_prominence\": 0.003498682299735852, \"half_prominence_width_nm\": 64.0}]"}
```

### TEST 160 — consistent scalar Asymmetric inner grading B production

- **Question:** Can this existing-data alternative explain the discrepancy?
- **Method:** Same-case scalar energies and matrices; parabolic me=.067, mhh=.112 m0 from Demo20; k cutoff retained for matched comparison.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** method-limited diagnostic; paper reproduction not established
- **Status:** INCONCLUSIVE
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"source": "C:\\code\\nonlinear_photonics\\demo_results\\demo19\\tables\\demo19_master_results.csv", "case_id": "07", "source_physical_valid": "False", "source_failure": "Demo 11/14 physical QC did not pass", "geometry": "Asymmetric inner grading B", "mass_reference": "Demo21 demo20_math_physics_reference.py lines375-390"}
- **Physics interpretation:** No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- **Reason it worked or failed:** Changes in poles and numerator cancellation
- **Hypothesis remains plausible?:** YES
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.28189231712325624, "correlation": 0.17639642468728614, "P1_nm": null, "P1_local_RMSE": 0.16649991079141352, "Z1_nm": null, "Z1_local_RMSE": 0.13337394926982973, "P2_nm": 757.0, "P2_local_RMSE": 0.11518335543665703, "P3_nm": null, "P3_local_RMSE": 0.3600817285138088, "Z2_nm": null, "Z2_local_RMSE": 0.6178044654254243, "P4_nm": 1514.0, "P4_local_RMSE": 0.20592584085234977, "all_peaks_nm": "648.0;698.0;757.0;838.0;1296.0;1514.0", "all_minima_nm": "689.0;702.0;833.0;932.0;1406.0", "topology_json": "[{\"nm\": 648.0, \"local_prominence\": 0.10216030682844751, \"half_prominence_width_nm\": 10.0}, {\"nm\": 698.0, \"local_prominence\": 0.002682950108281512, \"half_prominence_width_nm\": 7.0}, {\"nm\": 757.0, \"local_prominence\": 0.21166157103740835, \"half_prominence_width_nm\": 18.0}, {\"nm\": 838.0, \"local_prominence\": 0.0005772453653010712, \"half_prominence_width_nm\": 7.0}, {\"nm\": 1296.0, \"local_prominence\": 0.300725617700321, \"half_prominence_width_nm\": 23.0}, {\"nm\": 1514.0, \"local_prominence\": 0.328865329369723, \"half_prominence_width_nm\": 29.0}]"}
```

### TEST 161 — consistent scalar Asymmetric inner grading B k0_only

- **Question:** Can this existing-data alternative explain the discrepancy?
- **Method:** Same-case scalar energies and matrices; parabolic me=.067, mhh=.112 m0 from Demo20; k cutoff retained for matched comparison.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** method-limited diagnostic; paper reproduction not established
- **Status:** INCONCLUSIVE
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"source": "C:\\code\\nonlinear_photonics\\demo_results\\demo19\\tables\\demo19_master_results.csv", "case_id": "07", "source_physical_valid": "False", "source_failure": "Demo 11/14 physical QC did not pass", "geometry": "Asymmetric inner grading B", "mass_reference": "Demo21 demo20_math_physics_reference.py lines375-390"}
- **Physics interpretation:** No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- **Reason it worked or failed:** Changes in poles and numerator cancellation
- **Hypothesis remains plausible?:** YES
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.28340952500986705, "correlation": 0.5948608859067697, "P1_nm": null, "P1_local_RMSE": 0.19845112906797696, "Z1_nm": null, "Z1_local_RMSE": 0.04817350039801302, "P2_nm": 758.0, "P2_local_RMSE": 0.3273515842725001, "P3_nm": null, "P3_local_RMSE": 0.5073909293509987, "Z2_nm": null, "Z2_local_RMSE": 0.08167190612797838, "P4_nm": 1516.0, "P4_local_RMSE": 0.3585309141504973, "all_peaks_nm": "758.0;810.0;830.0;855.0;1516.0;1621.0;1659.0;1697.0", "all_minima_nm": "808.0;817.0;837.0;1003.0;1614.0;1634.0;1673.0", "topology_json": "[{\"nm\": 758.0, \"local_prominence\": 0.4628289421008575, \"half_prominence_width_nm\": 8.0}, {\"nm\": 810.0, \"local_prominence\": 0.00016787944445289388, \"half_prominence_width_nm\": 2.0}, {\"nm\": 830.0, \"local_prominence\": 0.008507091227554362, \"half_prominence_width_nm\": 7.0}, {\"nm\": 855.0, \"local_prominence\": 0.0028264523037478447, \"half_prominence_width_nm\": 59.0}, {\"nm\": 1516.0, \"local_prominence\": 0.9414379822013516, \"half_prominence_width_nm\": 16.0}, {\"nm\": 1621.0, \"local_prominence\": 0.0008735864504955393, \"half_prominence_width_nm\": 5.0}, {\"nm\": 1659.0, \"local_prominence\": 0.010225197177753463, \"half_prominence_width_nm\": 13.0}, {\"nm\": 1697.0, \"local_prominence\": 0.003061603215490767, \"half_prominence_width_nm\": 55.0}]"}
```

### TEST 162 — consistent scalar Inner interfaces graded only production

- **Question:** Can this existing-data alternative explain the discrepancy?
- **Method:** Same-case scalar energies and matrices; parabolic me=.067, mhh=.112 m0 from Demo20; k cutoff retained for matched comparison.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** method-limited diagnostic; paper reproduction not established
- **Status:** INCONCLUSIVE
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"source": "C:\\code\\nonlinear_photonics\\demo_results\\demo19\\tables\\demo19_master_results.csv", "case_id": "08", "source_physical_valid": "False", "source_failure": "Demo 11/14 physical QC did not pass", "geometry": "Inner interfaces graded only", "mass_reference": "Demo21 demo20_math_physics_reference.py lines375-390"}
- **Physics interpretation:** No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- **Reason it worked or failed:** Changes in poles and numerator cancellation
- **Hypothesis remains plausible?:** YES
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.28319089403803693, "correlation": 0.16756769461301074, "P1_nm": null, "P1_local_RMSE": 0.1663468470716661, "Z1_nm": null, "Z1_local_RMSE": 0.1374819151630488, "P2_nm": 756.0, "P2_local_RMSE": 0.11839673216968927, "P3_nm": null, "P3_local_RMSE": 0.36027285875397413, "Z2_nm": null, "Z2_local_RMSE": 0.6187031862801321, "P4_nm": 1513.0, "P4_local_RMSE": 0.21413098466315938, "all_peaks_nm": "648.0;698.0;756.0;840.0;1295.0;1513.0", "all_minima_nm": "689.0;703.0;833.0;929.0;1406.0", "topology_json": "[{\"nm\": 648.0, \"local_prominence\": 0.10060995217883462, \"half_prominence_width_nm\": 9.0}, {\"nm\": 698.0, \"local_prominence\": 0.002993288454542664, \"half_prominence_width_nm\": 7.0}, {\"nm\": 756.0, \"local_prominence\": 0.21126728628054758, \"half_prominence_width_nm\": 18.0}, {\"nm\": 840.0, \"local_prominence\": 0.0011431809331706455, \"half_prominence_width_nm\": 11.0}, {\"nm\": 1295.0, \"local_prominence\": 0.30252831977738626, \"half_prominence_width_nm\": 23.0}, {\"nm\": 1513.0, \"local_prominence\": 0.3298187097528046, \"half_prominence_width_nm\": 29.0}]"}
```

### TEST 163 — consistent scalar Inner interfaces graded only k0_only

- **Question:** Can this existing-data alternative explain the discrepancy?
- **Method:** Same-case scalar energies and matrices; parabolic me=.067, mhh=.112 m0 from Demo20; k cutoff retained for matched comparison.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** method-limited diagnostic; paper reproduction not established
- **Status:** INCONCLUSIVE
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"source": "C:\\code\\nonlinear_photonics\\demo_results\\demo19\\tables\\demo19_master_results.csv", "case_id": "08", "source_physical_valid": "False", "source_failure": "Demo 11/14 physical QC did not pass", "geometry": "Inner interfaces graded only", "mass_reference": "Demo21 demo20_math_physics_reference.py lines375-390"}
- **Physics interpretation:** No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- **Reason it worked or failed:** Changes in poles and numerator cancellation
- **Hypothesis remains plausible?:** YES
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.2842513238617989, "correlation": 0.5857857883891275, "P1_nm": null, "P1_local_RMSE": 0.19845673372607003, "Z1_nm": null, "Z1_local_RMSE": 0.048170644620021276, "P2_nm": 757.0, "P2_local_RMSE": 0.327760009098857, "P3_nm": null, "P3_local_RMSE": 0.5075124843601995, "Z2_nm": null, "Z2_local_RMSE": 0.08169815919891434, "P4_nm": 1515.0, "P4_local_RMSE": 0.3634211843452616, "all_peaks_nm": "757.0;811.0;830.0;858.0;1515.0;1622.0;1660.0;1700.0", "all_minima_nm": "807.0;817.0;837.0;1001.0;1614.0;1634.0;1673.0", "topology_json": "[{\"nm\": 757.0, \"local_prominence\": 0.4587259238778189, \"half_prominence_width_nm\": 9.0}, {\"nm\": 811.0, \"local_prominence\": 0.00028962430564414415, \"half_prominence_width_nm\": 3.0}, {\"nm\": 830.0, \"local_prominence\": 0.009980505993695044, \"half_prominence_width_nm\": 7.0}, {\"nm\": 858.0, \"local_prominence\": 0.0024644629619651817, \"half_prominence_width_nm\": 59.0}, {\"nm\": 1515.0, \"local_prominence\": 0.9429557083456089, \"half_prominence_width_nm\": 16.0}, {\"nm\": 1622.0, \"local_prominence\": 0.0011009361029692272, \"half_prominence_width_nm\": 6.0}, {\"nm\": 1660.0, \"local_prominence\": 0.011190297770160125, \"half_prominence_width_nm\": 14.0}, {\"nm\": 1700.0, \"local_prominence\": 0.0033187258626546853, \"half_prominence_width_nm\": 60.0}]"}
```

### TEST 164 — consistent scalar Outer interfaces graded only production

- **Question:** Can this existing-data alternative explain the discrepancy?
- **Method:** Same-case scalar energies and matrices; parabolic me=.067, mhh=.112 m0 from Demo20; k cutoff retained for matched comparison.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** method-limited diagnostic; paper reproduction not established
- **Status:** INCONCLUSIVE
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"source": "C:\\code\\nonlinear_photonics\\demo_results\\demo19\\tables\\demo19_master_results.csv", "case_id": "09", "source_physical_valid": "False", "source_failure": "Demo 11/14 physical QC did not pass", "geometry": "Outer interfaces graded only", "mass_reference": "Demo21 demo20_math_physics_reference.py lines375-390"}
- **Physics interpretation:** No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- **Reason it worked or failed:** Changes in poles and numerator cancellation
- **Hypothesis remains plausible?:** YES
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.2829329326457067, "correlation": 0.1684983833455839, "P1_nm": null, "P1_local_RMSE": 0.1663659150060308, "Z1_nm": null, "Z1_local_RMSE": 0.13700716859165418, "P2_nm": 757.0, "P2_local_RMSE": 0.11809930341700864, "P3_nm": null, "P3_local_RMSE": 0.36024871210756987, "Z2_nm": null, "Z2_local_RMSE": 0.6182077674534446, "P4_nm": 1513.0, "P4_local_RMSE": 0.21328775549281104, "all_peaks_nm": "648.0;698.0;757.0;839.0;1295.0;1513.0", "all_minima_nm": "689.0;702.0;833.0;930.0;1406.0", "topology_json": "[{\"nm\": 648.0, \"local_prominence\": 0.10123470504656906, \"half_prominence_width_nm\": 9.0}, {\"nm\": 698.0, \"local_prominence\": 0.0029596801099073256, \"half_prominence_width_nm\": 8.0}, {\"nm\": 757.0, \"local_prominence\": 0.21069914358198444, \"half_prominence_width_nm\": 18.0}, {\"nm\": 839.0, \"local_prominence\": 0.0009434433275261056, \"half_prominence_width_nm\": 10.0}, {\"nm\": 1295.0, \"local_prominence\": 0.30263636995230003, \"half_prominence_width_nm\": 23.0}, {\"nm\": 1513.0, \"local_prominence\": 0.329927618249678, \"half_prominence_width_nm\": 29.0}]"}
```

### TEST 165 — consistent scalar Outer interfaces graded only k0_only

- **Question:** Can this existing-data alternative explain the discrepancy?
- **Method:** Same-case scalar energies and matrices; parabolic me=.067, mhh=.112 m0 from Demo20; k cutoff retained for matched comparison.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** method-limited diagnostic; paper reproduction not established
- **Status:** INCONCLUSIVE
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"source": "C:\\code\\nonlinear_photonics\\demo_results\\demo19\\tables\\demo19_master_results.csv", "case_id": "09", "source_physical_valid": "False", "source_failure": "Demo 11/14 physical QC did not pass", "geometry": "Outer interfaces graded only", "mass_reference": "Demo21 demo20_math_physics_reference.py lines375-390"}
- **Physics interpretation:** No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- **Reason it worked or failed:** Changes in poles and numerator cancellation
- **Hypothesis remains plausible?:** YES
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.2842542009694418, "correlation": 0.5868598239856015, "P1_nm": null, "P1_local_RMSE": 0.19845993606555531, "Z1_nm": null, "Z1_local_RMSE": 0.048179549155829456, "P2_nm": 757.0, "P2_local_RMSE": 0.3278673539209011, "P3_nm": null, "P3_local_RMSE": 0.5075215370595575, "Z2_nm": null, "Z2_local_RMSE": 0.08173295135198068, "P4_nm": 1515.0, "P4_local_RMSE": 0.3632046339998003, "all_peaks_nm": "757.0;811.0;830.0;857.0;1515.0;1622.0;1660.0;1698.0", "all_minima_nm": "807.0;817.0;837.0;1001.0;1613.0;1634.0;1673.0", "topology_json": "[{\"nm\": 757.0, \"local_prominence\": 0.45418468405310825, \"half_prominence_width_nm\": 9.0}, {\"nm\": 811.0, \"local_prominence\": 0.00040730829378406164, \"half_prominence_width_nm\": 3.0}, {\"nm\": 830.0, \"local_prominence\": 0.009572202871901685, \"half_prominence_width_nm\": 7.0}, {\"nm\": 857.0, \"local_prominence\": 0.0025312696863750723, \"half_prominence_width_nm\": 58.0}, {\"nm\": 1515.0, \"local_prominence\": 0.942652907372652, \"half_prominence_width_nm\": 16.0}, {\"nm\": 1622.0, \"local_prominence\": 0.0014966021083564, \"half_prominence_width_nm\": 6.0}, {\"nm\": 1660.0, \"local_prominence\": 0.010263499967007261, \"half_prominence_width_nm\": 14.0}, {\"nm\": 1698.0, \"local_prominence\": 0.0029720561581193863, \"half_prominence_width_nm\": 55.0}]"}
```

### TEST 166 — consistent scalar Fermi-like 0.7 nm production

- **Question:** Can this existing-data alternative explain the discrepancy?
- **Method:** Same-case scalar energies and matrices; parabolic me=.067, mhh=.112 m0 from Demo20; k cutoff retained for matched comparison.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** method-limited diagnostic; paper reproduction not established
- **Status:** INCONCLUSIVE
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"source": "C:\\code\\nonlinear_photonics\\demo_results\\demo19\\tables\\demo19_master_results.csv", "case_id": "10", "source_physical_valid": "False", "source_failure": "Demo 11/14 physical QC did not pass", "geometry": "Fermi-like 0.7 nm", "mass_reference": "Demo21 demo20_math_physics_reference.py lines375-390"}
- **Physics interpretation:** No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- **Reason it worked or failed:** Changes in poles and numerator cancellation
- **Hypothesis remains plausible?:** YES
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.28286964673170556, "correlation": 0.1690054667782377, "P1_nm": null, "P1_local_RMSE": 0.1663783570861278, "Z1_nm": null, "Z1_local_RMSE": 0.13674688073272817, "P2_nm": 757.0, "P2_local_RMSE": 0.11793794614027642, "P3_nm": null, "P3_local_RMSE": 0.36024041360844017, "Z2_nm": null, "Z2_local_RMSE": 0.6182049759064534, "P4_nm": 1513.0, "P4_local_RMSE": 0.2127796508445828, "all_peaks_nm": "648.0;698.0;757.0;839.0;1295.0;1513.0", "all_minima_nm": "689.0;702.0;833.0;930.0;1406.0", "topology_json": "[{\"nm\": 648.0, \"local_prominence\": 0.10123103918843496, \"half_prominence_width_nm\": 9.0}, {\"nm\": 698.0, \"local_prominence\": 0.0029513920782374137, \"half_prominence_width_nm\": 8.0}, {\"nm\": 757.0, \"local_prominence\": 0.21085635489303395, \"half_prominence_width_nm\": 17.0}, {\"nm\": 839.0, \"local_prominence\": 0.0009291657306848278, \"half_prominence_width_nm\": 10.0}, {\"nm\": 1295.0, \"local_prominence\": 0.30225184719029274, \"half_prominence_width_nm\": 23.0}, {\"nm\": 1513.0, \"local_prominence\": 0.32977747002597346, \"half_prominence_width_nm\": 29.0}]"}
```

### TEST 167 — consistent scalar Fermi-like 0.7 nm k0_only

- **Question:** Can this existing-data alternative explain the discrepancy?
- **Method:** Same-case scalar energies and matrices; parabolic me=.067, mhh=.112 m0 from Demo20; k cutoff retained for matched comparison.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** method-limited diagnostic; paper reproduction not established
- **Status:** INCONCLUSIVE
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"source": "C:\\code\\nonlinear_photonics\\demo_results\\demo19\\tables\\demo19_master_results.csv", "case_id": "10", "source_physical_valid": "False", "source_failure": "Demo 11/14 physical QC did not pass", "geometry": "Fermi-like 0.7 nm", "mass_reference": "Demo21 demo20_math_physics_reference.py lines375-390"}
- **Physics interpretation:** No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- **Reason it worked or failed:** Changes in poles and numerator cancellation
- **Hypothesis remains plausible?:** YES
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.2842103471263298, "correlation": 0.5873571633327092, "P1_nm": null, "P1_local_RMSE": 0.1984595454373119, "Z1_nm": null, "Z1_local_RMSE": 0.04817961995378828, "P2_nm": 757.0, "P2_local_RMSE": 0.327868592751732, "P3_nm": null, "P3_local_RMSE": 0.5075129317866128, "Z2_nm": null, "Z2_local_RMSE": 0.0817290171820842, "P4_nm": 1515.0, "P4_local_RMSE": 0.3630054791863417, "all_peaks_nm": "757.0;811.0;830.0;857.0;1515.0;1622.0;1660.0;1698.0", "all_minima_nm": "807.0;817.0;837.0;1001.0;1614.0;1634.0;1673.0", "topology_json": "[{\"nm\": 757.0, \"local_prominence\": 0.45238540623186785, \"half_prominence_width_nm\": 9.0}, {\"nm\": 811.0, \"local_prominence\": 0.00033291621622372203, \"half_prominence_width_nm\": 3.0}, {\"nm\": 830.0, \"local_prominence\": 0.009471042898848436, \"half_prominence_width_nm\": 7.0}, {\"nm\": 857.0, \"local_prominence\": 0.00254855371911567, \"half_prominence_width_nm\": 58.0}, {\"nm\": 1515.0, \"local_prominence\": 0.9428681321838497, \"half_prominence_width_nm\": 16.0}, {\"nm\": 1622.0, \"local_prominence\": 0.0012480170384321504, \"half_prominence_width_nm\": 6.0}, {\"nm\": 1660.0, \"local_prominence\": 0.010504768808989096, \"half_prominence_width_nm\": 14.0}, {\"nm\": 1698.0, \"local_prominence\": 0.003098941228357306, \"half_prominence_width_nm\": 56.0}]"}
```

### TEST 168 — consistent scalar erf 0.7 nm production

- **Question:** Can this existing-data alternative explain the discrepancy?
- **Method:** Same-case scalar energies and matrices; parabolic me=.067, mhh=.112 m0 from Demo20; k cutoff retained for matched comparison.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** method-limited diagnostic; paper reproduction not established
- **Status:** INCONCLUSIVE
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"source": "C:\\code\\nonlinear_photonics\\demo_results\\demo19\\tables\\demo19_master_results.csv", "case_id": "11", "source_physical_valid": "False", "source_failure": "Demo 11/14 physical QC did not pass", "geometry": "erf 0.7 nm", "mass_reference": "Demo21 demo20_math_physics_reference.py lines375-390"}
- **Physics interpretation:** No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- **Reason it worked or failed:** Changes in poles and numerator cancellation
- **Hypothesis remains plausible?:** YES
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.28405982145874864, "correlation": 0.1609758386069631, "P1_nm": null, "P1_local_RMSE": 0.16622247658133127, "Z1_nm": null, "Z1_local_RMSE": 0.14007881128093244, "P2_nm": 756.0, "P2_local_RMSE": 0.12086927374752841, "P3_nm": null, "P3_local_RMSE": 0.3601066215924233, "Z2_nm": null, "Z2_local_RMSE": 0.6191957036388314, "P4_nm": 1511.0, "P4_local_RMSE": 0.22056377344600614, "all_peaks_nm": "647.0;698.0;756.0;839.0;1294.0;1511.0", "all_minima_nm": "689.0;702.0;833.0;929.0;1406.0", "topology_json": "[{\"nm\": 647.0, \"local_prominence\": 0.1025857022806948, \"half_prominence_width_nm\": 10.0}, {\"nm\": 698.0, \"local_prominence\": 0.0031718902046826147, \"half_prominence_width_nm\": 7.0}, {\"nm\": 756.0, \"local_prominence\": 0.21163131889768588, \"half_prominence_width_nm\": 17.0}, {\"nm\": 839.0, \"local_prominence\": 0.0010881090884751754, \"half_prominence_width_nm\": 10.0}, {\"nm\": 1294.0, \"local_prominence\": 0.30210297224884775, \"half_prominence_width_nm\": 23.0}, {\"nm\": 1511.0, \"local_prominence\": 0.32974093481511013, \"half_prominence_width_nm\": 28.0}]"}
```

### TEST 169 — consistent scalar erf 0.7 nm k0_only

- **Question:** Can this existing-data alternative explain the discrepancy?
- **Method:** Same-case scalar energies and matrices; parabolic me=.067, mhh=.112 m0 from Demo20; k cutoff retained for matched comparison.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** method-limited diagnostic; paper reproduction not established
- **Status:** INCONCLUSIVE
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"source": "C:\\code\\nonlinear_photonics\\demo_results\\demo19\\tables\\demo19_master_results.csv", "case_id": "11", "source_physical_valid": "False", "source_failure": "Demo 11/14 physical QC did not pass", "geometry": "erf 0.7 nm", "mass_reference": "Demo21 demo20_math_physics_reference.py lines375-390"}
- **Physics interpretation:** No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- **Reason it worked or failed:** Changes in poles and numerator cancellation
- **Hypothesis remains plausible?:** YES
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.2847669582509829, "correlation": 0.577715743467173, "P1_nm": null, "P1_local_RMSE": 0.1984469625423271, "Z1_nm": null, "Z1_local_RMSE": 0.04814012373824077, "P2_nm": 757.0, "P2_local_RMSE": 0.3279209282201555, "P3_nm": null, "P3_local_RMSE": 0.507488250088189, "Z2_nm": null, "Z2_local_RMSE": 0.08157256171474246, "P4_nm": 1513.0, "P4_local_RMSE": 0.3668795376894857, "all_peaks_nm": "757.0;810.0;830.0;858.0;1513.0;1621.0;1659.0;1698.0", "all_minima_nm": "807.0;816.0;837.0;1000.0;1613.0;1634.0;1673.0", "topology_json": "[{\"nm\": 757.0, \"local_prominence\": 0.461958354262032, \"half_prominence_width_nm\": 8.0}, {\"nm\": 810.0, \"local_prominence\": 0.00036279260175084427, \"half_prominence_width_nm\": 4.0}, {\"nm\": 830.0, \"local_prominence\": 0.009819442145394253, \"half_prominence_width_nm\": 7.0}, {\"nm\": 858.0, \"local_prominence\": 0.0024440814443985326, \"half_prominence_width_nm\": 58.0}, {\"nm\": 1513.0, \"local_prominence\": 0.9433220296548469, \"half_prominence_width_nm\": 16.0}, {\"nm\": 1621.0, \"local_prominence\": 0.001323414787320655, \"half_prominence_width_nm\": 7.0}, {\"nm\": 1659.0, \"local_prominence\": 0.01069799248467225, \"half_prominence_width_nm\": 13.0}, {\"nm\": 1698.0, \"local_prominence\": 0.0031346115972986505, \"half_prominence_width_nm\": 58.0}]"}
```

### TEST 170 — consistent scalar Cosine 0.7 nm production

- **Question:** Can this existing-data alternative explain the discrepancy?
- **Method:** Same-case scalar energies and matrices; parabolic me=.067, mhh=.112 m0 from Demo20; k cutoff retained for matched comparison.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** method-limited diagnostic; paper reproduction not established
- **Status:** INCONCLUSIVE
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"source": "C:\\code\\nonlinear_photonics\\demo_results\\demo19\\tables\\demo19_master_results.csv", "case_id": "12", "source_physical_valid": "False", "source_failure": "Demo 11/14 physical QC did not pass", "geometry": "Cosine 0.7 nm", "mass_reference": "Demo21 demo20_math_physics_reference.py lines375-390"}
- **Physics interpretation:** No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- **Reason it worked or failed:** Changes in poles and numerator cancellation
- **Hypothesis remains plausible?:** YES
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.284180298621738, "correlation": 0.1599500613714698, "P1_nm": null, "P1_local_RMSE": 0.16620806219048292, "Z1_nm": null, "Z1_local_RMSE": 0.14045669630765023, "P2_nm": 756.0, "P2_local_RMSE": 0.12126264201393165, "P3_nm": null, "P3_local_RMSE": 0.36011384027263177, "Z2_nm": null, "Z2_local_RMSE": 0.6192076916225275, "P4_nm": 1511.0, "P4_local_RMSE": 0.22150787233977604, "all_peaks_nm": "647.0;698.0;756.0;839.0;1294.0;1511.0", "all_minima_nm": "689.0;702.0;833.0;929.0;1406.0", "topology_json": "[{\"nm\": 647.0, \"local_prominence\": 0.10252048190229834, \"half_prominence_width_nm\": 9.0}, {\"nm\": 698.0, \"local_prominence\": 0.0031737564970001353, \"half_prominence_width_nm\": 7.0}, {\"nm\": 756.0, \"local_prominence\": 0.21117414337288692, \"half_prominence_width_nm\": 17.0}, {\"nm\": 839.0, \"local_prominence\": 0.0011059375058441734, \"half_prominence_width_nm\": 10.0}, {\"nm\": 1294.0, \"local_prominence\": 0.30160825030339944, \"half_prominence_width_nm\": 23.0}, {\"nm\": 1511.0, \"local_prominence\": 0.32984004984357973, \"half_prominence_width_nm\": 29.0}]"}
```

### TEST 171 — consistent scalar Cosine 0.7 nm k0_only

- **Question:** Can this existing-data alternative explain the discrepancy?
- **Method:** Same-case scalar energies and matrices; parabolic me=.067, mhh=.112 m0 from Demo20; k cutoff retained for matched comparison.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv
- **Result:** method-limited diagnostic; paper reproduction not established
- **Status:** INCONCLUSIVE
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"source": "C:\\code\\nonlinear_photonics\\demo_results\\demo19\\tables\\demo19_master_results.csv", "case_id": "12", "source_physical_valid": "False", "source_failure": "Demo 11/14 physical QC did not pass", "geometry": "Cosine 0.7 nm", "mass_reference": "Demo21 demo20_math_physics_reference.py lines375-390"}
- **Physics interpretation:** No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- **Reason it worked or failed:** Changes in poles and numerator cancellation
- **Hypothesis remains plausible?:** YES
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.2849729119022386, "correlation": 0.5764089973600529, "P1_nm": null, "P1_local_RMSE": 0.19845144063709447, "Z1_nm": null, "Z1_local_RMSE": 0.04814850287561591, "P2_nm": 757.0, "P2_local_RMSE": 0.32815854130128463, "P3_nm": null, "P3_local_RMSE": 0.5075233150298126, "Z2_nm": null, "Z2_local_RMSE": 0.08161064748437137, "P4_nm": 1513.0, "P4_local_RMSE": 0.36792869634235287, "all_peaks_nm": "757.0;810.0;830.0;858.0;1513.0;1621.0;1659.0;1698.0", "all_minima_nm": "807.0;816.0;837.0;1000.0;1613.0;1634.0;1673.0", "topology_json": "[{\"nm\": 757.0, \"local_prominence\": 0.4577536075180267, \"half_prominence_width_nm\": 9.0}, {\"nm\": 810.0, \"local_prominence\": 0.0003696789361656294, \"half_prominence_width_nm\": 4.0}, {\"nm\": 830.0, \"local_prominence\": 0.009842278565214933, \"half_prominence_width_nm\": 7.0}, {\"nm\": 858.0, \"local_prominence\": 0.0024233300769715034, \"half_prominence_width_nm\": 59.0}, {\"nm\": 1513.0, \"local_prominence\": 0.9435634955643477, \"half_prominence_width_nm\": 16.0}, {\"nm\": 1621.0, \"local_prominence\": 0.0013316086435319688, \"half_prominence_width_nm\": 7.0}, {\"nm\": 1659.0, \"local_prominence\": 0.01069145102755821, \"half_prominence_width_nm\": 13.0}, {\"nm\": 1698.0, \"local_prominence\": 0.0031266481147751886, \"half_prominence_width_nm\": 58.0}]"}
```

### TEST 172 — raw unanchored production labels frozen matrices

- **Question:** Can this existing-data alternative explain the discrepancy?
- **Method:** Remove statewise k0 anchoring only; intentionally cross-method frozen scalar numerator, diagnostic only.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo23\raw\production_y_n301_k0100\production_y_n301_k0100\bias_00000\QuantumDispersions\acqw\kp8\dispersion_Gamma_to_y.dat
- **Result:** method-limited diagnostic; paper reproduction not established
- **Status:** INCONCLUSIVE
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"source": "C:\\code\\nonlinear_photonics\\demo_results\\demo23\\raw\\production_y_n301_k0100\\production_y_n301_k0100\\bias_00000\\QuantumDispersions\\acqw\\kp8\\dispersion_Gamma_to_y.dat", "k0_energy_offsets_raw_minus_anchored_eV": [0.01135354112190079, 0.030125593857449395, -0.0040333205137002, 0.003956420170499797]}
- **Physics interpretation:** No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- **Reason it worked or failed:** Changes in poles and numerator cancellation
- **Hypothesis remains plausible?:** YES
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.2878778465814271, "correlation": 0.07539370368081245, "P1_nm": null, "P1_local_RMSE": 0.18231982580816003, "Z1_nm": null, "Z1_local_RMSE": 0.02410552573371528, "P2_nm": 740.0, "P2_local_RMSE": 0.2196895203640204, "P3_nm": null, "P3_local_RMSE": 0.4304799008645957, "Z2_nm": null, "Z2_local_RMSE": 0.4465612558051853, "P4_nm": 1480.0, "P4_local_RMSE": 0.3666298939573935, "all_peaks_nm": "679.0;740.0;831.0;1357.0;1480.0", "all_minima_nm": "709.0;823.0;937.0;1425.0", "topology_json": "[{\"nm\": 679.0, \"local_prominence\": 0.09744398672671128, \"half_prominence_width_nm\": 10.0}, {\"nm\": 740.0, \"local_prominence\": 0.20159849649309458, \"half_prominence_width_nm\": 10.0}, {\"nm\": 831.0, \"local_prominence\": 0.0013395790523459128, \"half_prominence_width_nm\": 15.0}, {\"nm\": 1357.0, \"local_prominence\": 0.2603974483495677, \"half_prominence_width_nm\": 21.0}, {\"nm\": 1480.0, \"local_prominence\": 0.3548896718383714, \"half_prominence_width_nm\": 18.0}]"}
```

### TEST 173 — pureHH alternative branch A k0_only

- **Question:** Can this existing-data alternative explain the discrepancy?
- **Method:** Same raw branch energies and normalized dominant-component envelopes; HH pair1/2 replaces LH-dominated pair3/4. No branch averaging; projected-component approximation, not full multiband optical matrix. Finite-k labels uncertified.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo23\raw\production_y_n301_k0100\production_y_n301_k0100\bias_00000\QuantumDispersions\acqw\kp8\dispersion_Gamma_to_y.dat; C:\code\nonlinear_photonics\demo_results\demo23\raw\production_y_n301_k0100\production_y_n301_k0100\bias_00000\Quantum\acqw\kp8
- **Result:** method-limited diagnostic; paper reproduction not established
- **Status:** INCONCLUSIVE
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"source": "C:\\code\\nonlinear_photonics\\demo_results\\demo23\\raw\\production_y_n301_k0100\\production_y_n301_k0100\\bias_00000\\QuantumDispersions\\acqw\\kp8\\dispersion_Gamma_to_y.dat; C:\\code\\nonlinear_photonics\\demo_results\\demo23\\raw\\production_y_n301_k0100\\production_y_n301_k0100\\bias_00000\\Quantum\\acqw\\kp8", "state_component_spec": [[11, "cb1"], [13, "cb1"], [6, "hh1"], [2, "hh1"]], "overlap_real": [[0.9893500543605964, -0.06272354731113158], [-0.08583792806417463, -0.8122470398256763]], "ze_real_nm": [[12.825102287002633, 1.5130367239648306], [1.5130367239648308, 17.670450306262918]], "zh_real_nm": [[12.65391553663491, -1.3532164159190025], [-1.3532164159190025, 14.290366295020007]], "limitation": "Method-limited projected-envelope diagnostic, even for pureHH states; finite-k spinors absent."}
- **Physics interpretation:** No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- **Reason it worked or failed:** Changes in poles and numerator cancellation
- **Hypothesis remains plausible?:** YES
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.30990383139317146, "correlation": 0.1907060194903151, "P1_nm": null, "P1_local_RMSE": 0.19814869125402237, "Z1_nm": null, "Z1_local_RMSE": 0.046991585912693964, "P2_nm": 732.0, "P2_local_RMSE": 0.35054555919283564, "P3_nm": null, "P3_local_RMSE": 0.5070632892723356, "Z2_nm": null, "Z2_local_RMSE": 0.07623388087718827, "P4_nm": 1464.0, "P4_local_RMSE": 0.5099623848881526, "all_peaks_nm": "732.0;820.0;844.0;1464.0;1589.0;1638.0;1665.0", "all_minima_nm": "807.0;826.0;970.0;1583.0;1602.0;1651.0", "topology_json": "[{\"nm\": 732.0, \"local_prominence\": 0.47222385070337863, \"half_prominence_width_nm\": 8.0}, {\"nm\": 820.0, \"local_prominence\": 0.0038849557240083384, \"half_prominence_width_nm\": 6.0}, {\"nm\": 844.0, \"local_prominence\": 0.0019193578619635682, \"half_prominence_width_nm\": 53.0}, {\"nm\": 1464.0, \"local_prominence\": 0.9583286612688103, \"half_prominence_width_nm\": 15.0}, {\"nm\": 1589.0, \"local_prominence\": 0.0004152342548740251, \"half_prominence_width_nm\": 5.0}, {\"nm\": 1638.0, \"local_prominence\": 0.0019414180866220987, \"half_prominence_width_nm\": 13.0}, {\"nm\": 1665.0, \"local_prominence\": 0.0006733421796959599, \"half_prominence_width_nm\": 24.0}]"}
```

### TEST 174 — pureHH alternative branch A production

- **Question:** Can this existing-data alternative explain the discrepancy?
- **Method:** Same raw branch energies and normalized dominant-component envelopes; HH pair1/2 replaces LH-dominated pair3/4. No branch averaging; projected-component approximation, not full multiband optical matrix. Finite-k labels uncertified.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo23\raw\production_y_n301_k0100\production_y_n301_k0100\bias_00000\QuantumDispersions\acqw\kp8\dispersion_Gamma_to_y.dat; C:\code\nonlinear_photonics\demo_results\demo23\raw\production_y_n301_k0100\production_y_n301_k0100\bias_00000\Quantum\acqw\kp8
- **Result:** method-limited diagnostic; paper reproduction not established
- **Status:** INCONCLUSIVE
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"source": "C:\\code\\nonlinear_photonics\\demo_results\\demo23\\raw\\production_y_n301_k0100\\production_y_n301_k0100\\bias_00000\\QuantumDispersions\\acqw\\kp8\\dispersion_Gamma_to_y.dat; C:\\code\\nonlinear_photonics\\demo_results\\demo23\\raw\\production_y_n301_k0100\\production_y_n301_k0100\\bias_00000\\Quantum\\acqw\\kp8", "state_component_spec": [[11, "cb1"], [13, "cb1"], [6, "hh1"], [2, "hh1"]], "overlap_real": [[0.9893500543605964, -0.06272354731113158], [-0.08583792806417463, -0.8122470398256763]], "ze_real_nm": [[12.825102287002633, 1.5130367239648306], [1.5130367239648308, 17.670450306262918]], "zh_real_nm": [[12.65391553663491, -1.3532164159190025], [-1.3532164159190025, 14.290366295020007]], "limitation": "Method-limited projected-envelope diagnostic, even for pureHH states; finite-k spinors absent."}
- **Physics interpretation:** No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- **Reason it worked or failed:** Changes in poles and numerator cancellation
- **Hypothesis remains plausible?:** YES
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.31525703546854883, "correlation": -0.08741928403104862, "P1_nm": null, "P1_local_RMSE": 0.17907708626360622, "Z1_nm": null, "Z1_local_RMSE": 0.03786196881273259, "P2_nm": 728.0, "P2_local_RMSE": 0.24481823847206224, "P3_nm": null, "P3_local_RMSE": 0.41894917491636524, "Z2_nm": null, "Z2_local_RMSE": 0.5550202197684095, "P4_nm": 1455.0, "P4_local_RMSE": 0.38617546606427644, "all_peaks_nm": "669.0;728.0;826.0;1337.0;1455.0", "all_minima_nm": "698.0;824.0;926.0;1406.0", "topology_json": "[{\"nm\": 669.0, \"local_prominence\": 0.09951959733385907, \"half_prominence_width_nm\": 9.0}, {\"nm\": 728.0, \"local_prominence\": 0.07713565214938484, \"half_prominence_width_nm\": 15.0}, {\"nm\": 826.0, \"local_prominence\": 5.4627691249212185e-05, \"half_prominence_width_nm\": 4.0}, {\"nm\": 1337.0, \"local_prominence\": 0.2694689975922271, \"half_prominence_width_nm\": 20.0}, {\"nm\": 1455.0, \"local_prominence\": 0.1036638017871756, \"half_prominence_width_nm\": 24.0}]"}
```

### TEST 175 — pureHH alternative branch B k0_only

- **Question:** Can this existing-data alternative explain the discrepancy?
- **Method:** Same raw branch energies and normalized dominant-component envelopes; HH pair1/2 replaces LH-dominated pair3/4. No branch averaging; projected-component approximation, not full multiband optical matrix. Finite-k labels uncertified.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo23\raw\production_y_n301_k0100\production_y_n301_k0100\bias_00000\QuantumDispersions\acqw\kp8\dispersion_Gamma_to_y.dat; C:\code\nonlinear_photonics\demo_results\demo23\raw\production_y_n301_k0100\production_y_n301_k0100\bias_00000\Quantum\acqw\kp8
- **Result:** method-limited diagnostic; paper reproduction not established
- **Status:** INCONCLUSIVE
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"source": "C:\\code\\nonlinear_photonics\\demo_results\\demo23\\raw\\production_y_n301_k0100\\production_y_n301_k0100\\bias_00000\\QuantumDispersions\\acqw\\kp8\\dispersion_Gamma_to_y.dat; C:\\code\\nonlinear_photonics\\demo_results\\demo23\\raw\\production_y_n301_k0100\\production_y_n301_k0100\\bias_00000\\Quantum\\acqw\\kp8", "state_component_spec": [[12, "cb2"], [14, "cb2"], [5, "hh2"], [1, "hh2"]], "overlap_real": [[0.9893500543606075, -0.0627235473111018], [-0.08583792806401819, -0.812247039826628]], "ze_real_nm": [[12.825102287002522, 1.5130367239639362], [1.5130367239639362, 17.670450306262794]], "zh_real_nm": [[12.653915536635537, -1.3532164159198565], [-1.3532164159198565, 14.290366295030307]], "limitation": "Method-limited projected-envelope diagnostic, even for pureHH states; finite-k spinors absent."}
- **Physics interpretation:** No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- **Reason it worked or failed:** Changes in poles and numerator cancellation
- **Hypothesis remains plausible?:** YES
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.3099038313932629, "correlation": 0.19070601948936347, "P1_nm": null, "P1_local_RMSE": 0.19814869125402687, "Z1_nm": null, "Z1_local_RMSE": 0.046991585912702506, "P2_nm": 732.0, "P2_local_RMSE": 0.35054555919303504, "P3_nm": null, "P3_local_RMSE": 0.5070632892723673, "Z2_nm": null, "Z2_local_RMSE": 0.07623388087721651, "P4_nm": 1464.0, "P4_local_RMSE": 0.5099623848884406, "all_peaks_nm": "732.0;820.0;844.0;1464.0;1589.0;1638.0;1665.0", "all_minima_nm": "807.0;826.0;970.0;1583.0;1602.0;1651.0", "topology_json": "[{\"nm\": 732.0, \"local_prominence\": 0.47222385070354495, \"half_prominence_width_nm\": 8.0}, {\"nm\": 820.0, \"local_prominence\": 0.0038849557241156032, \"half_prominence_width_nm\": 6.0}, {\"nm\": 844.0, \"local_prominence\": 0.0019193578619417818, \"half_prominence_width_nm\": 53.0}, {\"nm\": 1464.0, \"local_prominence\": 0.9583286612688641, \"half_prominence_width_nm\": 15.0}, {\"nm\": 1589.0, \"local_prominence\": 0.00041523425495781224, \"half_prominence_width_nm\": 5.0}, {\"nm\": 1638.0, \"local_prominence\": 0.0019414180865187092, \"half_prominence_width_nm\": 13.0}, {\"nm\": 1665.0, \"local_prominence\": 0.0006733421798072875, \"half_prominence_width_nm\": 24.0}]"}
```

### TEST 176 — pureHH alternative branch B production

- **Question:** Can this existing-data alternative explain the discrepancy?
- **Method:** Same raw branch energies and normalized dominant-component envelopes; HH pair1/2 replaces LH-dominated pair3/4. No branch averaging; projected-component approximation, not full multiband optical matrix. Finite-k labels uncertified.
- **Input data:** C:\code\nonlinear_photonics\demo_results\demo23\raw\production_y_n301_k0100\production_y_n301_k0100\bias_00000\QuantumDispersions\acqw\kp8\dispersion_Gamma_to_y.dat; C:\code\nonlinear_photonics\demo_results\demo23\raw\production_y_n301_k0100\production_y_n301_k0100\bias_00000\Quantum\acqw\kp8
- **Result:** method-limited diagnostic; paper reproduction not established
- **Status:** INCONCLUSIVE
- **Improved paper agreement?:** NO
- **Quantitative evidence / file:** {"source": "C:\\code\\nonlinear_photonics\\demo_results\\demo23\\raw\\production_y_n301_k0100\\production_y_n301_k0100\\bias_00000\\QuantumDispersions\\acqw\\kp8\\dispersion_Gamma_to_y.dat; C:\\code\\nonlinear_photonics\\demo_results\\demo23\\raw\\production_y_n301_k0100\\production_y_n301_k0100\\bias_00000\\Quantum\\acqw\\kp8", "state_component_spec": [[12, "cb2"], [14, "cb2"], [5, "hh2"], [1, "hh2"]], "overlap_real": [[0.9893500543606075, -0.0627235473111018], [-0.08583792806401819, -0.812247039826628]], "ze_real_nm": [[12.825102287002522, 1.5130367239639362], [1.5130367239639362, 17.670450306262794]], "zh_real_nm": [[12.653915536635537, -1.3532164159198565], [-1.3532164159198565, 14.290366295030307]], "limitation": "Method-limited projected-envelope diagnostic, even for pureHH states; finite-k spinors absent."}
- **Physics interpretation:** No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- **Reason it worked or failed:** Changes in poles and numerator cancellation
- **Hypothesis remains plausible?:** YES
- **Requires new Pro data?:** NO

```json
{"normalized_RMSE": 0.31184318537131206, "correlation": -0.10928084571332276, "P1_nm": null, "P1_local_RMSE": 0.1779652921718995, "Z1_nm": null, "Z1_local_RMSE": 0.04695288742754122, "P2_nm": 730.0, "P2_local_RMSE": 0.24362127891599847, "P3_nm": null, "P3_local_RMSE": 0.4155472937294529, "Z2_nm": null, "Z2_local_RMSE": 0.5583778231300988, "P4_nm": 1456.0, "P4_local_RMSE": 0.3840183162843947, "all_peaks_nm": "663.0;730.0;826.0;1327.0;1456.0", "all_minima_nm": "697.0;824.0;922.0;1404.0", "topology_json": "[{\"nm\": 663.0, \"local_prominence\": 0.12671726333432737, \"half_prominence_width_nm\": 10.0}, {\"nm\": 730.0, \"local_prominence\": 0.08445233588510642, \"half_prominence_width_nm\": 15.0}, {\"nm\": 826.0, \"local_prominence\": 5.2813280462485346e-05, \"half_prominence_width_nm\": 4.0}, {\"nm\": 1327.0, \"local_prominence\": 0.3315676123946444, \"half_prominence_width_nm\": 21.0}, {\"nm\": 1456.0, \"local_prominence\": 0.11655351387386759, \"half_prominence_width_nm\": 25.0}]"}
```

## 5. SECTION A — Things that improved agreement

Ranked within the full baseline wavelength domain. Mapping tests use their own shared-support comparator and are not mixed into this ranking. Paper-interpolation tests change the reference measure and are also separate.

1. TEST 36 offdiagonal_only: RMSE 0.221494; reduction 15.59%. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
2. TEST 100 global transition scale 0.95: RMSE 0.226694; reduction 13.60%. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
3. TEST 92 global transition offset -0.1 eV: RMSE 0.226800; reduction 13.56%. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
4. TEST 34 hh_diagonal: RMSE 0.228201; reduction 13.03%. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
5. TEST 38 hh_family: RMSE 0.228242; reduction 13.01%. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
6. TEST 33 electron_diagonal: RMSE 0.228760; reduction 12.82%. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
7. TEST 37 electron_family: RMSE 0.228832; reduction 12.79%. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
8. TEST 127 Global phase scan: RMSE 0.229700; reduction 12.46%. Fitted projection can improve error but cannot explain a magnitude-labeled curve.
9. TEST 93 global transition offset -0.05 eV: RMSE 0.230977; reduction 11.97%. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
10. TEST 28 Gamma 7.5 meV abs_Re: RMSE 0.235071; reduction 10.41%. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
11. TEST 31 Gamma 10 meV abs_Re: RMSE 0.235075; reduction 10.41%. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
12. TEST 87 C_m1_n1_l1 numerator +10%: RMSE 0.236976; reduction 9.69%. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
13. TEST 90 V_m1_n1_l1 numerator -10%: RMSE 0.237007; reduction 9.67%. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
14. TEST 03 observable abs_Re: RMSE 0.237873; reduction 9.34%. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
15. TEST 25 Gamma 5 meV abs_Re: RMSE 0.237873; reduction 9.34%. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
16. TEST 99 global transition scale 0.9: RMSE 0.239508; reduction 8.72%. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
17. TEST 94 global transition offset -0.02 eV: RMSE 0.242338; reduction 7.64%. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
18. TEST 86 C_m1_n1_l1 numerator -10%: RMSE 0.242733; reduction 7.49%. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
19. TEST 91 V_m1_n1_l1 numerator +10%: RMSE 0.242858; reduction 7.44%. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
20. TEST 75 projected kp8 branch B: RMSE 0.244186; reduction 6.94%. Not a full multiband optical matrix or equivalent scalar calculation. Large changes prove sensitivity, not a production matrix bug.
21. TEST 76 projected branch matrix mean: RMSE 0.244186; reduction 6.94%. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
22. TEST 74 projected kp8 branch A: RMSE 0.244186; reduction 6.94%. Not a full multiband optical matrix or equivalent scalar calculation. Large changes prove sensitivity, not a production matrix bug.
23. TEST 22 Gamma 2.5 meV abs_Re: RMSE 0.246522; reduction 6.05%. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
24. TEST 55 correct truncated trapezoid 0.075: RMSE 0.250850; reduction 4.40%. Earlier masked full-grid truncation retained excess half endpoint weight. This corrects truncated diagnostic only; full production integral unchanged.
25. TEST 70 independent raw kmax_y_n301_k0075: RMSE 0.250852; reduction 4.40%. Existing raw output reused, no solver. Comparing cutoff changes tests truncation sensitivity, not convergence with larger physical BZ. Raw finite-k identity uses fixed paired band labels because spinors are absent.
26. TEST 48 equal_points: RMSE 0.251566; reduction 4.13%. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
27. TEST 20 Gamma 2.5 meV magnitude: RMSE 0.257014; reduction 2.05%. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
28. TEST 85 hh2 +5 meV: RMSE 0.257024; reduction 2.05%. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
29. TEST 80 e2 -5 meV: RMSE 0.257050; reduction 2.04%. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
30. TEST 35 both_diagonal: RMSE 0.257341; reduction 1.92%. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
31. TEST 19 Gamma 1 meV abs_Re: RMSE 0.258549; reduction 1.46%. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
32. TEST 17 Gamma 1 meV magnitude: RMSE 0.258642; reduction 1.43%. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
33. TEST 89 C_m2_n2_l2 numerator +10%: RMSE 0.261989; reduction 0.15%. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
34. TEST 63 downsample existing grid stride 5: RMSE 0.262274; reduction 0.04%. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
35. TEST 51 left_rectangle: RMSE 0.262275; reduction 0.04%. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
36. TEST 78 e1 -5 meV: RMSE 0.262301; reduction 0.03%. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
37. TEST 83 hh1 +5 meV: RMSE 0.262332; reduction 0.02%. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
38. TEST 54 correct truncated trapezoid 0.05: RMSE 0.262339; reduction 0.02%. Earlier masked full-grid truncation retained excess half endpoint weight. This corrects truncated diagnostic only; full production integral unchanged.
39. TEST 69 independent raw kmax_y_n301_k0050: RMSE 0.262340; reduction 0.02%. Existing raw output reused, no solver. Comparing cutoff changes tests truncation sensitivity, not convergence with larger physical BZ. Raw finite-k identity uses fixed paired band labels because spinors are absent.
40. TEST 66 independent raw grid_y_n101_k0100: RMSE 0.262352; reduction 0.02%. Existing raw output reused, no solver. Comparing cutoff changes tests truncation sensitivity, not convergence with larger physical BZ. Raw finite-k identity uses fixed paired band labels because spinors are absent.
41. TEST 60 downsample existing grid stride 3: RMSE 0.262352; reduction 0.02%. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
42. TEST 14 Gamma 0.5 meV magnitude: RMSE 0.262357; reduction 0.01%. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
43. TEST 57 downsample existing grid stride 2: RMSE 0.262376; reduction 0.01%. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
44. TEST 67 independent raw grid_y_n201_k0100: RMSE 0.262385; reduction 0.00%. Existing raw output reused, no solver. Comparing cutoff changes tests truncation sensitivity, not convergence with larger physical BZ. Raw finite-k identity uses fixed paired band labels because spinors are absent.
45. TEST 65 shape_preserving_cubic stride 5: RMSE 0.262391; reduction 0.00%. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
46. TEST 62 shape_preserving_cubic stride 3: RMSE 0.262391; reduction 0.00%. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
47. TEST 59 shape_preserving_cubic stride 2: RMSE 0.262391; reduction 0.00%. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.

## 6. SECTION B — Things that did not fix the paper

1. TEST 01 observable magnitude: RMSE 0.262391; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=None, P4=1503.0. Full physical reproduction not established. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
2. TEST 02 observable Re: RMSE 0.383379; strict feature locations nm: P1=None, Z1=None, P2=None, P3=None, Z2=1374.0, P4=1505.0. Full physical reproduction not established. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
3. TEST 04 observable Im: RMSE 0.491303; strict feature locations nm: P1=None, Z1=None, P2=748.0, P3=None, Z2=1398.0, P4=1458.0. Full physical reproduction not established. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
4. TEST 05 observable abs_Im: RMSE 0.358331; strict feature locations nm: P1=None, Z1=None, P2=748.0, P3=None, Z2=None, P4=1496.0. Full physical reproduction not established. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
5. TEST 06 observable Re_squared: RMSE 0.301046; strict feature locations nm: P1=None, Z1=None, P2=753.0, P3=None, Z2=None, P4=1505.0. Full physical reproduction not established. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
6. TEST 07 observable magnitude_squared: RMSE 0.302087; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=None, P4=1503.0. Full physical reproduction not established. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
7. TEST 08 Gamma 0 meV magnitude: RMSE 0.333033; strict feature locations nm: P1=None, Z1=None, P2=758.0, P3=None, Z2=1376.0, P4=1520.0. Full physical reproduction not established. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
8. TEST 09 Gamma 0 meV Re: RMSE 0.340699; strict feature locations nm: P1=None, Z1=None, P2=761.0, P3=None, Z2=1374.0, P4=1520.0. Full physical reproduction not established. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
9. TEST 10 Gamma 0 meV abs_Re: RMSE 0.333033; strict feature locations nm: P1=None, Z1=None, P2=758.0, P3=None, Z2=1376.0, P4=1520.0. Full physical reproduction not established. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
10. TEST 11 Gamma 0.25 meV magnitude: RMSE 0.266403; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=1376.0, P4=1504.0. Full physical reproduction not established. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
11. TEST 12 Gamma 0.25 meV Re: RMSE 0.346574; strict feature locations nm: P1=None, Z1=None, P2=767.0, P3=None, Z2=1374.0, P4=1505.0. Full physical reproduction not established. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
12. TEST 13 Gamma 0.25 meV abs_Re: RMSE 0.266941; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=1376.0, P4=1505.0. Full physical reproduction not established. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
13. TEST 15 Gamma 0.5 meV Re: RMSE 0.347023; strict feature locations nm: P1=None, Z1=None, P2=731.0, P3=None, Z2=1374.0, P4=1505.0. Full physical reproduction not established. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
14. TEST 16 Gamma 0.5 meV abs_Re: RMSE 0.264477; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=1379.0, P4=1505.0. Full physical reproduction not established. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
15. TEST 18 Gamma 1 meV Re: RMSE 0.351096; strict feature locations nm: P1=None, Z1=None, P2=812.0, P3=None, Z2=1374.0, P4=1505.0. Full physical reproduction not established. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
16. TEST 21 Gamma 2.5 meV Re: RMSE 0.364208; strict feature locations nm: P1=None, Z1=None, P2=None, P3=None, Z2=1374.0, P4=1505.0. Full physical reproduction not established. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
17. TEST 23 Gamma 5 meV magnitude: RMSE 0.262391; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=None, P4=1503.0. Full physical reproduction not established. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
18. TEST 24 Gamma 5 meV Re: RMSE 0.383379; strict feature locations nm: P1=None, Z1=None, P2=None, P3=None, Z2=1374.0, P4=1505.0. Full physical reproduction not established. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
19. TEST 26 Gamma 7.5 meV magnitude: RMSE 0.269308; strict feature locations nm: P1=None, Z1=None, P2=751.0, P3=None, Z2=None, P4=1502.0. Full physical reproduction not established. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
20. TEST 27 Gamma 7.5 meV Re: RMSE 0.399482; strict feature locations nm: P1=None, Z1=None, P2=None, P3=None, Z2=1374.0, P4=1506.0. Full physical reproduction not established. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
21. TEST 29 Gamma 10 meV magnitude: RMSE 0.275894; strict feature locations nm: P1=None, Z1=None, P2=751.0, P3=None, Z2=None, P4=1501.0. Full physical reproduction not established. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
22. TEST 30 Gamma 10 meV Re: RMSE 0.414332; strict feature locations nm: P1=None, Z1=None, P2=None, P3=None, Z2=1374.0, P4=1507.0. Full physical reproduction not established. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
23. TEST 32 full16: RMSE 0.262391; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=None, P4=1503.0. Full physical reproduction not established. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
24. TEST 39 cancellation P1: see quantitative evidence Destructive interference is present; a small ratio is not an exact complex zero. Dominance table ranks all 16 pathways.
25. TEST 40 cancellation Z1: see quantitative evidence Destructive interference is present; a small ratio is not an exact complex zero. Dominance table ranks all 16 pathways.
26. TEST 41 cancellation P2: see quantitative evidence Destructive interference is present; a small ratio is not an exact complex zero. Dominance table ranks all 16 pathways.
27. TEST 42 cancellation P3: see quantitative evidence Destructive interference is present; a small ratio is not an exact complex zero. Dominance table ranks all 16 pathways.
28. TEST 43 cancellation Z2: see quantitative evidence Destructive interference is present; a small ratio is not an exact complex zero. Dominance table ranks all 16 pathways.
29. TEST 44 cancellation P4: see quantitative evidence Destructive interference is present; a small ratio is not an exact complex zero. Dominance table ranks all 16 pathways.
30. TEST 45 production: RMSE 0.262391; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=None, P4=1503.0. Full physical reproduction not established. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
31. TEST 46 radial_kdk: RMSE 0.262391; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=None, P4=1503.0. Full physical reproduction not established. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
32. TEST 47 bare_2pi_kdk: RMSE 0.262391; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=None, P4=1503.0. Full physical reproduction not established. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
33. TEST 49 k0_only: RMSE 0.289887; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=None, P4=1504.0. Full physical reproduction not established. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
34. TEST 50 Simpson: RMSE 0.262396; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=None, P4=1503.0. Full physical reproduction not established. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
35. TEST 52 right_rectangle: RMSE 0.262523; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=None, P4=1503.0. Full physical reproduction not established. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
36. TEST 53 correct truncated trapezoid 0.025: RMSE 0.287111; strict feature locations nm: P1=None, Z1=None, P2=751.0, P3=None, Z2=None, P4=1502.0. Full physical reproduction not established. Earlier masked full-grid truncation retained excess half endpoint weight. This corrects truncated diagnostic only; full production integral unchanged.
37. TEST 56 correct truncated trapezoid 0.1: RMSE 0.262391; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=None, P4=1503.0. Full physical reproduction not established. Earlier masked full-grid truncation retained excess half endpoint weight. This corrects truncated diagnostic only; full production integral unchanged.
38. TEST 58 linear stride 2: RMSE 0.262394; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=None, P4=1503.0. Full physical reproduction not established. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
39. TEST 61 linear stride 3: RMSE 0.262398; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=None, P4=1503.0. Full physical reproduction not established. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
40. TEST 64 linear stride 5: RMSE 0.262411; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=None, P4=1503.0. Full physical reproduction not established. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
41. TEST 68 independent raw production_y_n301_k0100: RMSE 0.262391; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=None, P4=1503.0. Full physical reproduction not established. Existing raw output reused, no solver. Comparing cutoff changes tests truncation sensitivity, not convergence with larger physical BZ. Raw finite-k identity uses fixed paired band labels because spinors are absent.
42. TEST 71 independent raw kmax_y_n301_k0125: RMSE 0.279161; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=None, P4=1503.0. Full physical reproduction not established. Existing raw output reused, no solver. Comparing cutoff changes tests truncation sensitivity, not convergence with larger physical BZ. Raw finite-k identity uses fixed paired band labels because spinors are absent.
43. TEST 72 independent raw isotropy_yz45_n301_k0100: RMSE 0.268200; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=None, P4=1503.0. Full physical reproduction not established. Existing raw output reused, no solver. Comparing cutoff changes tests truncation sensitivity, not convergence with larger physical BZ. Raw finite-k identity uses fixed paired band labels because spinors are absent.
44. TEST 73 existing candidate higher-state raw energy ranges: see quantitative evidence Energy-only screening; no higher-state chi without valid matrix elements; k0 mixed character cannot certify finite-k identity or boundness.
45. TEST 77 four-state resonances across measured k: see quantitative evidence Pole proximity is necessary for a literal resonance assignment, not proof of a peak or node.
46. TEST 79 e1 +5 meV: RMSE 0.262452; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=None, P4=1503.0. Full physical reproduction not established. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
47. TEST 81 e2 +5 meV: RMSE 0.267797; strict feature locations nm: P1=None, Z1=None, P2=749.0, P3=None, Z2=None, P4=1498.0. Full physical reproduction not established. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
48. TEST 82 hh1 -5 meV: RMSE 0.262426; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=None, P4=1503.0. Full physical reproduction not established. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
49. TEST 84 hh2 -5 meV: RMSE 0.267830; strict feature locations nm: P1=None, Z1=None, P2=749.0, P3=None, Z2=None, P4=1498.0. Full physical reproduction not established. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
50. TEST 88 C_m2_n2_l2 numerator -10%: RMSE 0.263119; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=None, P4=1503.0. Full physical reproduction not established. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
51. TEST 95 global transition offset 0 eV: RMSE 0.262391; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=None, P4=1503.0. Full physical reproduction not established. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
52. TEST 96 global transition offset 0.02 eV: RMSE 0.282658; strict feature locations nm: P1=None, Z1=None, P2=743.0, P3=None, Z2=None, P4=1485.0. Full physical reproduction not established. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
53. TEST 97 global transition offset 0.05 eV: RMSE 0.305674; strict feature locations nm: P1=None, Z1=None, P2=729.0, P3=None, Z2=None, P4=1459.0. Full physical reproduction not established. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
54. TEST 98 global transition offset 0.1 eV: RMSE 0.328127; strict feature locations nm: P1=None, Z1=None, P2=784.0, P3=None, Z2=1374.0, P4=None. Full physical reproduction not established. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
55. TEST 101 global transition scale 1: RMSE 0.262391; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=None, P4=1503.0. Full physical reproduction not established. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
56. TEST 102 global transition scale 1.05: RMSE 0.321493; strict feature locations nm: P1=None, Z1=None, P2=798.0, P3=None, Z2=1386.0, P4=None. Full physical reproduction not established. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
57. TEST 103 global transition scale 1.1: RMSE 0.336100; strict feature locations nm: P1=None, Z1=None, P2=762.0, P3=None, Z2=1323.0, P4=None. Full physical reproduction not established. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
58. TEST 104 lambda_half: see quantitative evidence Common-domain metric is not ranked against full-domain baseline; coordinate remapping cannot invent additional extrema.
59. TEST 106 wavelength shift -100: see quantitative evidence Common-domain metric is not ranked against full-domain baseline; coordinate remapping cannot invent additional extrema.
60. TEST 107 wavelength shift -50: see quantitative evidence Common-domain metric is not ranked against full-domain baseline; coordinate remapping cannot invent additional extrema.
61. TEST 110 wavelength scale 0.9: see quantitative evidence Common-domain metric is not ranked against full-domain baseline; coordinate remapping cannot invent additional extrema.
62. TEST 111 wavelength scale 0.95: see quantitative evidence Common-domain metric is not ranked against full-domain baseline; coordinate remapping cannot invent additional extrema.
63. TEST 114 paper linear: RMSE 0.262391; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=None, P4=1503.0. Full physical reproduction not established. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
64. TEST 115 paper shape_preserving_cubic: RMSE 0.265058; strict feature locations nm: P1=None, Z1=None, P2=752.0, P3=None, Z2=None, P4=1503.0. Full physical reproduction not established. Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
65. TEST 116 direct_paper_points: see quantitative evidence Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
66. TEST 146 consistent scalar Abrupt reference production: method-limited diagnostic; paper reproduction not established No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
67. TEST 147 consistent scalar Abrupt reference k0_only: method-limited diagnostic; paper reproduction not established No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
68. TEST 148 consistent scalar Linear 0.2 nm production: method-limited diagnostic; paper reproduction not established No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
69. TEST 149 consistent scalar Linear 0.2 nm k0_only: method-limited diagnostic; paper reproduction not established No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
70. TEST 150 consistent scalar Linear 0.4 nm production: method-limited diagnostic; paper reproduction not established No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
71. TEST 151 consistent scalar Linear 0.4 nm k0_only: method-limited diagnostic; paper reproduction not established No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
72. TEST 152 consistent scalar Linear 0.7 nm production: method-limited diagnostic; paper reproduction not established No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
73. TEST 153 consistent scalar Linear 0.7 nm k0_only: method-limited diagnostic; paper reproduction not established No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
74. TEST 154 consistent scalar Linear 1.0 nm production: method-limited diagnostic; paper reproduction not established No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
75. TEST 155 consistent scalar Linear 1.0 nm k0_only: method-limited diagnostic; paper reproduction not established No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
76. TEST 156 consistent scalar Linear 1.4 nm production: method-limited diagnostic; paper reproduction not established No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
77. TEST 157 consistent scalar Linear 1.4 nm k0_only: method-limited diagnostic; paper reproduction not established No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
78. TEST 158 consistent scalar Asymmetric inner grading A production: method-limited diagnostic; paper reproduction not established No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
79. TEST 159 consistent scalar Asymmetric inner grading A k0_only: method-limited diagnostic; paper reproduction not established No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
80. TEST 160 consistent scalar Asymmetric inner grading B production: method-limited diagnostic; paper reproduction not established No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
81. TEST 161 consistent scalar Asymmetric inner grading B k0_only: method-limited diagnostic; paper reproduction not established No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
82. TEST 162 consistent scalar Inner interfaces graded only production: method-limited diagnostic; paper reproduction not established No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
83. TEST 163 consistent scalar Inner interfaces graded only k0_only: method-limited diagnostic; paper reproduction not established No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
84. TEST 164 consistent scalar Outer interfaces graded only production: method-limited diagnostic; paper reproduction not established No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
85. TEST 165 consistent scalar Outer interfaces graded only k0_only: method-limited diagnostic; paper reproduction not established No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
86. TEST 166 consistent scalar Fermi-like 0.7 nm production: method-limited diagnostic; paper reproduction not established No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
87. TEST 167 consistent scalar Fermi-like 0.7 nm k0_only: method-limited diagnostic; paper reproduction not established No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
88. TEST 168 consistent scalar erf 0.7 nm production: method-limited diagnostic; paper reproduction not established No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
89. TEST 169 consistent scalar erf 0.7 nm k0_only: method-limited diagnostic; paper reproduction not established No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
90. TEST 170 consistent scalar Cosine 0.7 nm production: method-limited diagnostic; paper reproduction not established No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
91. TEST 171 consistent scalar Cosine 0.7 nm k0_only: method-limited diagnostic; paper reproduction not established No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
92. TEST 172 raw unanchored production labels frozen matrices: method-limited diagnostic; paper reproduction not established No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
93. TEST 173 pureHH alternative branch A k0_only: method-limited diagnostic; paper reproduction not established No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
94. TEST 174 pureHH alternative branch A production: method-limited diagnostic; paper reproduction not established No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
95. TEST 175 pureHH alternative branch B k0_only: method-limited diagnostic; paper reproduction not established No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
96. TEST 176 pureHH alternative branch B production: method-limited diagnostic; paper reproduction not established No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.

## 7. Inconclusive results

- TEST 73 existing candidate higher-state raw energy ranges: Energy-only screening; no higher-state chi without valid matrix elements; k0 mixed character cannot certify finite-k identity or boundness.
- TEST 74 projected kp8 branch A: Not a full multiband optical matrix or equivalent scalar calculation. Large changes prove sensitivity, not a production matrix bug.
- TEST 75 projected kp8 branch B: Not a full multiband optical matrix or equivalent scalar calculation. Large changes prove sensitivity, not a production matrix bug.
- TEST 76 projected branch matrix mean: Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.
- TEST 121 Literal printed Eq2: Do not extend real-input agreement to general complex matrices.
- TEST 128 Units and dimensional normalization: Overall factors disappear after normalization; paper-version ambiguity matters for absolute response, not baseline normalized mismatch.
- TEST 129 2.296eV resonance inference: Coherent extrema need not equal poles. No author assignment of both peaks to one transition.
- TEST 132 HWHM versus FWHM: A factor two changes width but does not explain missing peaks.
- TEST 133 BZ definition: Different radius remains plausible; exact author/friend convention needed.
- TEST 135 Matrix reconstruction provenance: Different component/state constructions: discrepancy is not proof of a same-method integration error.
- TEST 140 Poisson setup match: Paper/friend electrostatics and carrier conditions unspecified.
- TEST 144 Exact zero and digitization robustness: Use apparent deep minima, not exact analytic nodes. No experimental error bars invented.
- TEST 146 consistent scalar Abrupt reference production: No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- TEST 147 consistent scalar Abrupt reference k0_only: No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- TEST 148 consistent scalar Linear 0.2 nm production: No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- TEST 149 consistent scalar Linear 0.2 nm k0_only: No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- TEST 150 consistent scalar Linear 0.4 nm production: No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- TEST 151 consistent scalar Linear 0.4 nm k0_only: No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- TEST 152 consistent scalar Linear 0.7 nm production: No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- TEST 153 consistent scalar Linear 0.7 nm k0_only: No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- TEST 154 consistent scalar Linear 1.0 nm production: No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- TEST 155 consistent scalar Linear 1.0 nm k0_only: No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- TEST 156 consistent scalar Linear 1.4 nm production: No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- TEST 157 consistent scalar Linear 1.4 nm k0_only: No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- TEST 158 consistent scalar Asymmetric inner grading A production: No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- TEST 159 consistent scalar Asymmetric inner grading A k0_only: No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- TEST 160 consistent scalar Asymmetric inner grading B production: No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- TEST 161 consistent scalar Asymmetric inner grading B k0_only: No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- TEST 162 consistent scalar Inner interfaces graded only production: No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- TEST 163 consistent scalar Inner interfaces graded only k0_only: No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- TEST 164 consistent scalar Outer interfaces graded only production: No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- TEST 165 consistent scalar Outer interfaces graded only k0_only: No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- TEST 166 consistent scalar Fermi-like 0.7 nm production: No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- TEST 167 consistent scalar Fermi-like 0.7 nm k0_only: No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- TEST 168 consistent scalar erf 0.7 nm production: No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- TEST 169 consistent scalar erf 0.7 nm k0_only: No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- TEST 170 consistent scalar Cosine 0.7 nm production: No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- TEST 171 consistent scalar Cosine 0.7 nm k0_only: No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- TEST 172 raw unanchored production labels frozen matrices: No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- TEST 173 pureHH alternative branch A k0_only: No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- TEST 174 pureHH alternative branch A production: No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- TEST 175 pureHH alternative branch B k0_only: No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.
- TEST 176 pureHH alternative branch B production: No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.

## 8. Existing reusable alternatives

The scalar abrupt/graded variants are internally consistent parabolic diagnostics from each individual matrix/energy record. They are not replacements for kp8 dispersion. Any projected spinor reduction is method-limited; branch averaging is not endorsed as physical. The raw k0 hh2 pair3+4 is97.5757%LH and0%HH. A pureHH pair1+2 exists, but a consistent reduced optical theory is needed. See inventory and additional_data_rows.json.

## 9. Friend reproduction hypotheses

FRIEND_REPRODUCTION_HYPOTHESES.csv maps each plausible difference to numbered tests. Ask first for the exact runnable deck PLUS the exact spectrum-generation/postprocessing script, accompanied by raw output/version/database identifiers. This resolves several uncertainties together. A screenshot does not.

## 10. Root-cause ranking

1. Different matrix source/state labels: Raw hh2 is LH-like; frozen scalar matrices paired with anchored kp8 dispersion. Against: No like-for-like matrix bug proved. Confidence: High concern, medium causal confidence.
2. Abrupt structure: Interface mismatch established. Against: No controlled abrupt kp8 comparison; scalar QC failed. Confidence: Medium.
3. Different BZ definition/cutoff: pi/a versus2pi/a ambiguity; cutoff-sensitive peaks. Against: No0.20pi/a output. Confidence: Medium.
4. Schrodinger-Poisson: Production lacks loop; paper says Poisson. Against: Electrostatic conditions unclear; zero doping not proof of spectral effect. Confidence: Medium-low.
5. Finite-k matrices: Could change cancellation. Against: Friend reportedly reproduced withM0; no demonstration of necessity. Confidence: Unresolved.
6. Different Gamma: Some RMSE improvement. Against: No complete topology repair. Confidence: Low as sole cause.
7. Friend plotted absolute real: RMSE0.237873. Against: Paper magnitude label; missing features. Confidence: Low as sole cause.
8. Different pathway subset: Offdiagonal RMSE0.221494. Against: Deleting terms not justified. Confidence: Low as physical remedy.
9. Different equation/complex handling: Latent conjugation bug for complex inputs. Against: Baseline real-input agreement excellent. Confidence: Low for baseline, high implementation concern.
10. Different wavelength convention: Can move features. Against: Paper explicitly fundamental; cannot invent topology. Confidence: Low.
11. Different version/database: Could alter bands. Against: No evidence of actual difference yet. Confidence: Unknown.
12. Ordinary radial normalization bug: None; normalized constant variants identical. Against: Direct numerical checks pass. Confidence: Strongly disfavored.

## 11. Independent physics professor review

# Independent physics review — Demo 26 home exhaustive audit

Reviewed 2026-09-06 in a separate agent reasoning pass. This is an independent computational physics critique, not an external human professor's certification. No nextnano solver was invoked and no production physics file was changed by this review.

## Verdict

**B. NEED FRIEND'S FILES BEFORE RUNNING PRO.**

The 176 numbered tests provide a substantial, useful audit of the requested families, but neither a paper reproduction nor literal exhaustion of all possible home analysis. The evidence supports postponing a new Professional campaign. The most immediate uncertainty is whether the colleague used the same states, matrices, energy anchoring and integration domain. The demonstrated complex-input bug must be corrected before production use with complex matrices, but it does not explain the current real-matrix baseline discrepancy. Thus A would be misleading if interpreted as finding the cause of the missing paper features; B is the best overall decision.

## Review basis and independent checks

I inspected the complete numbered-test collection and summary, the final report, all 31 added alternative-data rows (TEST 146–176), the existing-data inventory, literal-equation and units notes, raw-state-character CSV, cancellation table, direct-engine numerical evidence, and the actual implementations in `chi2_22.py`, `extended_implementation_audit.py`, `numerical_home_audit.py`, and `close_data_tests.py`. I checked the numerator conjugation algebra independently under general state phases and checked that the reported scalar alternative computations keep each case's energies and matrices together. I did not independently rerun every spectral calculation or re-render every paper page; the source-page transcription audit is supplied evidence, whereas the code algebra and interpretation here are independently examined.

The count is 176 variants/checks, not 176 independent scientific hypotheses: 52 lower-RMSE comparisons, 96 without improvement, 28 without a fit comparison; 25 PASS, 102 FAIL, 43 INCONCLUSIVE, 6 NOT TESTABLE. These two classifications overlap. Tiny numerical decreases and repeated controls do not represent distinct physical successes. FAIL in a fitting row means failure to establish reproduction, not a failed numerical implementation test. A tested variant's insufficiency does not exclude a contribution from its underlying hypothesis.

## Answers to the eleven requested questions

### 1. Have we exhausted the useful home-laptop tests?

**No, in the literal sense.** The declared numerical test families have broad coverage, including the previously overlooked 0.125 pi/a data, scalar abrupt alternatives, genuine independent denominators, continuous phases and pure-HH alternatives. No further cheap parameter sweep is presently compelled by these results. Useful home work remains: reconcile the multiband-to-scalar optical reduction, validate production complex-input behavior after a deliberate fix, and compare the friend's actual files. Existing k=0 multiband data may support more careful optical-operator work, but simply normalizing selected components is not that derivation. Do not turn a bounded audit into a theorem that all home physics is exhausted.

### 2. Which results are actually physically meaningful?

The strongest results are invariants, provenance facts and controlled numerical comparisons. TEST 117–120 independently support the real-input implementation: denominator error zero, pathway error about 4.69e-13 pm/V, final error about 8.76e-13 pm/V. This is shared-input algebra agreement, not independent model validation. TEST 122/124–126 verify the appropriate sign, continuous-phase, origin and real-numerator time-convention invariants in their stated scope. TEST 136 establishes that the retained hh2 pair is 97.5757% LH and 0% HH at k=0. TEST 138 establishes a geometry mismatch. TEST 66–72 use genuine separate dispersion grids/cutoffs and constrain ordinary quadrature sensitivity.

The cancellation table is also physically informative within the assumed model. The total is only about 2.8–4.9% of the sum of electron and signed-hole subtotal magnitudes at the six targets. At Z1 and Z2 the residuals are approximately 3.312+0.061i and -25.209-1.032i pm/V. Strong destructive interference is present, but it does not yield the paper's apparent minima at those wavelengths. Cancellation sensitivity makes internally consistent numerators particularly important.

### 3. Which improved fits are merely numerical fitting?

Absolute real (TEST 03, RMSE 0.237873), selected pathways (TEST 36, 0.221494), arbitrary global phase (TEST 127, approximately 0.2297), freely chosen global shifts/scales, and individual numerator perturbations are diagnostic fit changes. They do not identify a physical correction. Broadening and cutoff changes are physically interpretable only after their conventions are independently established; selecting them by lowest RMSE is still fitting. Projected branch matrices (TEST 74–76) are a method sensitivity study, not a validated multiband susceptibility.

Topology must accompany RMSE. Baseline TEST 01 has P2/P4 at 752/1503 nm but lacks interior P1/P3/Z1/Z2 in the declared target windows. It also has extra structure, including peaks near 688/1376 nm and a tiny 837 nm feature. Raw extrema counts include tiny shoulders; use prominence and wavelength ordering rather than treating every derivative sign change as an equally meaningful paper peak. Gamma=0 finiteness on a finite sampling grid does not establish a converged zero-linewidth continuum response.

### 4. What is most likely different in the friend's reproduction?

My first priority is the state/matrix/energy construction: pure HH versus LH-like selected bands, scalar versus spinor optical matrix definitions, and whether state-specific anchoring was applied. Next are actual interface grading, integration domain/BZ definition, and electrostatic conditions. This is a ranking of diagnostic priority, not quantified posterior probabilities. The friend's report of reproduction is not yet independently verified, and M(k)=M(0) does not specify what M(0) was.

### 5. Is abrupt-versus-graded now the leading cause?

**Not demonstrated.** It is a real discrepancy and a reasonable controlled future test, but matrix/state provenance is at least as concerning. TEST 146 gives scalar abrupt RMSE 0.279932 versus same-method graded 1 nm TEST 154 at 0.291360: abrupt helps that scalar comparison by about 3.9%, while both remain worse than hybrid baseline 0.262391 and lack P1/P3. The abrupt peaks at 759/1517 nm align P2/P4 well; they do not repair the missing topology. All scalar source records have physical_valid=False, so these are explicitly qualified diagnostics. This evidence neither proves nor rules out a larger effect in a consistent kp8 calculation.

### 6. Is BZ convention still important?

**Yes.** Constant radial prefactors cannot change normalized shape (TEST 45–47), but integration bounds can. Existing output reaches 0.125 pi/a; it does not cover the 0.20 pi/a candidate (TEST 133–134). A crystallographic direction, a circular radial domain and a fraction of BZ area are different definitions. The reported 45-degree result also means angular isotropy should remain an approximation under scrutiny. Do not extrapolate the available ray or equate convergence in point count with convergence in physical integration domain.

### 7. Are matrix provenance/state identity more concerning?

**Yes, as a model-consistency concern; not yet as a proved cause.** A nominal HH-only reduced expression paired with an almost purely LH second valence state requires justification. The frozen scalar matrices and statewise-anchored kp8 dispersions are not one raw self-contained multiband dataset. TEST 172 removing anchoring gives RMSE 0.287878, so unanchoring alone is not a fix. The physically motivated pure-HH alternatives TEST 173–176 give roughly 0.3099–0.3153 and still lack P1/P3. These negative results rule against the particular replacement recipe as a cure; they do not validate the original labels or the normalized-component reduction. Kramers branch averaging before evaluating a nonlinear matrix expression is not automatically the physical sum over degenerate states.

### 8. Is Schrodinger–Poisson a serious mismatch?

It is a serious unresolved setup discrepancy, with **unestablished spectral importance**. The recorded quantum-only/no-density deck does not establish the same self-consistent calculation as the paper. Zero doping does not by itself prove electrostatic equivalence; conversely the mere word Poisson does not prove a large field or band bending. The unusual reported charge output should not be treated as a validated physical carrier density without its conventions. Obtain boundary conditions, occupations and carrier assumptions first. A coarse different-geometry Poisson fixture cannot settle this question (TEST 140–141).

### 9. Is finite-k M(k) necessary for reproduction, or future physics?

**Necessity is not established.** It is useful future physics and could matter greatly for cancellation. The colleague's unverified M0 claim and unresolved input differences make a full Demo 25 campaign premature as a required reproduction step. No finite-k wavefunctions were found; energy-column continuity alone cannot certify eigenstate continuity or avoided-crossing identities (TEST 137/142). Do not manufacture M(k) from the energy dispersions.

### 10. What ONE thing from the friend resolves most uncertainty?

Request **the exact runnable reproduction package**: the nextnano input deck and the exact spectrum-generation script, with its selected raw output or precise output-file references and version/database identifiers. Treat this as one archived reproducibility package, not a screenshot. If only one individual file is immediately obtainable, the spectrum-generation script is the most revealing first item because it exposes state indices, matrix definitions, anchoring, k weights and plotted observable; it does not eliminate the need for the deck and data.

### 11. What is the smallest justified new Pro calculation?

**None is justified as the immediate next action before the file comparison.** If files remain unavailable and a controlled geometry discriminator is chosen, run only the abrupt counterpart of the existing graded structure: same nominal 7.1/1.8/2.9 nm structure, outer barriers, material database, temperature, k direction, 301 points and 0.10 pi/a, changing grading alone. Export full k=0 spinors, energies and appropriate optical operators, plus per-k character/overlap information needed to identify states. Reconcile the existing matrix reduction and energy convention before comparing chi. If the friend instead demonstrates a different cutoff or electrostatic setting, that specific controlled change takes priority. A 0.20 pi/a test, a Poisson change and a geometry change should not be bundled into one uninterpretable experiment.

## Implementation finding that must not be hidden

TEST 123 is a real production bug for advertised general complex inputs. With O[n,m]=<e_n|hh_m>, phase cancellation requires conj(O[n,m])*ze[n,l]*O[l,m] and O[n,m]*zh[m,l]*conj(O[n,l]). Production omits the conjugates; the independent engine includes them. The observed magnitude variation reaches about 4.518 pm/V under arbitrary state phases while the independent engine remains invariant within 4.59e-13 pm/V. Real sign flips cannot detect this error. Therefore answer 'Is there an obvious code bug?' with **YES — latent complex-input conjugation bug**, immediately adding **not a demonstrated cause of the frozen-real baseline mismatch**. Correct and regress it in a deliberate future production change before complex use; preserving historical outputs during this audit was appropriate.

## Acceptance and remaining limits

I accept decision B and the conclusion that no tested variant establishes a defensible full reproduction. I do not accept a claim that geometry is proved to be the principal cause, that low RMSE validates altered physics, that real-input agreement validates complex algebra, that all home analysis is exhausted, or that new Professional data are always necessary when the friend may already possess them.

The 2.296 eV inference remains weak as a unique missing-state diagnosis (TEST 129): extrema are not necessarily poles, the paper digitization is approximate, and interference can shift features. Tests based on sample spacing/interpolation quantify robustness, not experimental uncertainty. Absolute normalization and paper-version density notation remain outside a demonstrated normalized-shape reproduction.

The audit is reviewable and the previously missing independent review is now supplied. Its practical next step is provenance reconciliation with the colleague, followed by one controlled calculation only if the comparison identifies a missing eigenstate dataset. This review does not authorize or invoke that calculation.


## 12. SECTION C — Home versus Pro boundary

HOME-COMPLETABLE: compare friend files, reconcile scalar versus kp8 projection and energy anchors, and correct the latent production complex-input conjugation behavior before future complex use. Audit computations already use the independent conjugated engine. Finite-k character certification, matching abrupt kp8, extended0.20pi/a and matching Poisson require missing eigenstates unless the friend already has those outputs.

## 13. Recommended next action

**NEED FRIEND'S FILES BEFORE RUNNING PRO.** First compare exact deck, postprocessing, selected states, matrix definitions, energy anchoring, k vector list, Gamma and electrostatics. No demonstrated requirement for full Demo25 yet. No solver was invoked. No production formula was silently modified.

## 14. Exact minimum Pro run if files do not resolve it

After matching settings, the smallest useful first discriminator is one exact abrupt-versus-existing-graded kp8 comparison: same nominal7.1/1.8/2.9nm design and outer barriers, material database, temperature, k direction,301points and0.10pi/a; change only interface grading to abrupt. Export k0 full complex spinors/matrices, per-k state character and energies; include eigenvectors needed to track states if supported. Reconcile states/energy reference and compute the same justified M0 reduction offline. Do not change Poisson, cutoff and geometry together. If the friend instead specifies0.20pi/a or a different electrostatic solve, that matched convention becomes the targeted discriminator. Full finite-k M(k) campaign is not yet justified by this audit alone.
