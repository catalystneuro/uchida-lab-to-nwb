# Conversion Notes — Uchida Lab (Hannah's photometry + pose dataset)

## Experiment Overview
Fiber photometry + 3D pose tracking + multi-camera video during lone-animal
behavior (condition folder named `Lone_data`, path on acquisition rig contained
`M1-M7_photometry/Alone`). 30-minute sessions per subject per day, 2 days.
Experimenter: Hannah. Lab: Uchida (Harvard).

> TO CONFIRM with user: task description, brain region(s) recorded, indicator
> (GCaMP?), subject species, whether social data also exists, publication/DOI.

## Data Source
- Local path: `H:\Uchida-CN-data-share\Hannah_data\M4-M7\Lone_data\`

## Directory Structure
```
Lone_data/
  day_{1,2}/
    M{4,5,7}/
      240624_135840_M4.h5            # DAQ sync (Campy's Arduino/NIDAQ dump)
      BBC300_Acq_0093.doric          # Raw Doric fiber photometry (HDF5)
      interpolated_campy_and_doric_data.mat   # Processed photometry (derivative)
      DANNCE/save_data_AVG0.mat      # 3D pose predictions (23 keypoints)
      calibration/
        calibration.json             # 6-camera intrinsics + extrinsics
        hires_camN_params.mat        # per-camera DANNCE calibration
      videos/
        Camera{1..6}/
          0.mp4                      # H.264 video, 1920x1200 @ 50 fps, ~30 min
          frametimes.mat / .npy      # per-frame timestamps
          metadata.csv               # acquisition metadata (campy)
```

## Data Streams
| Stream | Format | Acquisition | NeuroConv Interface |
|--------|--------|-------------|---------------------|
| Raw fiber photometry | Doric `.doric` (HDF5) | Doric BBC300 | `DoricFiberPhotometryInterface` (to confirm, or custom) |
| DAQ sync signals | Custom `.h5` (h5py) | Campy (Arduino/NIDAQ) | custom TimeSeries |
| 6-camera video | `.mp4` per camera | Basler a2A1920-160ucPRO via Campy | `VideoInterface` (per-camera) |
| 3D pose | DANNCE `.mat` (23 kpts) | DANNCE inference | custom interface (reuse olveczky-lab-to-nwb) |
| Camera calibration | JSON + `.mat` | — | write as scratch / reuse olveczky pattern |
| Processed dF/F | `.mat` (derivative) | custom pipeline | custom ProcessingModule (optional) |

## Doric file structure (raw photometry)
- `DataAcquisition/BBC300/`
  - `ROISignals/Series0001/CAM1EXC1/{ROI01,ROI02,ROI03,Time}` — ~54,456 samples (excitation 1)
  - `ROISignals/Series0001/CAM1EXC2/{ROI01,ROI02,ROI03,Time}` — ~54,455 samples (excitation 2)
  - `Signals/Series0001/AnalogOut/{AnalogCh1,AnalogCh2,Time}` — 1,808,137 samples (raw DAQ)
  - `Signals/Series0001/DigitalIO/{Camera1,DigitalCh1,Time}` — trigger/sync channels
- `Configurations/BBC300/ROIs/CAM{1}_EXC{1,2}/ROI{01..03}` — ROI pixel masks (100 pts)
- Root attrs: `Created: "Mon Jun 24 13:58:38 2024"`, `SoftwareName: "Doric Neuroscience Studio"`, `SoftwareVersion: "6.4.1.0"`
- Interpretation: 2 excitation wavelengths × 3 ROIs (fibers or brain regions per subject)
  → likely signal + isosbestic or two-color imaging. Confirm with user.

## DANNCE output
`save_data_AVG0.mat`:
- `pred`: (90000, 3, 23) — 3D predictions, (frames, xyz, keypoints)
- `data`: (90000, 3, 23) — ground truth or smoothed? confirm
- `p_max`: (90000, 23) — per-keypoint confidence
- `sampleID`: (90000,) — frame indices

## Interpolated/processed photometry (`interpolated_campy_and_doric_data.mat`)
- 90,071 samples (≈ matches the 90,000-frame video)
- `rawG`, `rawGR`, `rawR`, `rawTd` — raw channels
- `vG`, `vG2`, `vR`, `vR2` — signal after some transform (demodulated?)
- `resG`, `resG2`, `fit_baseG`, `fit_baseG2`, `dff_resG`, `dff_resG2` — baseline fit + dF/F
- `bValidSignal`, `bValidSignal2` — validity masks
- `b`, `b2`, `k` — fit coefficients
- `adata`, `interpolated_data` — mat structs
→ This is a lab-specific post-processed derivative. We will prefer the raw
  `.doric` file and add dF/F via `ndx-fiber-photometry` ProcessingModule OR
  mirror the lab's processed traces as a secondary ProcessingModule if needed.

## DAQ sync (`240624_135840_M4.h5`)
- `digital_input/data`: shape (1,820,000, 2) int16 — 2 channels at ~1 kHz
- `analog_input/data`: empty
- No attrs. Assume Arduino-driven camera trigger + photometry sync. Confirm
  sampling rate and channel assignment with user.

## Sessions
- Subjects: M4, M5, M7 (M6 missing from this share)
- Days: day_1, day_2
- Condition: Lone (solo). User path suggests a "Social" condition may exist too.
- Total sessions observed: 6

## Existing Resources
- [ ] Publication: ?
- [ ] Existing public data: ?
- [ ] Analysis code (dF/F pipeline): ? — clearly exists, produced the `.mat`
- [ ] Ground truth / project info in DANNCE pipeline
- Prior similar conversion: `olveczky-lab-to-nwb` (same DANNCE + 6-cam + campy stack)

## Open Questions (for user)
- [ ] Lab PI confirmation: Naoshige Uchida, Harvard?
- [ ] Experimenter: Hannah's full name? Email? ORCID?
- [ ] Subject species (Mus musculus?), strain, sex, DOB for M4–M7
- [ ] Brain region(s) recorded by photometry, indicator (GCaMP6/7/8?), fiber type
- [ ] Excitation wavelengths (CAM1EXC1, CAM1EXC2 — 470 + 415? 470 + 560?)
- [ ] What do the 3 ROIs per excitation represent? (3 fibers? 3 anatomical sites?)
- [ ] Behavior during Lone session: open field? What was the animal doing?
- [ ] Digital channels in `*.h5`: what are channels 0 and 1?
- [ ] Is there a matching "Social" dataset? (path suggests yes)
- [ ] Is there a manuscript/preprint? DOI?
- [ ] Analysis code repo / processing pipeline code available?
- [ ] DANDI instance: sandbox first, then main archive?
