# Lean acquisition/transfer validation — 2026-09-11

- Current default: 601 k points to 0.20 pi/a; 8 electron + 16 valence states.
- Full lean deck: static PASS and installed nextnano++ Free `--parse` PASS.
- Three-point pilot deck: static PASS and Free `--parse` PASS.
- Professional execution on HOME: **none**.
- Complete Demo28 tests: **90 PASS, 0 FAIL** (11 new compact/pilot tests).
- Command: `python -m pytest tests -q -p no:cacheprovider --basetemp outputs/test_lean_verified`.
- Tests exercise exact parsed-number raw/compact round trips, identical 28L
  matrices for text versus compact input, missing/corrupt frames, original-data
  preservation, state-ID checks, existing-folder refusal, source-config validation,
  byte-budget failure without truncation, separate pilot plans and rejection of
  pilot data for production analysis. A fake-solver test checks auto-pack end to end.
- Synthetic tests are not Professional output or new physical results.
- Actual full-grid output support, size and runtime remain pending WORK pilot/run.
- Estimated wavefunction binary payload at 281 spatial nodes: 518,802,432 bytes,
  before lossless compression and supporting metadata. Full transfer target is
  1,000,000,000 bytes; the packer validates actual folder size and fails if exceeded.
- Original WORK text remains larger (estimated 2.4–2.5 GB for essential envelopes)
  and is never deleted. Compact numerical storage does not preserve text formatting.
- Existing 28A–28J and original 28K `work_laptop/` artifacts retained. New plans
  live in `work_laptop_lean/` and its `pilot/` child.
- Equation 2 is unchanged; the compact path uses no previous-demo physics inputs.
- PyYAML is now explicitly declared for the existing work-machine YAML lookup.
- Optical-operator/branch/spin review and high-k convergence assessment remain
  separate future tasks; reducing output does not establish those physics claims.
