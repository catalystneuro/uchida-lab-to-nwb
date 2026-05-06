# Conversion Notes — Uchida Lab (Hannah's photometry + pose dataset)

## Experiment Overview
**Project**: SFARI Autism Rat Models Consortium (ARC)
**Lab**: Uchida Lab — PI: Prof. Naoshige Uchida, Harvard University
**Point person**: Hannah Phillips
**Study**: Social behavior and observational fear learning in autism rat models
**Species**: Rats (Rattus norvegicus — strain/model TBD, SFARI ARC autism models)
**GitHub repo**: https://github.com/catalystneuro/uchida-lab-to-nwb
**DANDI**: Embargo mode → public on paper publication
**Spyglass compatibility**: Required (Flatiron RSE team integration)
**Timezone**: America/New_York (Harvard, Eastern)
**Sync system**: pCampi (LabVIEW) → NIDAQ H5 file with 2-channel digital TTL at 1 kHz

Data in share: fiber photometry + 3D pose tracking + 6-camera video during
lone-animal sessions ("Lone_data", path on rig: `M1-M7_photometry/Alone`).
30-minute sessions. 3 subjects × 2 days = 6 sessions.
**Note**: `Social_data/day_1` and `day_2` are empty — likely an upload error; flagged with Hannah.

## Data Source
- Local path: `H:\Uchida-CN-data-share\Hannah_data\M4-M7\Lone_data\`

## Directory Structure
```
Lone_data/
  day_{1,2}/
    M{4,5,7}/
      YYMMDD_HHMMSS_M{id}.h5                    # pCampi sync (NIDAQ digital input, 1 kHz)
      BBC300_Acq_*.doric                          # Raw Doric fiber photometry (HDF5)
      interpolated_campy_and_doric_data.mat       # Processed photometry (lab pipeline)
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
|--------|--------|-------------|---------------------|
| Raw fiber photometry | Doric `.doric` (HDF5) | Doric BBC300 | `DoricFiberPhotometryInterface` (neuroconv) |
| Processed dF/F | `.mat` (lab pipeline) | Uchida lab MATLAB | `DoricProcessedPhotometryInterface` (custom) |
| pCampi sync | Custom `.h5` (NIDAQ) | LabVIEW at 1 kHz | `PCampiSyncInterface` (custom) |
| 3D pose | DANNCE `.mat` (23 kpts) | DANNCE inference | `SDANNCEInterface` (neuroconv) |
| 6-camera video | `.mp4` per camera | Basler a2A1920-160ucPRO via campy | `ExternalVideoInterface` × 6 (neuroconv) |
| Camera calibration | JSON + `.mat` | — | not written to NWB (used by DANNCE internally) |

## Doric File Structure (raw photometry)
- `DataAcquisition/BBC300/`
  - `ROISignals/Series0001/CAM1EXC1/{ROI01,ROI02,ROI03,Time}` — ~54,456 samples (excitation 1)
  - `ROISignals/Series0001/CAM1EXC2/{ROI01,ROI02,ROI03,Time}` — ~54,455 samples (excitation 2)
  - `Signals/Series0001/AnalogOut/{AnalogCh1,AnalogCh2,Time}` — 1,808,137 samples (raw DAQ)
  - `Signals/Series0001/DigitalIO/{Camera1,DigitalCh1,Time}` — trigger/sync channels
    - `Camera1`: BBC300 Camera1 output pulse (~60 Hz total; used for Doric ↔ pCampi clock alignment)
- `Configurations/BBC300/ROIs/CAM{1}_EXC{1,2}/ROI{01..03}` — ROI pixel masks (100 pts)
- Root attrs: `Created: "Mon Jun 24 13:58:38 2024"`, `SoftwareName: "Doric Neuroscience Studio"`, `SoftwareVersion: "6.4.1.0"`
- Interpretation: 2 excitation wavelengths (EXC1 ≈ 470 nm signal, EXC2 ≈ 415 nm isosbestic — TBD) × 3 ROIs (3 fiber implants, brain regions TBD)

## DANNCE Output (`save_data_AVG0.mat`)

- `pred`: (90000, 3, 23) — 3D predictions, axes: (frames, xyz, keypoints)
- `data`: (90000, 3, 23) — smoothed / ground truth? TBD
- `p_max`: (90000, 23) — per-keypoint confidence
- `sampleID`: (90000,) — 0-based frame indices into the video; used to index into campy_trigger rising edges for alignment
- **Lone sessions**: `animal_index=0` (single animal); confirmed in `convert_session.py`
- **Social sessions**: animal_index scheme TBD (2 animals expected); data not yet available (empty share)

## Processed Photometry (`interpolated_campy_and_doric_data.mat`)

- 90,071 samples — matches video frame count (~50 Hz × 30 min)
- Variables written to NWB `processing/ophys`:

| Variable | Meaning (TBD — awaiting Hannah) |
| -------- | ------------------------------- |
| `rawG` | Raw green fluorescence (EXC1 channel) |
| `rawGR` | Raw green reference / isosbestic (EXC2 channel)? |
| `rawR` | Raw red fluorescence |
| `rawTd` | Raw TdTomato reference channel? |
| `vG`, `vG2` | Demodulated green signal (channels 1 & 2)? |
| `vR`, `vR2` | Demodulated red signal (channels 1 & 2)? |
| `resG`, `resG2` | Residuals after baseline fit (green) |
| `fit_baseG`, `fit_baseG2` | Fitted photobleaching baseline (green) |
| `dff_resG`, `dff_resG2` | Final dF/F (green channels 1 & 2) |
| `bValidSignal`, `bValidSignal2` | Validity masks |
| `b`, `b2`, `k` | Fit coefficients |

All processed signals are interpolated to the video frame rate. The per-signal ROI mapping
(which FiberPhotometryTable row each corresponds to) uses row 0 as a placeholder — needs
confirmation from Hannah before release.

## pCampi Sync File (`YYMMDD_HHMMSS_M{id}.h5`)

- `digital_input/data`: shape `(N, 2)` int16 — 2 channels at 1 kHz
- `analog_input/data`: empty
- Channel assignment (implemented; awaiting lab confirmation):
  - **Channel 0 (`campy_trigger`)**: rising edges → camera frame timestamps (~50 Hz)
  - **Channel 1 (`rbfmc_frames`)**: rising edges → Doric BBC300 Camera1 output pulses (~60 Hz), used for Doric clock alignment
- Session start time parsed from filename: `YYMMDD_HHMMSS` → `datetime` with `America/New_York` timezone

## Temporal Synchronization

**Reference clock**: pCampi (defines `t = 0` in NWB)

| Stream | Alignment method |
| ------ | ---------------- |
| Video (6 cameras) | campy_trigger rising edges → per-frame timestamps |
| Doric raw photometry | Doric `DigitalIO/Camera1` rising edges ↔ pCampi `rbfmc_frames` rising edges → linear interp/extrapolation |
| Processed dF/F | Same as video (already interpolated to video rate by lab pipeline) |
| DANNCE pose | `sampleID` frame indices → campy_trigger timestamps |
| pCampi TTL | Native (written as acquisition TimeSeries at 1 kHz, `starting_time=0.0`) |

Implementation: `Phillips2025NWBConverter.temporally_align_data_interfaces()` in
`src/uchida_lab_to_nwb/phillips_2025/phillips_2025_nwbconverter.py`.

## NWB Output Structure

- **acquisition**: Raw Doric photometry (6 FiberPhotometryResponseSeries) + pCampi TTL (2 TimeSeries) + video (6 ImageSeries)
- **processing/ophys**: Processed photometry (8 FiberPhotometryResponseSeries)
- **processing/behavior**: DANNCE pose (PoseEstimation + Skeletons via ndx-pose)
- **lab_meta_data**: FiberPhotometryTable (ndx-fiber-photometry + ndx-ophys-devices)

Output filename convention: `sub-{subject_id}_ses-{YYMMDD_HHMMSS}_{subject_id}.nwb`

## Sessions

- Subjects: M4, M5, M7 (M6 missing from this share; M1–M3 status TBD)
- Days: day_1, day_2
- Condition: Lone (solo)
- Total sessions: 6
- Social condition: share exists but folders are empty (flagged with Hannah)

## Key Dependencies

- `neuroconv` — `add-dannce-interface` branch for `SDANNCEInterface` (pending merge to main)
- `ndx-fiber-photometry`, `ndx-ophys-devices ≥ 0.3.1`, `ndx-pose`
- `DoricFiberPhotometryInterface` now imported from neuroconv main (as of `reviews_part_1` branch)

## Open Questions (for Hannah)

- [ ] Subject metadata: strain/genotype, sex, DOB, weight, experimental group for M4, M5, M7
- [ ] Are M1, M2, M3, M6 part of this dataset?
- [ ] Fiber photometry: EXC1 and EXC2 exact excitation wavelengths (nm)
- [ ] Fiber photometry: LED power at fiber tip (mW)
- [ ] Fiber photometry: Doric BBC300 camera gain setting
- [ ] Fiber photometry: Brain regions and hemisphere for each ROI (ROI01, ROI02, ROI03)
- [ ] Fiber photometry: Fiber implant coordinates (AP/ML/DV from bregma) per ROI
- [ ] Fiber photometry: Fluorescent indicator identity (GCaMP variant? dLight? GRAB-DA?)
- [ ] Fiber photometry: Virus construct, titer, injection coordinates
- [ ] pCampi channel assignment: confirm Ch0 = campy_trigger, Ch1 = rbfmc_frames
- [ ] Processed photometry: exact meaning of rawG, rawGR, rawR, rawTd, vG, vG2, vR, vR2 and which ROI each maps to
- [ ] Processed photometry: share MATLAB/Python dF/F pipeline script
- [ ] DANNCE: confirm `data` field meaning (smoothed predictions? ground truth?)
- [ ] DANNCE Social sessions: how many animals in the array, how to identify each
- [ ] Social_data: re-upload needed (empty folders)
- [ ] DANDI: ORCIDs for all contributors, SFARI grant number, related publication DOI
- [ ] Publication: is there a manuscript or preprint in preparation?
