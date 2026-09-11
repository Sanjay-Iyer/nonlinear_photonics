# 28K–28M preparation validation — 2026-09-11

- Static deck/config validation: PASS.
- Installed `nextnano++_Microsoft_32bit_free.exe --parse`: PASS, no grammar errors.
- Professional solve on home laptop: **NOT EXECUTED**.
- New extension tests: **14 PASS, 0 FAIL**.
- Complete Demo28 test suite: **79 PASS, 0 FAIL**, including the original 65 tests.
- Command: `python -m pytest tests -q -p no:cacheprovider --basetemp outputs/test_extended8band_regression`.
- Synthetic software-fixture plots: four Re/Im overlay/1550-nm figures inspected;
  labels and legends fit. These live only in ignored `outputs/test_*` directories,
  are not experimental/calculated Professional results, and are not meeting figures.
- 28A–28J production studies were not rerun or rewritten. Old demos untouched.
- Equation 2 unchanged: SHA256
  `6f69da8fe002f7954f6f5013712522c9e63445f7aa5e7ac447e608e36283a460`.
- New production path imports only local Demo28 modules and Python dependencies
  already listed in `requirements.txt`. No Demo26/Condensed/Demo27 import or data
  read is used. Historical comparison data is an explicitly supplied plot reference.
- Exact acquisition deck/config/parser result: `work_laptop/`.
- Actual Professional runtime, disk usage, full-k file coverage and solver-version
  naming compatibility remain untested until WORK execution.
- Optical operator/basis conventions, selected branches and degenerate-subspace/
  spin reduction require review before interpreting the 28M Eq2 output as physics.
  The adapter refuses absent review; a full unrestricted 8-band response is not
  claimed. No new convergence, peak-shift or HH/LH conclusions are asserted.
