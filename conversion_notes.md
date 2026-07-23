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
| Raw fiber photometry | Doric `.doric` (HDF5) | Doric BBC300 | `DoricFiberPhotometryInterface` × 2 (neuroconv) — one instance per channel, each writing a 2-column (NAc, TS) `FiberPhotometryResponseSeries` |
| Raw interpolated photometry | `.mat` (lab pipeline) | Uchida lab MATLAB | `ProcessedFiberPhotometryInterface` |
| pCampi sync | Custom `.h5` (NIDAQ) | LabVIEW at 1 kHz | `PCampiSyncInterface` (custom) |
| 3D pose + 6-camera video | DANNCE `.mat` (23 kpts) + `.mp4` per camera | DANNCE inference; Basler a2A1920-160ucPRO via campy | `DANNCEConverter` (neuroconv) — combines pose + per-camera source video + calibrated Device, linked automatically |
| Camera calibration | JSON + `.mat` (`hires_camN_params.mat`) | — | consumed by `DANNCEConverter` (`calibration_path`) to create calibrated camera Devices |

**2026-07-23 update:** Migrated pose/video from `SDANNCEInterface` + 6× `ExternalVideoInterface`
to the newly-added `neuroconv.converters.DANNCEConverter` (pattern taken from
`olveczky-lab-to-nwb`'s `klibaite_2025_rat` conversion), which wires video-to-DANNCE linking and
calibrated camera Devices internally. Also updated `DoricFiberPhotometryInterface` usage to its
current signature (`stream_names` + `metadata_key`, one interface per response series instead of
one interface for all 4 channels) — this had drifted since the interface was last touched, so
`_metadata/fiber_photometry.yaml` was rewritten to match the current top-level
`Devices`/`DeviceModels`/`FiberPhotometryTable` metadata schema. Required upgrading `ndx-pose` to
≥0.3.0 (installed 0.4.0, editable from local checkout) — the DANNCE interface hard-requires it.
Verified end-to-end (stub conversion + nwbinspector) against the real M4 day_1 session data.

Also renamed all Doric metadata/device/interface keys from raw hardware channel names to
functional roles (confirmed with the team): `EXC1` → `control` (tdTomato), `EXC2` →
`dopamine_signal` (GRABDA3m); `ROI01` → `NAc`, `ROI02` → `TS` (also replaced the
`FiberPhotometryTable` `location` value `"Tail of Striatum"` with `"TS"`). Applies throughout
`nwbconverter.py`, `convert_session.py`, and `_metadata/fiber_photometry.yaml` — e.g.
`excitation_source_EXC1` → `excitation_source_control`, `optical_fiber_ROI01` →
`optical_fiber_NAc`.

**2026-07-23 (later same day):** Collapsed the 4 per-ROI `DoricFiberPhotometryInterface`
instances (`DoricControlNAc`, `DoricDopamineSignalNAc`, `DoricControlTS`,
`DoricDopamineSignalTS`) into 2 per-channel instances (`DoricControl`, `DoricDopamineSignal`),
each passing a 2-element `stream_names` list (NAc, TS ROI streams for that channel) so the
interface column-stacks them into one `FiberPhotometryResponseSeries` of shape
`(n_times, 2)` instead of writing 2 separate 1-column series. Both ROI streams under a given
excitation channel share the same Doric `Time` array, so a single shared timestamp array is
still correct. `FiberPhotometryTable` itself is unchanged (still 4 rows, one per ROI × channel);
only the response series were merged, with `fiber_photometry_table_region` set to
`[row_..._NAc, row_..._TS]` (order matches the data columns). Final acquisition:
`FiberPhotometryControl`, `FiberPhotometryDopamineSignal` (2 series total, not 4). Verified
end-to-end against real M4 day_1 data — data shapes and table-region row order confirmed
correct (`[NAc, TS]`).

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

## Processed Photometry

Hannah's clean replacement files have arrived and were inspected directly (HDF5/v7.3, via
`h5py`) against the real M4 day_1 session
(`H:\Uchida-CN-data-share\Hannah_data\M4-M7\Lone_data\day_1\M4\`). There are now **two separate
files** where there used to be one — they are not alternates of each other, they carry different
content:

### `interpolated_campy_and_doric.mat` — raw ROI traces, interpolated to video rate

v7.3 MAT-file containing one struct, `interpolated_data`, with two fields:

- `channel_names`: 2 entries, `"CAM1EXC1"`, `"CAM1EXC2"` — these are the same stream-name roots
  used by `DoricFiberPhotometryInterface` on the raw `.doric` file, i.e. **control** (tdTomato,
  568 nm) and **dopamine_signal** (GRABDA3m, 473 nm).
- `roi_traces_interpolated`: 2 entries (one per channel above), each shaped **(90074, 3)**
  float64 — column order matches the 3 raw Doric ROI signals (ROI01, ROI02, ROI03) for that
  excitation channel. Values are on the same scale as the raw `.doric` ROI signals (tens of
  thousands to low hundreds), confirming these are **raw fluorescence, not dF/F** — exactly what
  Hannah said the clean file would contain.
- No embedded timestamps — like the old interface, alignment to the video frame clock still
  needs to come from `frametimes.npy` (or the pCampi-aligned timestamps the converter already
  computes for video/DANNCE).
- ROI03 is still present and still unidentified (open question below carries over unchanged).

This maps cleanly onto `BaseFiberPhotometryInterface`'s stream model: `stream_names` = the two
channel names, `_get_stream_data` dereferences `roi_traces_interpolated[i]` for that channel
(optionally sliced to columns `[0, 1]` = NAc, TS via `stream_indices`, dropping ROI03 the same
way the raw Doric interfaces do), `_get_stream_timestamps` returns the shared video-rate
timestamps for all channels.

### `processed_dff.mat` — computed dF/F, single trace only

A second, separate v7.3 file containing exactly **one** variable, `dff_resG`, shaped **(1,
90071)** float64. This is a single already-computed dF/F trace — not per-ROI, not per-channel,
no channel/ROI labels anywhere in the file. Name suggests "green" (dopamine_signal channel) but
which ROI (NAc vs TS) or whether it's already a combination is unconfirmed.

**Open question added**: ask Hannah (a) which ROI/channel `dff_resG` corresponds to, (b) why
there is only one dF/F trace when there are 4 raw ROI×channel combinations (NAc/TS ×
control/dopamine_signal) upstream, and (c) whether more dF/F traces are coming later or this is
the final intended set.

### Interface refactor (done, 2026-07-23)

`DoricProcessedPhotometryInterface` (custom `BaseDataInterface`, hand-rolled `sio.loadmat` +
manual `FiberPhotometryResponseSeries` construction) has been replaced by
`ProcessedFiberPhotometryInterface` (`interfaces/processed_fiber_photometry_interface.py`),
inheriting `BaseFiberPhotometryInterface` (pattern copied from neuroconv's
`DoricFiberPhotometryInterface`) so it shares the same stream/timestamps/metadata-key/table-region
machinery as the raw Doric interfaces instead of duplicating it. Two instances, one per channel
(`ProcessedControl`, `ProcessedDopamineSignal`), each reading `interpolated_campy_and_doric.mat`
with `stream_names="CAM1EXCn"` and `stream_indices=[0, 1]` (keeping NAc/TS, dropping the
unidentified third ROI column, same convention as the raw interfaces). Since
`BaseFiberPhotometryInterface.add_to_nwbfile` always writes to `acquisition`, this interface
overrides `add_to_nwbfile` to reuse the same device/table-region helpers but write into
`processing/ophys` instead (this data is a processed derivative, not raw acquisition).
`processed_dff.mat` (single untagged dF/F trace) is intentionally **not** handled by this
interface yet — decided to skip it until Hannah answers the open question above about what
`dff_resG` actually is.

Also fixed a latent bug found in the same pass: `convert_session.py` was looking for
`interpolated_campy_and_doric_data.mat`, but the real file on disk is
`interpolated_campy_and_doric.mat` (no `_data` suffix) — so this interface was silently never
firing before. Added two new metadata entries (`fiber_photometry_processed_control`,
`fiber_photometry_processed_dopamine_signal`) to `metadata/fiber_photometry.yaml`, reusing the
same `FiberPhotometryTable` rows as the raw series.

Verified end-to-end against the real M4 day_1 session (stub conversion): output NWB has
`FiberPhotometryProcessedControl`/`FiberPhotometryProcessedDopamineSignal` in
`processing/ophys`, shape `(n, 2)`, table regions `[NAc, TS]` rows matching the raw acquisition
series; `nwbinspector --config dandi` reports only pre-existing DANNCE/video issues, nothing
related to fiber photometry.

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

- `neuroconv` — `DANNCEConverter` / `DANNCEInterface` (local checkout, `C:\Users\amtra\CatalystNeuro\neuroconv`)
- `ndx-fiber-photometry`, `ndx-ophys-devices ≥ 0.3.1`
- `ndx-pose ≥ 0.3.0` — required by `DANNCEInterface`; installed as editable from
  `C:\Users\amtra\CatalystNeuro\ndx-pose` (0.4.0) since the conda env had 0.2.2
- `DoricFiberPhotometryInterface` imported from neuroconv main (as of `reviews_part_1` branch)

## Open Questions

- [ ] **ROI03**: Why does the Doric file have 3 ROI signals per excitation channel when Hannah reports only 2 implants (NAc + TS)? Clarify with Hannah.
- [ ] **Subject metadata**: Import from `Subject metadata.xlsx` (attached to Hannah's reply) — strain, sex, DOB, weight, surgery dates per animal.
- [x] **Clean .mat files**: Received and inspected, see "Processed Photometry — clean files received" above. Now two files: `interpolated_campy_and_doric.mat` (raw ROI traces, 2 channels × 3 ROIs, interpolated to video rate) and `processed_dff.mat` (single untagged dF/F trace, `dff_resG`).
- [ ] **`dff_resG` identity**: Which ROI/channel does the single dF/F trace in `processed_dff.mat` correspond to? Why only one trace instead of 4 (2 ROIs × 2 channels)? Ask Hannah.
- [ ] **Social data**: update conversion to handle 2-animal DANNCE arrays.
- [ ] **SFARI grant number + CC-BY-4.0 license**: Ask Nao Uchida directly.
- [ ] **ORCIDs / contributors**: Follow up when manuscript writing begins.
- [ ] **DANNCE `data` field**: Confirm meaning (smoothed predictions vs. ground truth).
