# Professor review input

## Primary computed summary

```json
{
  "status": "PRIMARY_ANALYSIS_COMPLETE",
  "demo23_root": "C:\\code\\nonlinear_photonics\\demo_results\\demo23",
  "output": "C:\\code\\nonlinear_photonics\\nextnano\\demos\\24_equation2_spectral_shape_audit\\outputs",
  "finite_k_test": "REQUIRES_NEW_PROFESSIONAL_DATA: finite-k envelope components, finite-k overlap O_nm(k), finite-k electron z matrix z_e(k), finite-k heavy-hole z matrix z_hh(k)",
  "model_metrics": [
    {
      "case": "23A",
      "major_peak_count": 4,
      "peak_wavelengths_nm": "644.0;751.0;1287.0;1502.0",
      "dominant_peak_nm": 1502.0,
      "normalized_RMSE": 0.2913604332576591,
      "spectral_correlation": 0.11151253089873811,
      "rank1_peak_nm": 1502.0,
      "rank1_peak_norm": 1.0,
      "rank2_peak_nm": 1287.0,
      "rank2_peak_norm": 0.9734511287965952,
      "rank3_peak_nm": 751.0,
      "rank3_peak_norm": 0.5541210224851444,
      "rank4_peak_nm": 644.0,
      "rank4_peak_norm": 0.44542420005001127,
      "Z1_minimum_nm": 550.0,
      "Z1_minimum_norm": 0.04508129286892499,
      "Z2_minimum_nm": 1250.0,
      "Z2_minimum_norm": 0.4277626108061773
    },
    {
      "case": "23B",
      "major_peak_count": 3,
      "peak_wavelengths_nm": "751.0;1377.0;1502.0",
      "dominant_peak_nm": 1502.0,
      "normalized_RMSE": 0.2766391185110278,
      "spectral_correlation": 0.23059506399534518,
      "rank1_peak_nm": 1502.0,
      "rank1_peak_norm": 1.0,
      "rank2_peak_nm": 1377.0,
      "rank2_peak_norm": 0.9861389710774016,
      "rank3_peak_nm": 751.0,
      "rank3_peak_norm": 0.5348843939077984,
      "Z1_minimum_nm": 550.0,
      "Z1_minimum_norm": 0.022910028544721097,
      "Z2_minimum_nm": 1250.0,
      "Z2_minimum_norm": 0.17955097527494754
    },
    {
      "case": "23C",
      "major_peak_count": 3,
      "peak_wavelengths_nm": "752.0;1375.0;1503.0",
      "dominant_peak_nm": 1503.0,
      "normalized_RMSE": 0.25891467029269294,
      "spectral_correlation": 0.25603316075168153,
      "rank1_peak_nm": 1503.0,
      "rank1_peak_norm": 1.0,
      "rank2_peak_nm": 1375.0,
      "rank2_peak_norm": 0.8595893424850244,
      "rank3_peak_nm": 752.0,
      "rank3_peak_norm": 0.5291294168356009,
      "Z1_minimum_nm": 550.0,
      "Z1_minimum_norm": 0.020413113633735,
      "Z2_minimum_nm": 1250.0,
      "Z2_minimum_norm": 0.16026058814817717
    },
    {
      "case": "23D",
      "major_peak_count": 3,
      "peak_wavelengths_nm": "752.0;1376.0;1503.0",
      "dominant_peak_nm": 1503.0,
      "normalized_RMSE": 0.2623911178693678,
      "spectral_correlation": 0.24755539373508834,
      "rank1_peak_nm": 1503.0,
      "rank1_peak_norm": 1.0,
      "rank2_peak_nm": 1376.0,
      "rank2_peak_norm": 0.9075002905390831,
      "rank3_peak_nm": 752.0,
      "rank3_peak_norm": 0.5298169782402193,
      "Z1_minimum_nm": 550.0,
      "Z1_minimum_norm": 0.020805620815258073,
      "Z2_minimum_nm": 1250.0,
      "Z2_minimum_norm": 0.16325487004214348
    },
    {
      "case": "24_state_corrected_hh2_pair1+2",
      "major_peak_count": 3,
      "peak_wavelengths_nm": "683.0;1365.0;1495.0",
      "dominant_peak_nm": 1365.0,
      "normalized_RMSE": 0.28030644976444374,
      "spectral_correlation": 0.1485999898079364,
      "rank1_peak_nm": 1365.0,
      "rank1_peak_norm": 1.0,
      "rank2_peak_nm": 1495.0,
      "rank2_peak_norm": 0.8033639093273364,
      "rank3_peak_nm": 683.0,
      "rank3_peak_norm": 0.4731739661125806,
      "Z1_minimum_nm": 550.0,
      "Z1_minimum_norm": 0.02366714942685447,
      "Z2_minimum_nm": 1250.0,
      "Z2_minimum_norm": 0.18766040950258106
    }
  ],
  "baseline_features": [
    {
      "Model": "23D",
      "Feature": "P1",
      "Feature type": "peak",
      "Paper wavelength nm": 540.0,
      "Model wavelength nm": 575.0,
      "Wavelength error nm": 35.0,
      "Paper normalized amplitude": 0.3189873417721519,
      "Model normalized amplitude": 0.02765613281768148,
      "Model amplitude at paper wavelength": 0.018684634024776055,
      "Signed full complex zero": "n/a",
      "Nearest Re crossing nm": "n/a",
      "Nearest Im crossing nm": "n/a",
      "Search window nm": "490-575",
      "Status": "MISMATCH"
    },
    {
      "Model": "23D",
      "Feature": "Z1",
      "Feature type": "minimum",
      "Paper wavelength nm": 605.0,
      "Model wavelength nm": 550.0,
      "Wavelength error nm": -55.0,
      "Paper normalized amplitude": 0.0,
      "Model normalized amplitude": 0.020805620815258073,
      "Model amplitude at paper wavelength": 0.04064783904527022,
      "Signed full complex zero": false,
      "Nearest Re crossing nm": null,
      "Nearest Im crossing nm": null,
      "Search window nm": "550-650",
      "Status": "MISMATCH"
    },
    {
      "Model": "23D",
      "Feature": "P2",
      "Feature type": "peak",
      "Paper wavelength nm": 760.0,
      "Model wavelength nm": 752.0,
      "Wavelength error nm": -8.0,
      "Paper normalized amplitude": 0.620253164556962,
      "Model normalized amplitude": 0.5298169782402193,
      "Model amplitude at paper wavelength": 0.3198138514659221,
      "Signed full complex zero": "n/a",
      "Nearest Re crossing nm": "n/a",
      "Nearest Im crossing nm": "n/a",
      "Search window nm": "680-830",
      "Status": "MATCH"
    },
    {
      "Model": "23D",
      "Feature": "P3",
      "Feature type": "peak",
      "Paper wavelength nm": 1080.0,
      "Model wavelength nm": 1160.0,
      "Wavelength error nm": 80.0,
      "Paper normalized amplitude": 0.8227848101265823,
      "Model normalized amplitude": 0.11160854018108785,
      "Model amplitude at paper wavelength": 0.09087130652715195,
      "Signed full complex zero": "n/a",
      "Nearest Re crossing nm": "n/a",
      "Nearest Im crossing nm": "n/a",
      "Search window nm": "950-1160",
      "Status": "MISMATCH"
    },
    {
      "Model": "23D",
      "Feature": "Z2",
      "Feature type": "minimum",
      "Paper wavelength nm": 1330.0,
      "Model wavelength nm": 1250.0,
      "Wavelength error nm": -80.0,
      "Paper normalized amplitude": 0.0,
      "Model normalized amplitude": 0.16325487004214348,
      "Model amplitude at paper wavelength": 0.30960299970400745,
      "Signed full complex zero": false,
      "Nearest Re crossing nm": null,
      "Nearest Im crossing nm": null,
      "Search window nm": "1250-1400",
      "Status": "MISMATCH"
    },
    {
      "Model": "23D",
      "Feature": "P4",
      "Feature type": "peak",
      "Paper wavelength nm": 1520.0,
      "Model wavelength nm": 1503.0,
      "Wavelength error nm": -17.0,
      "Paper normalized amplitude": 1.0,
      "Model normalized amplitude": 1.0,
      "Model amplitude at paper wavelength": 0.5625120922447611,
      "Signed full complex zero": "n/a",
      "Nearest Re crossing nm": "n/a",
      "Nearest Im crossing nm": "n/a",
      "Search window nm": "1420-1620",
      "Status": "MISMATCH"
    }
  ],
  "state_corrected_features": [
    {
      "Model": "24_state_corrected_hh2_pair1+2",
      "Feature": "P1",
      "Feature type": "peak",
      "Paper wavelength nm": 540.0,
      "Model wavelength nm": 575.0,
      "Wavelength error nm": 35.0,
      "Paper normalized amplitude": 0.3189873417721519,
      "Model normalized amplitude": 0.031702750388736614,
      "Model amplitude at paper wavelength": 0.021202553793863432,
      "Signed full complex zero": "n/a",
      "Nearest Re crossing nm": "n/a",
      "Nearest Im crossing nm": "n/a",
      "Search window nm": "490-575",
      "Status": "MISMATCH"
    },
    {
      "Model": "24_state_corrected_hh2_pair1+2",
      "Feature": "Z1",
      "Feature type": "minimum",
      "Paper wavelength nm": 605.0,
      "Model wavelength nm": 550.0,
      "Wavelength error nm": -55.0,
      "Paper normalized amplitude": 0.0,
      "Model normalized amplitude": 0.02366714942685447,
      "Model amplitude at paper wavelength": 0.047264552304372036,
      "Signed full complex zero": false,
      "Nearest Re crossing nm": null,
      "Nearest Im crossing nm": null,
      "Search window nm": "550-650",
      "Status": "MISMATCH"
    },
    {
      "Model": "24_state_corrected_hh2_pair1+2",
      "Feature": "P2",
      "Feature type": "peak",
      "Paper wavelength nm": 760.0,
      "Model wavelength nm": 683.0,
      "Wavelength error nm": -77.0,
      "Paper normalized amplitude": 0.620253164556962,
      "Model normalized amplitude": 0.4731739661125806,
      "Model amplitude at paper wavelength": 0.28903018756737947,
      "Signed full complex zero": "n/a",
      "Nearest Re crossing nm": "n/a",
      "Nearest Im crossing nm": "n/a",
      "Search window nm": "680-830",
      "Status": "MISMATCH"
    },
    {
      "Model": "24_state_corrected_hh2_pair1+2",
      "Feature": "P3",
      "Feature type": "peak",
      "Paper wavelength nm": 1080.0,
      "Model wavelength nm": 1160.0,
      "Wavelength error nm": 80.0,
      "Paper normalized amplitude": 0.8227848101265823,
      "Model normalized amplitude": 0.12458811018350953,
      "Model amplitude at paper wavelength": 0.09999103691371217,
      "Signed full complex zero": "n/a",
      "Nearest Re crossing nm": "n/a",
      "Nearest Im crossing nm": "n/a",
      "Search window nm": "950-1160",
      "Status": "MISMATCH"
    },
    {
      "Model": "24_state_corrected_hh2_pair1+2",
      "Feature": "Z2",
      "Feature type": "minimum",
      "Paper wavelength nm": 1330.0,
      "Model wavelength nm": 1250.0,
      "Wavelength error nm": -80.0,
      "Paper normalized amplitude": 0.0,
      "Model normalized amplitude": 0.18766040950258106,
      "Model amplitude at paper wavelength": 0.39163099949120683,
      "Signed full complex zero": false,
      "Nearest Re crossing nm": null,
      "Nearest Im crossing nm": null,
      "Search window nm": "1250-1400",
      "Status": "MISMATCH"
    },
    {
      "Model": "24_state_corrected_hh2_pair1+2",
      "Feature": "P4",
      "Feature type": "peak",
      "Paper wavelength nm": 1520.0,
      "Model wavelength nm": 1495.0,
      "Wavelength error nm": -25.0,
      "Paper normalized amplitude": 1.0,
      "Model normalized amplitude": 0.8033639093273364,
      "Model amplitude at paper wavelength": 0.49259477340760166,
      "Signed full complex zero": "n/a",
      "Nearest Re crossing nm": "n/a",
      "Nearest Im crossing nm": "n/a",
      "Search window nm": "1420-1620",
      "Status": "MISMATCH"
    }
  ],
  "state_corrected_metrics": {
    "case": "24_state_corrected_hh2_pair1+2",
    "major_peak_count": 3,
    "peak_wavelengths_nm": "683.0;1365.0;1495.0",
    "dominant_peak_nm": 1365.0,
    "normalized_RMSE": 0.28030644976444374,
    "spectral_correlation": 0.1485999898079364,
    "rank1_peak_nm": 1365.0,
    "rank1_peak_norm": 1.0,
    "rank2_peak_nm": 1495.0,
    "rank2_peak_norm": 0.8033639093273364,
    "rank3_peak_nm": 683.0,
    "rank3_peak_norm": 0.4731739661125806,
    "Z1_minimum_nm": 550.0,
    "Z1_minimum_norm": 0.02366714942685447,
    "Z2_minimum_nm": 1250.0,
    "Z2_minimum_norm": 0.18766040950258106
  },
  "zero_analysis": [
    {
      "model": "23D",
      "feature": "Z1",
      "window_nm": "550-650",
      "wavelength_nm": 550.0,
      "normalized_amplitude": 0.020805620815258073,
      "real_crossings_nm": "",
      "imag_crossings_nm": "",
      "nearest_real_crossing_nm": null,
      "nearest_imag_crossing_nm": null,
      "full_complex_zero": false,
      "threshold_fraction": 0.02
    },
    {
      "model": "23D",
      "feature": "Z2",
      "window_nm": "1250-1400",
      "wavelength_nm": 1250.0,
      "normalized_amplitude": 0.16325487004214348,
      "real_crossings_nm": "",
      "imag_crossings_nm": "",
      "nearest_real_crossing_nm": null,
      "nearest_imag_crossing_nm": null,
      "full_complex_zero": false,
      "threshold_fraction": 0.02
    }
  ],
  "cancellation": [
    {
      "Feature": "P1",
      "wavelength_nm": 540.0,
      "electron_real": 20.946259967195346,
      "electron_imag": 0.19369728037910983,
      "electron_abs": 20.947155540783015,
      "heavy_hole_signed_real": -19.42372408696649,
      "heavy_hole_signed_imag": -0.17737900225109862,
      "heavy_hole_signed_abs": 19.424533989700805,
      "total_real": 1.5225358802288547,
      "total_imag": 0.016318278128011204,
      "total_abs": 1.5226233259691369,
      "phase_difference_deg": -179.99339639245204,
      "cancellation_ratio": 0.0377151252196031
    },
    {
      "Feature": "Z1",
      "wavelength_nm": 605.0,
      "electron_real": 40.3196822312466,
      "electron_imag": 0.5842110619670293,
      "electron_abs": 40.32391446516109,
      "heavy_hole_signed_real": -37.007826666907334,
      "heavy_hole_signed_imag": -0.5230857941082983,
      "heavy_hole_signed_abs": 37.01152325095328,
      "total_real": 3.311855564339268,
      "total_imag": 0.06112526785873107,
      "total_abs": 3.3124195956152316,
      "phase_difference_deg": -179.97966348568093,
      "cancellation_ratio": 0.04283184647864252
    },
    {
      "Feature": "P2",
      "wavelength_nm": 760.0,
      "electron_real": 27.1949613850052,
      "electron_imag": 379.44527842011416,
      "electron_abs": 380.4185658456352,
      "heavy_hole_signed_real": -53.2055261073474,
      "heavy_hole_signed_imag": -377.81118174734627,
      "heavy_hole_signed_abs": 381.539142240591,
      "total_real": -26.010564722342203,
      "total_imag": 1.634096672767896,
      "total_abs": 26.061844698929193,
      "phase_difference_deg": -176.08339182498116,
      "cancellation_ratio": 0.03420379428195237
    },
    {
      "Feature": "P3",
      "wavelength_nm": 1080.0,
      "electron_real": -133.86775662511002,
      "electron_imag": 0.48639554529147044,
      "electron_abs": 133.8686402577772,
      "heavy_hole_signed_real": 126.4625936002977,
      "heavy_hole_signed_imag": -0.489206311097045,
      "heavy_hole_signed_abs": 126.46353981653714,
      "total_real": -7.405163024812325,
      "total_imag": -0.0028107658055745444,
      "total_abs": 7.405163558251231,
      "phase_difference_deg": -179.98653658747452,
      "cancellation_ratio": 0.028445056451097805
    },
    {
      "Feature": "Z2",
      "wavelength_nm": 1330.0,
      "electron_real": -272.1269927508607,
      "electron_imag": -5.404385104763041,
      "electron_abs": 272.1806524387573,
      "heavy_hole_signed_real": 246.91834564029796,
      "heavy_hole_signed_imag": 4.3725535385043965,
      "heavy_hole_signed_abs": 246.9570582878504,
      "total_real": -25.208647110562765,
      "total_imag": -1.0318315662586448,
      "total_abs": 25.229755558189865,
      "phase_difference_deg": -179.8767836525972,
      "cancellation_ratio": 0.04859935049387416
    },
    {
      "Feature": "P4",
      "wavelength_nm": 1520.0,
      "electron_real": -151.21380853204636,
      "electron_imag": -758.4581492364199,
      "electron_abs": 773.3850140996409,
      "heavy_hole_signed_real": 196.95155648550877,
      "heavy_hole_signed_imag": 755.4057808666099,
      "heavy_hole_signed_abs": 780.6585741338894,
      "total_real": 45.73774795346242,
      "total_imag": -3.052368369809983,
      "total_abs": 45.83948669563689,
      "phase_difference_deg": -176.66221703045093,
      "cancellation_ratio": 0.029496911825840286
    }
  ],
  "top_root_causes": [
    {
      "Rank": 1,
      "Hypothesis": "missing states / model-space truncation (transition above the bound-subband range)",
      "Evidence for": "24N reachability: P1 (540 nm) and P3 (1080 nm) are an exact one-photon/two-photon pair of a single 2.296 eV transition; the largest transition any bound-subband pair reaches before the electron leaves the 2.145 eV barrier is 1.966 eV, so no k, energy shift, amplitude, sign, broadening or normalization change can create them; both model 'features' sit on their search-window edges",
      "Evidence against": "the paper text restricts Eq. 2 to the first two electron and HH bound states, so this implies the compared curve is not that four-state calculation",
      "Explains peak positions?": "yes",
      "Explains 605 zero?": "yes",
      "Explains 1330 zero?": "partly",
      "Explains overall shape?": "yes",
      "Can test from existing data?": "yes",
      "Requires Pro rerun?": "yes",
      "Confidence": "0.94",
      "Confidence score": 0.94
    },
    {
      "Rank": 2,
      "Hypothesis": "missing finite-k M(k)",
      "Evidence for": "24N amplitude scan: a single -10% change in C_m1_n1_l1 (or +10% in V_m1_n1_l1) opens a genuine complex node at 573 nm (normalized 0.0001) and 1282 nm (0.0018), both moving toward the paper's 605/1330 nm; electron and heavy-hole subtotals are 180.0 deg antiphase and cancel to 4.3-4.9%, so a few-percent numerator error is amplified about 21-24x; a frozen numerator also fails to damp the high-k tail, which is what leaves the cutoff artifact sharp",
      "Evidence against": "no finite-k envelope or matrix data exist in the copied output, so the required M(k) variation is bounded, not measured",
      "Explains peak positions?": "partly",
      "Explains 605 zero?": "yes",
      "Explains 1330 zero?": "yes",
      "Explains overall shape?": "yes",
      "Can test from existing data?": "no",
      "Requires Pro rerun?": "yes",
      "Confidence": "0.90",
      "Confidence score": 0.9
    },
    {
      "Rank": 3,
      "Hypothesis": "kmax / k-truncation artifact",
      "Evidence for": "24N cutoff test: the model peak near 1318 nm moves 1502->1431->1376->1318 nm as kmax goes 0.05->0.125 pi/a and matches 2hc/DeltaE(kmax) to 9 nm mean error, so it is a truncation artifact, not a resonance; the 659 nm peak behaves the same way at one photon; the integrand for P1/Z1/P3/Z2 still peaks at the last k sample",
      "Evidence against": "the two features that do match the paper (752 and 1503 nm) are stable to 1 nm across all four cutoffs, so truncation does not explain the P2/P4 residual; extending kmax alone would move the artifact rather than remove it",
      "Explains peak positions?": "partly",
      "Explains 605 zero?": "partly",
      "Explains 1330 zero?": "yes",
      "Explains overall shape?": "yes",
      "Can test from existing data?": "yes",
      "Requires Pro rerun?": "yes",
      "Confidence": "0.88",
      "Confidence score": 0.88
    },
    {
      "Rank": 4,
      "Hypothesis": "geometry mismatch",
      "Evidence for": "a structure whose second dominant transition sits at 2.296 eV differs materially from the Demo 23 stack, whose barrier gap is only 2.145 eV; Fig. 2d also appears to use ideal interfaces against Demo 23's 1-nm linear grading",
      "Evidence against": "all nominal layer dimensions match and the P2/P4 pair is already reproduced to 8-17 nm",
      "Explains peak positions?": "yes",
      "Explains 605 zero?": "possible",
      "Explains 1330 zero?": "possible",
      "Explains overall shape?": "yes",
      "Can test from existing data?": "partly",
      "Requires Pro rerun?": "yes",
      "Confidence": "0.72",
      "Confidence score": 0.72
    },
    {
      "Rank": 5,
      "Hypothesis": "energy-dispersion mismatch",
      "Evidence for": "24N derivatives: P2 and P4 are controlled by DeltaE_22 with dLambda/dE = -0.46 and -0.92 nm/meV (exactly the 1:2 one-/two-photon ratio), and both close on the paper with a single coherent -17/-18 meV shift of e2",
      "Evidence against": "a 17 meV offset is within band-parameter uncertainty and cannot touch P1/Z1/P3/Z2, which are energy-insensitive to machine precision",
      "Explains peak positions?": "partly",
      "Explains 605 zero?": "no",
      "Explains 1330 zero?": "no",
      "Explains overall shape?": "partly",
      "Can test from existing data?": "yes",
      "Requires Pro rerun?": "maybe",
      "Confidence": "0.55",
      "Confidence score": 0.55
    }
  ],
  "professional_rerun": "B. TARGETED PRO RUN RECOMMENDED"
}
```

## Evidence files

- C:\code\nonlinear_photonics\nextnano\demos\24_equation2_spectral_shape_audit\outputs\FEATURE_SCORECARD.csv
- C:\code\nonlinear_photonics\nextnano\demos\24_equation2_spectral_shape_audit\outputs\SIGNED_ZERO_ANALYSIS.csv
- C:\code\nonlinear_photonics\nextnano\demos\24_equation2_spectral_shape_audit\outputs\ELECTRON_HH_CANCELLATION.csv
- C:\code\nonlinear_photonics\nextnano\demos\24_equation2_spectral_shape_audit\outputs\PATHWAY_FEATURE_BREAKDOWN.csv
- C:\code\nonlinear_photonics\nextnano\demos\24_equation2_spectral_shape_audit\outputs\RESONANCE_MAP.csv
- C:\code\nonlinear_photonics\nextnano\demos\24_equation2_spectral_shape_audit\outputs\BROADENING_SENSITIVITY.csv
- C:\code\nonlinear_photonics\nextnano\demos\24_equation2_spectral_shape_audit\outputs\KGRID_SENSITIVITY.csv
- C:\code\nonlinear_photonics\nextnano\demos\24_equation2_spectral_shape_audit\outputs\KMAX_SENSITIVITY.csv
- C:\code\nonlinear_photonics\nextnano\demos\24_equation2_spectral_shape_audit\outputs\ISOTROPY_SPECTRAL_SENSITIVITY.csv
- C:\code\nonlinear_photonics\nextnano\demos\24_equation2_spectral_shape_audit\outputs\STATE_MIXING_AUDIT.csv
- C:\code\nonlinear_photonics\nextnano\demos\24_equation2_spectral_shape_audit\outputs\FINITE_K_DATA_INVENTORY.md
- C:\code\nonlinear_photonics\nextnano\demos\24_equation2_spectral_shape_audit\outputs\ROOT_CAUSE_RANKING.csv
- C:\code\nonlinear_photonics\nextnano\demos\24_equation2_spectral_shape_audit\outputs\PROFESSIONAL_RERUN_RECOMMENDATION.md

## Demo 24N causal-sensitivity evidence

- C:\code\nonlinear_photonics\nextnano\demos\24_equation2_spectral_shape_audit\outputs\RESONANCE_REACHABILITY.csv
- C:\code\nonlinear_photonics\nextnano\demos\24_equation2_spectral_shape_audit\outputs\FEATURE_CAUSAL_TRACEBACK.csv
- C:\code\nonlinear_photonics\nextnano\demos\24_equation2_spectral_shape_audit\outputs\ENERGY_FEATURE_SENSITIVITY.csv
- C:\code\nonlinear_photonics\nextnano\demos\24_equation2_spectral_shape_audit\outputs\ENERGY_FEATURE_DERIVATIVES.csv
- C:\code\nonlinear_photonics\nextnano\demos\24_equation2_spectral_shape_audit\outputs\ENERGY_SHIFT_DIRECTION_STATEMENTS.csv
- C:\code\nonlinear_photonics\nextnano\demos\24_equation2_spectral_shape_audit\outputs\PATHWAY_AMPLITUDE_SENSITIVITY.csv
- C:\code\nonlinear_photonics\nextnano\demos\24_equation2_spectral_shape_audit\outputs\NODE_CANCELLATION_SENSITIVITY.csv
- C:\code\nonlinear_photonics\nextnano\demos\24_equation2_spectral_shape_audit\outputs\PHASE_SENSITIVITY.csv
- C:\code\nonlinear_photonics\nextnano\demos\24_equation2_spectral_shape_audit\outputs\NUMERATOR_PHASE_CONTENT.json
- C:\code\nonlinear_photonics\nextnano\demos\24_equation2_spectral_shape_audit\outputs\FEATURE_K_REGION_SENSITIVITY.csv
- C:\code\nonlinear_photonics\nextnano\demos\24_equation2_spectral_shape_audit\outputs\CUTOFF_ARTIFACT_TEST.csv
- C:\code\nonlinear_photonics\nextnano\demos\24_equation2_spectral_shape_audit\outputs\EXTRAPOLATION_VALIDATION.csv
- C:\code\nonlinear_photonics\nextnano\demos\24_equation2_spectral_shape_audit\outputs\RESONANCE_BAND_EDGES.csv
- C:\code\nonlinear_photonics\nextnano\demos\24_equation2_spectral_shape_audit\outputs\SPECTRAL_FEATURE_CAUSAL_DIAGNOSIS.csv
- C:\code\nonlinear_photonics\nextnano\demos\24_equation2_spectral_shape_audit\outputs\FEATURE_CAUSAL_STATEMENTS.md
- C:\code\nonlinear_photonics\nextnano\demos\24_equation2_spectral_shape_audit\outputs\BAND_EDGES.json

The paper source is `2602.23246v1.pdf`, especially Fig. 2d (page 7) and Eq. 2/methods (pages 11-12). The plotted paper simulation is nonnegative `|chi^(2)|`; the digitization is an eye trace, not author data.
