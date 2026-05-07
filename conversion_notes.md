# Conversion Notes — Uchida Lab (Hannah's photometry + pose dataset)

## Experiment Overview

**Project**: SFARI Autism Rat Models Consortium (ARC)
**Lab**: Uchida Lab — PI: Prof. Naoshige Uchida, Harvard University
**Point person**: Hannah Phillips
**Study**: Social behavior and observational fear learning in autism rat models
**Species**: *Rattus norvegicus* — strain/genotype TBD (in subject spreadsheet)
**GitHub repo**: https://github.com/catalystneuro/uchida-lab-to-nwb
**DANDI**: Embargo mode → public on paper publication (no manuscript yet)
**Spyglass compatibility**: Required (Flatiron RSE team integration)
**Timezone**: America/New_York (Harvard, Eastern)
**Sync system**: pCampi (LabVIEW) → NIDAQ H5 file with 2-channel digital TTL at 1 kHz

Data in share: fiber photometry + 3D pose tracking + 6-camera video during
lone-animal sessions ("Lone_data"). 30-minute sessions. 3 subjects × 2 days = 6 sessions.
**Note**: `Social_data/day_1` and `day_2` were empty at inspection — Hannah plans to re-upload this week.

## Data Source

- Local path: `H:\Uchida-CN-data-share\Hannah_data\M4-M7\Lone_data\`

## Directory Structure

```
Lone_data/
  day_{1,2}/
    M{4,5,7}/
      YYMMDD_HHMMSS_M{id}.h5                    # pCampi sync (NIDAQ digital input, 1 kHz)
      BBC300_Acq_*.doric                          # Raw Doric fiber photometry (HDF5)
      interpolated_campy_and_doric_data.mat       # Raw interpolated photometry (lab pipeline)
      DANNCE/save_data_AVG0.mat                   # 3D pose predictions (23 keypoints)
      calibration/
        calibration.json                          # 6-camera intrinsics + extrinsics
        hires_camN_params.mat                     # per-camera DANNCE calibration
      videos/
        Camera{1..6}/
          0.mp4                                   # H.264 video, 1920x1200 @ 50 fps, ~30 min
          frametimes.npy                          # (2, n_frames): row 0 = frame index, row 1 = elapsed seconds
          metadata.csv                            # acquisition metadata (campy)
```

## Data Streams

| Stream | Format | Acquisition | NeuroConv Interface |
| ------ | ------ | ----------- | ------------------- |
| Raw fiber photometry | Doric `.doric` (HDF5) | Doric BBC300 | `DoricFiberPhotometryInterface` (neuroconv) |
| Raw interpolated photometry | `.mat` (lab pipeline) | Uchida lab MATLAB | `DoricProcessedPhotometryInterface` (custom) — **needs revision, see below** |
| pCampi sync | Custom `.h5` (NIDAQ) | LabVIEW at 1 kHz | `PCampiSyncInterface` (custom) |
| 3D pose | DANNCE `.mat` (23 kpts) | DANNCE inference | `SDANNCEInterface` (neuroconv) |
| 6-camera video | `.mp4` per camera | Basler a2A1920-160ucPRO via campy | `ExternalVideoInterface` × 6 (neuroconv) |
| Camera calibration | JSON + `.mat` | — | not written to NWB (used by DANNCE internally) |

## Doric File Structure (raw photometry)

- `DataAcquisition/BBC300/`
  - `ROISignals/Series0001/CAM1EXC1/{ROI01,ROI02,ROI03,Time}` — ~54,456 samples (EXC1 = 568 nm, tdTomato)
  - `ROISignals/Series0001/CAM1EXC2/{ROI01,ROI02,ROI03,Time}` — ~54,455 samples (EXC2 = 473 nm, GRABDA3m)
  - `Signals/Series0001/AnalogOut/{AnalogCh1,AnalogCh2,Time}` — 1,808,137 samples (raw DAQ)
  - `Signals/Series0001/DigitalIO/{Camera1,DigitalCh1,Time}` — trigger/sync channels
    - `Camera1`: BBC300 Camera1 output pulse (~60 Hz total; used for Doric ↔ pCampi clock alignment)
- `Configurations/BBC300/ROIs/CAM{1}_EXC{1,2}/ROI{01..03}` — ROI pixel masks (100 pts)
- Root attrs: `Created: "Mon Jun 24 13:58:38 2024"`, `SoftwareName: "Doric Neuroscience Studio"`, `SoftwareVersion: "6.4.1.0"`
- **Confirmed**: EXC1 = 568 nm (tdTomato excitation), EXC2 = 473 nm (GRABDA3m excitation)
- **Open question**: Hannah reports only 2 implants (NAc + TS) but the Doric file has 3 ROI signals per excitation channel. ROI03 purpose unknown — needs clarification.

## Fiber Photometry Hardware (confirmed by Hannah)

### Excitation Sources

| | EXC1 | EXC2 |
| - | ---- | ---- |
| Wavelength (nm) | **568** | **473** |
| Power at fiber tip | **50 µW** | **50 µW** |
| Target indicator | tdTomato (emission 581 nm) | GRABDA3m (emission 520 nm) |

### Photodetector

- Model: BBC300 (Doric BFPD CMOS camera)
- Wavelength range: 350–1100 nm (approximate)
- Gain: 0 dB

### Optical Fiber Implants

| Field | ROI01 | ROI02 |
| ----- | ----- | ----- |
| Brain region | **NAc** | **Tail of Striatum (TS)** |
| Hemisphere | randomized per animal | randomized per animal |
| Part number | MFC_400/430-0.66_8.5mm_MF2.5_FLT | MFC_400/430-0.66_7.5mm_MF2.5_FLT |
| NA | 0.66 | 0.66 |
| Core diameter | 400 µm | 400 µm |
| Active length | 8.5 mm | 7.5 mm |
| Ferrule | MF2.5 | MF2.5 |
| AP (mm from bregma) | ±1.15 | ±3.15 |
| ML (mm from bregma) | ±2.2 | ±5.2 |
| DV (mm from brain surface) | −6.3 | −4.5 |
| Yaw / pitch | n/a (vertical) | n/a (vertical) |

### Fluorescent Indicators (co-injected at both ROI sites)

| Field | GRABDA3m | tdTomato |
| ----- | --------- | -------- |
| Role | Dopamine sensor | Control fluorophore |
| Manufacturer | WZ Biosciences | Addgene |
| Virus | AAV9-hSyn-DA3m (DA3.3) | AAV5-CAG-tdTomato |
| Titer (vg/mL) | ≥1×10¹³ | ≥5×10¹² |
| Injection volume | 1 µL | 1:10 dilution in GRABDA3m |
| ROI1 injection (NAc) | ±1.15 mm, ±2.2 mm, −6.5 to −7.0 mm | same |
| ROI2 injection (TS) | ±3.15 mm, ±5.2 mm, −4.75 to −5.15 mm | same |
| Hemisphere | randomized per animal | same |
| Injection dates | per animal — in spreadsheet | same |
| Emission (nm) | 520 | 581 |

## DANNCE Output (`save_data_AVG0.mat`)

- **Lone sessions**: `pred` shape = **(90000, 1, 3, 23)** — axes: (frames, animals, xyz, keypoints); `animal_index=0`
- **Social sessions**: `pred` shape = **(90000, 2, 3, 23)** — 2 animals; both to be written to NWB
- `p_max`: (90000, 23) — per-keypoint confidence
- `sampleID`: (90000,) — 0-based frame indices; used to index campy_trigger rising edges for alignment
- `data` field meaning: smoothed / ground truth — TBD

## Processed Photometry (`interpolated_campy_and_doric_data.mat`)

**Important update (2026-05-06):** Hannah clarified that this file should contain only raw
interpolated photometry signals (the Doric ROI signals resampled to video frame rate). The extra
variables (`dff_resG`, `fit_baseG`, `rawGR`, etc.) are artifacts of an old test version of her
interpolation script. She will replace the files with clean versions.

**Action needed**: Update `DoricProcessedPhotometryInterface` once clean files are available.
The interface currently reads dF/F variables that will no longer be present. The updated file will
contain the raw GRABDA3m and tdTomato signals interpolated to ~50 Hz. The per-signal ROI
mapping (which FiberPhotometryTable row each signal corresponds to) still needs to be confirmed
once Hannah provides the clean files.

Hannah can provide separately computed dF/F at a later date if needed.

## pCampi Sync File (`YYMMDD_HHMMSS_M{id}.h5`)

- `digital_input/data`: shape `(N, 2)` int16 — 2 channels at 1 kHz
- `analog_input/data`: empty
- Channel assignment (**confirmed by Hannah**):
  - **Channel 0 (`campy_trigger`)**: rising edges → camera frame timestamps (~50 Hz)
  - **Channel 1 (`rbfmc_frames`)**: rising edges → Doric BBC300 Camera1 output pulses, used for Doric clock alignment
- Session start time parsed from filename: `YYMMDD_HHMMSS` → `datetime` with `America/New_York` timezone

## Temporal Synchronization

**Reference clock**: pCampi (defines `t = 0` in NWB)

| Stream | Alignment method |
| ------ | ---------------- |
| Video (6 cameras) | campy_trigger rising edges → per-frame timestamps |
| Doric raw photometry | Doric `DigitalIO/Camera1` rising edges ↔ pCampi `rbfmc_frames` rising edges → linear interp/extrapolation |
| Interpolated photometry | Same as video (resampled to video frame rate by lab pipeline) |
| DANNCE pose | `sampleID` frame indices → campy_trigger timestamps |
| pCampi TTL | Native (written as acquisition TimeSeries at 1 kHz, `starting_time=0.0`) |

Implementation: `Phillips2025NWBConverter.temporally_align_data_interfaces()` in
`src/uchida_lab_to_nwb/phillips_2025/phillips_2025_nwbconverter.py`.

## NWB Output Structure

- **acquisition**: Raw Doric photometry (4 FiberPhotometryResponseSeries: 2 ROIs × 2 excitations) + pCampi TTL (2 TimeSeries) + video (6 ImageSeries)
- **processing/ophys**: Interpolated photometry (raw GRABDA3m + tdTomato signals at video rate)
- **processing/behavior**: DANNCE pose (PoseEstimation + Skeletons via ndx-pose)
- **lab_meta_data**: FiberPhotometryTable (ndx-fiber-photometry + ndx-ophys-devices)

Output filename convention: `sub-{subject_id}_ses-{YYMMDD_HHMMSS}_{subject_id}.nwb`

## Sessions

- Subjects: **M4, M5, M7 only** (M1, M2, M3, M6 are not part of this dataset — confirmed by Hannah)
- Days: day_1, day_2
- Condition: Lone (solo)
- Total sessions: 6
- Social condition: Hannah plans to upload data this week (2026-05-06)

## Key Dependencies

- `neuroconv` — `add-dannce-interface` branch for `SDANNCEInterface` (pending merge to main)
- `ndx-fiber-photometry`, `ndx-ophys-devices ≥ 0.3.1`, `ndx-pose`
- `DoricFiberPhotometryInterface` imported from neuroconv main (as of `reviews_part_1` branch)

## Open Questions

- [ ] **ROI03**: Why does the Doric file have 3 ROI signals per excitation channel when Hannah reports only 2 implants (NAc + TS)? Clarify with Hannah.
- [ ] **Subject metadata**: Import from `Subject metadata.xlsx` (attached to Hannah's reply) — strain, sex, DOB, weight, surgery dates per animal.
- [ ] **Clean .mat files**: Wait for Hannah to replace `interpolated_campy_and_doric_data.mat` with clean interpolated-only version; then update `DoricProcessedPhotometryInterface`.
- [ ] **Social data**: Wait for Hannah's re-upload; update conversion to handle 2-animal DANNCE arrays.
- [ ] **SFARI grant number + CC-BY-4.0 license**: Ask Nao Uchida directly.
- [ ] **ORCIDs / contributors**: Follow up when manuscript writing begins.
- [ ] **DANNCE `data` field**: Confirm meaning (smoothed predictions vs. ground truth).
