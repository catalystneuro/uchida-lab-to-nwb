# Conversion Notes — Uchida Lab (Phillips 2025)

## Project Overview

Conversion of fiber photometry + 3D pose + multi-camera video recordings from the Uchida Lab
(Harvard University) to NWB. Part of the **SFARI Autism Rat Models Consortium (ARC)**, studying
social behavior and observational fear learning in autism rat models. The behavioral setup
(6-camera video + DANNCE pose) overlaps substantially with the Olveczky lab conversion (same
facility; see `olveczky-lab-to-nwb`).

- **Lab POC:** Hannah Phillips. **PI:** Prof. Naoshige Uchida, Harvard University.
- **Repo:** <https://github.com/catalystneuro/uchida-lab-to-nwb>
- **DANDI:** Embargo mode planned → public on paper publication (no manuscript yet).
- **Spyglass compatibility:** required (Flatiron RSE team integration).
- **Timezone:** America/New_York (Harvard, Eastern).
- **Sync system:** pCampi (LabVIEW) → NIDAQ H5 file, 2-channel digital TTL at 1 kHz.
- Data in the share: fiber photometry + 3D pose tracking + 6-camera video during lone-animal
  sessions (`Lone_data`), 30-minute sessions, 3 subjects × 2 days = 6 sessions. A `Social_data/`
  condition (2 rats per session) is now also in the share (`Social_data/day_1`, `Social_data/day_2`),
  3 subjects × 2 days = 6 subject-session directories.

## Data Streams

| Stream | Format | Acquisition | NeuroConv Interface |
|---|---|---|---|
| Raw fiber photometry | Doric `.doric` (HDF5) | Doric BBC300 | `DoricFiberPhotometryInterface` (neuroconv) — one instance per channel (control, dopamine_signal), each writing a 2-column (NAc, TS) `FiberPhotometryResponseSeries` |
| Lab-processed (interpolated) photometry | `interpolated_campy_and_doric.mat` (MATLAB v7.3) | Uchida lab MATLAB pipeline | `ProcessedFiberPhotometryInterface` (custom) — one instance per channel, writes to `processing/ophys`, reusing the raw interfaces' `FiberPhotometryTable` |
| pCampi sync | Custom `.h5` (NIDAQ) | LabVIEW at 1 kHz | `PCampiSyncInterface` (custom) — one instance per digital channel (`channel_name` required at init; `get_available_channels()` discovers them); also the source of `session_start_time` |
| 3D pose + 6-camera video | DANNCE `.mat` (23 keypoints) + `.mp4` per camera | DANNCE inference; Basler a2A1920-160ucPRO via campy | `DANNCEConverter` (neuroconv) — combines pose, per-camera source video, and calibrated `Device`s |
| Camera calibration | JSON + `.mat` (`hires_camN_params.mat`) | — | consumed by `DANNCEConverter` (`calibration_path`) |
| Subject metadata | XLSX (lab-provided) | `Subject metadata.xlsx` | `Subject`, via `utils/subject_metadata.get_subject_metadata()` |

Not converted:
- **`processed_dff.mat`** (single untagged dF/F trace, `dff_resG`) — not per-ROI/per-channel, no
  labels; skipped until the lab clarifies what it represents (see Open Questions).
- **`Channels.csv`** (per-animal, 21.6M rows) — derived envelope/RMS feature used only as sleep/
  seizure-scoring input, not raw data; will not be republished.

## Directory Structure

Raw data share (e.g. `H:/Uchida-CN-data-share/Hannah_data/M4-M7/Lone_data/`):

```text
Lone_data/
  day_{1,2}/
    M{4,5,7}/
      YYMMDD_HHMMSS_M{id}.h5                # pCampi sync (NIDAQ digital input, 1 kHz)
      BBC300_Acq_*.doric                     # raw Doric fiber photometry (HDF5)
      interpolated_campy_and_doric.mat       # lab-processed photometry, interpolated to video rate
      DANNCE/save_data_AVG0.mat              # 3D pose predictions (23 keypoints)
      calibration/
        calibration.json                     # 6-camera intrinsics + extrinsics
        hires_camN_params.mat                # per-camera DANNCE calibration
      videos/
        Camera{1..6}/
          0.mp4                              # H.264 video, 1920x1200 @ 50 fps, ~30 min
          frametimes.npy                     # (2, n_frames): row 0 = frame index, row 1 = elapsed seconds
          metadata.csv                       # acquisition metadata (campy), incl. frameRate
```

`Social_data/` (`H:/Uchida-CN-data-share/Hannah_data/M4-M7/Social_data/`) mirrors `Lone_data/` per
subject-session directory, with two differences:

```text
Social_data/
  day_{1,2}/
    M{4,5,7}/
      YYMMDD_HHMMSS_M{id}.h5                # pCampi sync — shared between the two paired
                                             # subjects on day_1 (M5 and M7 both point at the
                                             # same 240716_160054_M5.h5/BBC300_Acq_0146.doric);
                                             # each subject has its own file on day_2
      BBC300_Acq_*.doric                     # raw Doric fiber photometry
      interpolated_campy_and_doric.mat       # lab-processed photometry
      processed_dff.mat                      # single untagged dF/F trace (not converted; also
                                              # present in Lone_data)
      sDANNCE/predict05/                     # 3D pose predictions — note folder name `sDANNCE`
        save_data_AVG0.mat                   # (not `DANNCE`, as in Lone_data), plus intermediate
        save_data_AVG.mat                    # DANNCE pipeline artifacts (`init_save_data_AVG.mat`,
        init_save_data_AVG.mat               # `com3d_used.mat`, `M{id}day{n}_save_data_AVG0.mat`,
        com3d_used.mat                       # `stats_dannce_predict.log`) not present in Lone_data
        M{id}day{n}_save_data_AVG0.mat
        stats_dannce_predict.log
      calibration/                           # same as Lone_data
      videos/                                # same as Lone_data (6 camera subfolders)
```

`pred`/`data` arrays in `sDANNCE/predict05/save_data_AVG0.mat` are shape `(90000, 2, 3, 23)` —
confirmed both animals are written (vs. `(90000, 1, 3, 23)` in Lone_data).

Repository (`src/uchida_lab_to_nwb/phillips_2025/`):

```text
phillips_2025/
├── nwbconverter.py              # Phillips2025NWBConverter — 6 interface slots
├── convert_session.py           # session_to_nwb() — one subject-session directory, one NWB file
├── convert_all_sessions.py      # discovers sessions, resolves subject metadata, batch-converts
├── general_metadata.yaml        # static NWBFile metadata
├── fiber_photometry.yaml        # fiber photometry hardware metadata (devices, indicators, table)
├── interfaces/
│   ├── pcampi_sync_interface.py             # PCampiSyncInterface (custom)
│   └── processed_fiber_photometry_interface.py  # ProcessedFiberPhotometryInterface (custom)
├── utils/
│   └── subject_metadata.py       # get_subject_metadata() (reads Subject metadata.xlsx)
└── documentation/
    ├── conversion_notes.md        # this file
    ├── project_track.md           # conversion progress tracker
    └── inspect_data.py            # ad hoc script for inspecting an output NWB file (not a test suite)
```

Raw Doric fiber photometry (`DoricFiberPhotometryInterface`) and DANNCE pose + video
(`DANNCEConverter`) are used directly from `neuroconv`, not reimplemented in this repo.

## File Inventory & Counts

- **Sessions:** 12 total — subjects **M4, M5, M7** × **day_1, day_2** × **Lone, Social** conditions
  (6 Lone + 6 Social subject-session directories).
- **Social condition:** now uploaded, at
  `H:/Uchida-CN-data-share/Hannah_data/M4-M7/Social_data/{day_1,day_2}/M{4,5,7}/`.
  - **day_1:** M5 and M7 share the same pCampi/Doric recording (`240716_160054_M5.h5`,
    `BBC300_Acq_0146.doric`) — a genuine paired social session; M4's day_1 session
    (`240716_152034_M4.h5`, `BBC300_Acq_0145.doric`) is a separate recording.
  - **day_2:** M4, M5, M7 each have their own distinct pCampi/Doric files — no shared recordings.
  - DANNCE output lives under `sDANNCE/predict05/` (not `DANNCE/` as in Lone_data) and includes
    extra pipeline artifacts alongside `save_data_AVG0.mat`. Confirmed `pred`/`data` shape
    `(90000, 2, 3, 23)` (both animals present), vs. `(90000, 1, 3, 23)` for Lone sessions.
- Per Lone-session directory: one `.h5` (pCampi), one `.doric` (raw photometry), one
  `interpolated_campy_and_doric.mat` (processed photometry, present once the lab pipeline has
  run), one `DANNCE/save_data_AVG0.mat`, one `calibration/` folder, 6 camera subfolders under
  `videos/`.
- Per Social-session directory: same as Lone, plus `processed_dff.mat`, but with
  `sDANNCE/predict05/` in place of `DANNCE/`.

## Sessions / Subjects

- **Subjects:** M4, M5, M7 only (M1, M2, M3, M6 are not part of this dataset — confirmed by
  Hannah Phillips).
- **Session/subject ID:** parsed from the pCampi filename, `YYMMDD_HHMMSS_M{id}.h5` →
  `session_id = f"{datetime_str}_{subject_id}"`, e.g. `"240624_135840_M4"`.
- **Per-subject metadata source:** `Subject metadata.xlsx` (lab-provided), transposed format
  (rows = fields, columns = subjects): `Subject ID`, `Species`, `Strain / genotype`, `Sex`,
  `Date of birth`, `Weight at time of experiment`, `Experimental group`, `Surgery date`. Read by
  `utils/subject_metadata.get_subject_metadata(subject_id, xlsx_path)`, which also parses
  `"Long Evans WT"` → `strain="Long Evans"`, `genotype="WT"`.
- **DANNCE array shape:** Lone sessions — `pred` shape `(90000, 1, 3, 23)`, `animal_index=0`.
  Social sessions — confirmed `(90000, 2, 3, 23)`, both animals written.
- **Species/strain:** *Rattus norvegicus*, Long Evans background (WT for all 3 subjects currently
  in the share).

## Existing Resources



## Interface Mapping

| Interface | Writes | Notes |
|---|---|---|
| `DoricFiberPhotometryInterface` (neuroconv, ×2: `DoricControl`, `DoricDopamineSignal`) | 2 `FiberPhotometryResponseSeries` in `acquisition`, each with 2 columns (NAc, TS) | One instance per excitation channel (EXC1=control/tdTomato 568 nm, EXC2=dopamine_signal/GRABDA3m 473 nm); each column-stacks 2 ROI streams via a 2-element `stream_names` list. Shares one `FiberPhotometryTable` (4 rows: 2 ROIs × 2 channels) defined in `fiber_photometry.yaml`. |
| `ProcessedFiberPhotometryInterface` (custom, ×2: `InterpolatedFPControlSignal`, `InterpolatedFPDopamineSignal`) | 2 `FiberPhotometryResponseSeries` in `processing/ophys` | Reads `interpolated_campy_and_doric.mat` (raw fluorescence resampled to video rate, not dF/F); reuses the raw interfaces' `FiberPhotometryTable` rows. No embedded timestamps — generates a nominal regular series from the camera frame rate (read from `videos/Camera1/metadata.csv`). Only present when the `.mat` file and `videos/` folder both exist. |
| `PCampiSyncInterface` (custom, ×2: `PCampiSyncCampyTrigger`, `PCampiSyncRbfmcFrames`) | 1 `TimeSeries` each (`SyncTTL_campy_trigger`, `SyncTTL_rbfmc_frames`) in `acquisition` | Writes one channel per instance — takes no assumptions about channel names or count; `channel_name` is required at init, and `get_available_channels(file_path)` discovers the channels present in a given `.h5` file. `convert_session.py` instantiates one interface per channel found. Also the **only** interface class that sets `NWBFile.session_start_time` (parsed from the pCampi filename). `campy_trigger` = camera trigger pulses; `rbfmc_frames` = intended Doric BBC300 Camera1 output pulses, but reads as all-zero (see Temporal Alignment). |
| `DANNCEConverter` (neuroconv) | `PoseEstimation` (ndx-pose) in `processing/behavior` + 6 `ImageSeries` (external video) + calibrated `Device`s | Reads `DANNCE/save_data_AVG0.mat` (`animal_index=0` for Lone sessions); no `frametimes_file_path` passed — pose timestamps computed from `sampleID`/sampling rate, video keeps each camera's own native per-frame timestamps. Skeleton (`SDANNCE_LANDMARK_NAMES`/`SDANNCE_SKELETON_EDGES` from `utils/constants.py`) is injected into `Behavior/Pose` metadata at conversion time (`session_to_nwb()`), keyed by `pose_key` ("PoseEstimationDANNCE"). |

`Phillips2025NWBConverter` (`nwbconverter.py`) registers 7 interface slots:
`DoricControl`, `DoricDopamineSignal`, `InterpolatedFPControlSignal`, `InterpolatedFPDopamineSignal`,
`PCampiSyncCampyTrigger`, `PCampiSyncRbfmcFrames`, `DANNCE`. `convert_session.py::session_to_nwb()`
discovers the files present in one subject-session directory, conditionally includes the
processed-photometry and DANNCE interfaces only when their source files exist, discovers the
pCampi channels present via `PCampiSyncInterface.get_available_channels()` and maps each to its
interface slot via `_PCAMPI_CHANNEL_TO_INTERFACE_KEY` (raising if an unrecognized channel name
is encountered), and merges `general_metadata.yaml` + `fiber_photometry.yaml` + caller-supplied
`subject_metadata` into one NWB file. `convert_all_sessions.py` batches this over every
`day_*/M*/` directory with both a `.h5` and a `.doric` file present, resolving each subject's
metadata via `get_subject_metadata()` (warning + fallback if missing), using
`ProcessPoolExecutor` and per-subject error capture to a file.

Dependencies (`pyproject.toml`, `[phillips_2025]` extra): `neuroconv` (from the
`add-dannce-interface` branch, pending merge to `main`), `ndx-fiber-photometry`,
`ndx-ophys-devices>=0.3.1`, `ndx-pose`, `h5py`, `scipy`, `numpy`, `opencv-python-headless`,
`openpyxl`, `tqdm`.

## Metadata

- **`general_metadata.yaml`**: static `NWBFile` fields (experiment/session description,
  institution, lab, experimenter, keywords); `related_publications` left as a TODO comment (no
  manuscript yet).
- **`fiber_photometry.yaml`**: hardware catalogue (`DeviceModels`/`Devices` for the two excitation
  LEDs, the BFPD camera, and the NAc/TS optical fibers), fluorescent indicators (GRABDA3m,
  tdTomato), and the `FiberPhotometryTable` (4 rows: ROI × channel) plus per-series metadata for
  all 4 response series (raw ×2, processed ×2). Naming convention: metadata keys use functional
  roles (`control`/`dopamine_signal`, `NAc`/`TS`), not raw hardware channel names (`EXC1`/`EXC2`,
  `ROI01`/`ROI02`) — confirmed with the lab, 2026-07-23.
- **`utils/subject_metadata.py`**: `get_subject_metadata(subject_id, xlsx_path)` reads
  `Subject metadata.xlsx` (transposed: rows=fields, columns=subjects) and returns `subject_id`,
  `species`, `strain`, `genotype`, `sex`, `description`, and (when present) `date_of_birth` and
  `weight`.
- **`utils/constants.py`**: `SDANNCE_LANDMARK_NAMES` (23 rat23 joints: Snout, EarL/R,
  Spine{F,M,L}, TailBase, Shoulder/Elbow/Wrist/Hand ×2, Hip/Knee/Ankle/Foot ×2) and
  `SDANNCE_SKELETON_EDGES` (23 edges, from `diegoaldarondo/Label3D`'s `rat23.mat`, converted from
  1- to 0-based indices) — mirrors the same constants in `olveczky-lab-to-nwb`'s
  `klibaite_2025_rat` conversion, which uses the same rat23 DANNCE skeleton. `DANNCEInterface`'s
  own `get_metadata()` seeds `Behavior/Pose/Skeletons[pose_key]` with `nodes` but an empty `edges`
  list (it has no anatomical knowledge of the skeleton); `session_to_nwb()` overrides that entry,
  keyed by the same `pose_key` used in `source_data["DANNCE"]["metadata_key"]`, with the real
  edges. The override key must match `pose_key` exactly (not the Skeleton's descriptive `name`
  field) — `DANNCEInterface.add_to_nwbfile()` looks up the skeleton via
  `PoseEstimations[pose_key]["skeleton_metadata_key"]`, and the metadata merge there is a
  key-for-key `DeepDict.deep_update`, not a name-based match.

## Temporal Alignment

**Status: cross-stream alignment REMOVED pending redesign.** An earlier
`temporally_align_data_interfaces()` implementation (pCampi as reference clock) had multiple
confirmed bugs, found by writing full-length (`stub_test=False`) single-stream debug NWB files
and inspecting them directly:

- **Doric → pCampi alignment never worked.** pCampi channel 1 (`rbfmc_frames`, intended to carry
  Doric BBC300 Camera1 sync pulses) is entirely zero for the full session, in all 6 session
  `.h5` files inspected — likely an acquisition-side wiring issue, not a code bug.
- **Frame-count mismatch:** pCampi `campy_trigger` pulses (90,074) vs. actual saved camera frames
  (90,000) — the camera dropped ~74 frames relative to trigger pulses, which broke naive
  1:1 assumptions between pCampi edges and video/DANNCE frame indices.

**Current interim behavior — each stream on its own clock, no cross-stream alignment:**

| Stream | Timestamps |
|---|---|
| Doric raw photometry | Native Doric clock (as read from the `.doric` file), unmodified |
| Processed (interpolated) photometry | Nominal regular series at the camera frame rate (`metadata.csv` `frameRate`), `starting_time=0.0` — no real per-sample clock available |
| DANNCE pose | `sampleID / sampling_rate` (`DANNCEConverter`'s built-in fallback when no `frametimes_file_path`/`video_file_path` is given) |
| Video (6 cameras) | Each camera's own native per-frame timestamps, from the video file itself |
| pCampi TTL | Native (written as acquisition `TimeSeries` at 1 kHz, `starting_time=0.0`) |

`NWBFile.session_start_time` is set from the pCampi filename (`PCampiSyncInterface` is the only
interface that provides it) — but `DoricFiberPhotometryInterface` does not set its own
`session_start_time`, so raw Doric photometry timestamps should **not** be interpreted as
starting exactly at `session_start_time`; the actual offset between Doric's recording start and
pCampi's recording start is currently unknown.

## Open Questions

Items that need input from the lab (Hannah Phillips) before they can be resolved:

- **ROI03**: the Doric file has 3 ROI signals per excitation channel, but only 2 implants
  (NAc, TS) are confirmed — what does ROI03 correspond to?
- **`dff_resG` identity** (`processed_dff.mat`): which ROI/channel does this single dF/F trace
  correspond to, and why only one trace instead of 4 (2 ROIs × 2 channels)?
- **Doric ↔ pCampi clock alignment**: `rbfmc_frames` (pCampi channel 1) reads as all-zero in
  every session inspected — acquisition issue to investigate with the lab before cross-stream
  alignment can be redesigned.
- **Social condition — shared pCampi/Doric recording**: on day_1, M5 and M7 point at the same
  `.h5`/`.doric` files — confirm with the lab whether this reflects one shared photometry rig for
  the pair or a labeling artifact in the share, and how `session_id`/subject assignment should
  handle it.
- **SFARI grant number + CC-BY-4.0 license** — ask Nao Uchida directly.
- **ORCIDs / contributors / publication DOI** — defer to manuscript stage.

## TODOs

Internal code/repo work, not blocked on the lab:

- **Cross-stream temporal alignment redesign** — needs a new reference clock strategy now that
  pCampi's `rbfmc_frames` channel has turned out to be unusable for Doric alignment.
- **Social condition support** — extend `convert_session.py`/`nwbconverter.py` for 2-animal DANNCE
  arrays and the `sDANNCE/predict05/` path (now uploaded, see File Inventory & Counts).
