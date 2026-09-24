# Demo 29: next WORK session, one command per step

Run these in PowerShell on the licensed WORK laptop **after this code is
published and pulled there**. Each Python line is a separate command. The
runner prints status about every 15 seconds; it never estimates percent done.
Every output folder is new and the scripts refuse overwrites.

## Enter Demo 29 and check decks

```powershell
Set-Location C:\Code\optics\nextnano\nonlinear_photonics\nextnano\demos\29_temperature_chi2_study
python scripts\run_nextnano.py --check
```

## Job 1: 300 K target-aligned full-8-band pilot

```powershell
python scripts\run_nextnano.py --run --temperature 300 --pilot-finite-k --output nextnano\work_runs\pilot_target_300K_trial2
```

The run automatically writes a debug ZIP and prints its path. For a second
debug ZIP at a predictable path, run:

```powershell
python scripts\collect_debug.py --input nextnano\work_runs\pilot_target_300K_trial2 --temperature 300 --run-id target300_trial2 --output-dir nextnano\transfer\pilot_target_300K_debug_trial2
```

Send this small ZIP first:

```text
nextnano\transfer\pilot_target_300K_debug_trial2\demo29_300K_debug_target300_trial2.zip
```

If the diagnostic reports at least three complete target-path frames, create
the full raw pilot ZIP for home state-tracking and matrix analysis:

```powershell
python scripts\package_pilot.py --input nextnano\work_runs\pilot_target_300K_trial2 --zip nextnano\transfer\demo29_300K_target_pilot_raw.zip
```

Keep the original `nextnano\work_runs\pilot_target_300K_trial2` folder on WORK.
The full ZIP includes all solver outputs, the executed deck, logs and a hash
manifest. If packaging refuses due to insufficient target-path coverage, send
only the debug ZIP and its printed error. Do not run full-8-band 100/500 K yet.

## Job 2: 100 K historical mixed-model control

```powershell
python scripts\run_nextnano.py --run --temperature 100
```

```powershell
python scripts\transfer_mixed.py --pack nextnano\work_runs\100K
```

Send `nextnano\transfer\demo29_100K_mixed_raw.zip`. The run has a standard
8-band dispersion job plus a 100 K single-band job. The ZIP contains the eight
scientific files needed by the historical mixed calculation, executed decks,
metadata, logs and checksums.

## Job 3: 500 K historical mixed-model control

```powershell
python scripts\run_nextnano.py --run --temperature 500
```

```powershell
python scripts\transfer_mixed.py --pack nextnano\work_runs\500K
```

Send `nextnano\transfer\demo29_500K_mixed_raw.zip`.

## HOME after copying ZIPs into nextnano_raw

Run each line from the HOME Demo 29 folder. The existing 300 K mixed result is
already in `outputs\29C_mixed_control\300K`; recalculate it from the original
HOME solver run only if that output is missing.

```powershell
python scripts\transfer_mixed.py --unpack C:\code\nonlinear_photonics\nextnano_raw\demo29_100K_mixed_raw.zip
```

```powershell
python scripts\transfer_mixed.py --unpack C:\code\nonlinear_photonics\nextnano_raw\demo29_500K_mixed_raw.zip
```

```powershell
python scripts\calculate_mixed.py --input C:\code\nonlinear_photonics\nextnano_raw\demo29_100K_mixed_raw --output outputs\29C_mixed_control\100K
```

```powershell
python scripts\calculate_mixed.py --input C:\code\nonlinear_photonics\nextnano_raw\demo29_500K_mixed_raw --output outputs\29C_mixed_control\500K
```

```powershell
python scripts\plot_temperature.py --model mixed
```

```powershell
python scripts\plot_electronic_temperature.py
```

The plot command writes Re, Im, |Re| and |χ²| overlays, a 1550 nm table and
k=0 transition energies. Feature positions and zero crossings are in each
temperature's `metadata.json`. The 29C results remain historical mixed-model
controls, including single-band k=0 matrices and `M(k)=M(0)`.

If `demo29_300K_target_pilot_raw.zip` was produced, also unpack it into
`C:\code\nonlinear_photonics\nextnano_raw` on HOME and run:

```powershell
python scripts\analyze_pilot.py --input C:\code\nonlinear_photonics\nextnano_raw\pilot_target_300K_trial2 --output outputs\29A_full8band_baseline\target_pilot_trial2
```

This writes state-tracking flags and complex growth-position/component-overlap
matrices for the exported target-path points. It does not calculate a
full-8-band χ² while the optical operator is unresolved.
