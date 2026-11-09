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
  condition is also in the share (`Social_data/day_1`, `Social_data/day_2`), 3 subjects × 2 days =
  6 subject-session directories. Each social session has 2 rats in the arena, but only the subject
  (M4, M5 or M7) has fiber photometry; the partner rat appears only in the sDANNCE pose.

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
- **`processed_dff.mat`** (`dff_resG`, and `dff_resG2` for M5/M7 sessions) — We exclude this from the conversion for now, but prepare interface for the future dff computation:
  `DffFiberPhotometryInterface` (`interfaces/dff_fiber_photometry_interface.py`) exists and is
  registered in `Phillips2025NWBConverter`, but is **commented out by default** in
  `convert_session.py`: the `DffFiberPhotometryInterface` import near the top of the file, and
  the two blocks inside `session_to_nwb()` that build its `source_data` entry and trim its
  `fiber_photometry_table_region` (search for "DffDopamineSignal"), are all commented out, with
  a matching commented-out `fiber_photometry_dff_dopamine_signal` block at the bottom of
  `fiber_photometry.yaml`. All of it has to be uncommented together to use the interface.
  Confirmed as the go-forward plan at the 2026-09-15 midway meeting: keep the interface ready,
  don't add the data to NWB files for now.
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
      YYMMDD_HHMMSS_M{id}.h5                # pCampi sync — each subject has its own file
      BBC300_Acq_*.doric                     # raw Doric fiber photometry
      interpolated_campy_and_doric.mat       # lab-processed photometry
      processed_dff.mat                      # dff_resG (+ dff_resG2 for M5/M7); not converted,
                                              # also present in Lone_data — see "Not converted" above
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

`pred`/`data` arrays in `sDANNCE/predict05/save_data_AVG0.mat` are shape `(90000, 2, 3, 23)`, with
both animals in one file (vs. `(90000, 1, 3, 23)` in Lone_data). `M{id}day{n}_save_data_AVG0.mat`
is a byte-identical copy of `save_data_AVG0.mat` in all 6 social sessions (checked 2026-11-03), not
a per-animal split. Nothing in the files says which animal index is the implanted subject.

Repository (`src/uchida_lab_to_nwb/phillips_2025/`):

```text
phillips_2025/
├── nwbconverter.py              # Phillips2025NWBConverter — 10 interface slots
├── convert_session.py           # session_to_nwb() — one subject-session directory, one NWB file
├── convert_all_sessions.py      # discovers sessions, resolves subject metadata, batch-converts
├── general_metadata.yaml        # static NWBFile metadata, Tasks (per condition), HED schema + definitions
├── fiber_photometry.yaml        # fiber photometry hardware metadata (devices, indicators, table);
│                                 # ends with a commented-out AD HOC block for DffFiberPhotometryInterface
├── interfaces/
│   ├── pcampi_sync_interface.py                  # PCampiSyncInterface (custom)
│   ├── processed_fiber_photometry_interface.py   # ProcessedFiberPhotometryInterface (custom)
│   ├── task_epoch_interface.py                   # TaskEpochInterface (custom): epoch + Spyglass task table + HED
│   └── dff_fiber_photometry_interface.py         # DffFiberPhotometryInterface (custom, AD HOC — registered but its use in convert_session.py is commented out by default)
├── utils/
│   ├── constants.py              # SDANNCE_LANDMARK_NAMES, SDANNCE_SKELETON_EDGES (rat23)
│   └── subject_metadata.py       # get_subject_metadata() (reads Subject metadata.xlsx)
└── documentation/
    ├── conversion_notes.md        # this file
    ├── project_track.md           # conversion progress tracker
    ├── explore_sync_signals.py    # ad hoc exploration of the pCampi/Doric sync signals
    ├── inspect_data.py            # ad hoc script for inspecting an output NWB file (not a test suite)
    ├── testing.ipynb              # ad hoc checks on converted files
    └── midway_review.html         # material for the 2026-09-15 midway meeting
```

The example notebook for DANDI is `notebooks/dandi_001935_tutorial.ipynb` at the repo root.

Raw Doric fiber photometry (`DoricFiberPhotometryInterface`) and DANNCE pose + video
(`DANNCEConverter`) are used directly from `neuroconv`, not reimplemented in this repo.

## File Inventory & Counts

- **Sessions:** 12 total — subjects **M4, M5, M7** × **day_1, day_2** × **Lone, Social** conditions
  (6 Lone + 6 Social subject-session directories).
- **Social condition:** now uploaded, at
  `H:/Uchida-CN-data-share/Hannah_data/M4-M7/Social_data/{day_1,day_2}/M{4,5,7}/`.
  - **day_1:** M4, M5, M7 each have their own distinct pCampi/Doric files (M5: `240716_160054_M5.h5`/
    `BBC300_Acq_0146.doric`; M7: `240716_172845_M7.h5`/`BBC300_Acq_0148.doric`; M4: `240716_152034_M4.h5`/
    `BBC300_Acq_0145.doric`). M5 and M7 previously appeared to share the same recording in the
    share — resolved: labeling artifact, fixed by Hannah re-uploading M7's own files (2026-09).
  - **day_2:** M4, M5, M7 each have their own distinct pCampi/Doric files — no shared recordings.
  - DANNCE output lives under `sDANNCE/predict05/` (not `DANNCE/` as in Lone_data) and includes
    extra pipeline artifacts alongside `save_data_AVG0.mat`. Confirmed `pred`/`data` shape
    `(90000, 2, 3, 23)` (both animals present), vs. `(90000, 1, 3, 23)` for Lone sessions.
  - Each social `.doric` file has the same layout as the lone ones (ROI01–ROI03 × 2 excitations),
    so it holds the subject's photometry only.
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
- **DANNCE array shape:** Lone sessions: `pred` shape `(90000, 1, 3, 23)`, `animal_index=0`.
  Social sessions: `(90000, 2, 3, 23)`, index 0 = implanted subject, index 1 = partner (confirmed
  2026-11-03); both are written (see Open Questions → Storing the social partner rat).
- **Social partner rat:** not one of M4, M5, M7 (the three subjects' social sessions were recorded
  at different times, e.g. day_1 at 15:20, 16:00 and 17:28), has no photometry, and has no entry in
  `Subject metadata.xlsx`.
- **Species/strain:** *Rattus norvegicus*, Long Evans background (WT for all 3 subjects currently
  in the share).

## Existing Resources

- `interpolate_campy_and_doric2_clean.m` — the Uchida lab's own MATLAB
  script for aligning Doric photometry to Campy video frames via the Campy trigger signal on Doric
  DIO1 (`DigitalCh1`); shared by Hannah Phillips at the 2026-09-15 midway meeting. Used to confirm
  the `interpolated_data` resampling grid — see Temporal Alignment and Open Questions.

## Interface Mapping

| Interface | Writes | Notes |
|---|---|---|
| `DoricFiberPhotometryInterface` (neuroconv, ×2: `DoricControl`, `DoricDopamineSignal`) | 2 `FiberPhotometryResponseSeries` in `acquisition`, each with 2 columns (NAc, TS) | One instance per excitation channel (EXC1=control/tdTomato 568 nm, EXC2=dopamine_signal/GRABDA3m 473 nm); each column-stacks 2 ROI streams via a 2-element `stream_names` list. Shares one `FiberPhotometryTable` (4 rows: 2 ROIs × 2 channels) defined in `fiber_photometry.yaml`. |
| `ProcessedFiberPhotometryInterface` (custom, ×2: `InterpolatedFPControlSignal`, `InterpolatedFPDopamineSignal`) | 2 `FiberPhotometryResponseSeries` in `processing/ophys` | Reads `interpolated_campy_and_doric.mat` (raw fluorescence, not dF/F); reuses the raw interfaces' `FiberPhotometryTable` rows. No embedded timestamps — generates a nominal regular series from the camera frame rate (read from `videos/Camera1/metadata.csv`), on the assumption `interpolated_data` is resampled to the saved-video-frame grid. Only present when the `.mat` file and `videos/` folder both exist. |
| `PCampiSyncInterface` (custom, ×2: `PCampiSyncCampyTrigger`, `PCampiSyncRbfmcFrames`) | 1 `TimeSeries` each (`SyncTTL_campy_trigger`, `SyncTTL_rbfmc_frames`) in `acquisition` | Writes one channel per instance — takes no assumptions about channel names or count; `channel_name` is required at init, and `get_available_channels(file_path)` discovers the channels present in a given `.h5` file. `convert_session.py` instantiates one interface per channel found. Also the **only** interface class that sets `NWBFile.session_start_time` (parsed from the pCampi filename), and its `campy_trigger` instance defines the NWB time base (see Temporal Alignment). `rbfmc_frames` reads as all-zero (`has_meaningful_signal()` returns False) so it is skipped with a warning, not written. |
| `DANNCEConverter` (neuroconv) | `MultiCameraPoseEstimation` (ndx-pose) in `processing/behavior`, with one per-camera `PoseEstimation` child linking each camera and its video, + 6 `ImageSeries` (external video) + calibrated `Device`s | Reads `DANNCE/save_data_AVG0.mat` (Lone) or `sDANNCE/predict05/save_data_AVG0.mat` (Social), `animal_index=0` in both. There is no sync table, so pose timestamps are `sampleID` / camera frame rate, with the rate from `videos/Camera1/metadata.csv` passed as `sampling_rate`; each video is timed by its own `frametimes.npy` (both then re-anchored to the pCampi clock, see Temporal Alignment). Skeleton (`SDANNCE_LANDMARK_NAMES`/`SDANNCE_SKELETON_EDGES` from `utils/constants.py`) is injected into `Behavior/Pose` metadata at conversion time (`session_to_nwb()`), keyed by `pose_key` ("PoseEstimationDANNCE"). |
| `DANNCEInterface` (neuroconv, `DANNCEPartner`, social sessions only) | Second `MultiCameraPoseEstimation`, `PoseEstimationDANNCEPartner`, in `processing/behavior` | The partner rat (`animal_index=1`) from the same sDANNCE file. Reuses the camera Devices and videos written by `DANNCE`; its Skeleton is not linked to the file's Subject. |
| `TaskEpochInterface` (custom, `TaskEpoch`) | 1 row in `epochs`, `processing/tasks/task_table` (1 row), `HedLabMetaData` | Epoch spans the pCampi recording (0 to `n_samples / 1 kHz`; 10 s in stub mode), tagged `01_<task_name>`. Task text and HED come from `general_metadata.yaml` (`Tasks`, keyed by condition, and `HED`). See Metadata → Task, epoch and HED. |

`Phillips2025NWBConverter` (`nwbconverter.py`) registers 10 interface slots:
`DANNCE`, `DANNCEPartner` (social sessions only), `DoricControl`, `DoricDopamineSignal`, `InterpolatedFPControlSignal`,
`InterpolatedFPDopamineSignal`, `DffDopamineSignal` (disabled by default),
`PCampiSyncCampyTrigger`, `PCampiSyncRbfmcFrames`, `TaskEpoch`. `convert_session.py::session_to_nwb()`
discovers the files present in one subject-session directory, conditionally includes the
processed-photometry and DANNCE interfaces only when their source files exist, discovers the
pCampi channels present via `PCampiSyncInterface.get_available_channels()` and maps each to its
interface slot via `_PCAMPI_CHANNEL_TO_INTERFACE_KEY` (raising if an unrecognized channel name
is encountered), and merges `general_metadata.yaml` + `fiber_photometry.yaml` + caller-supplied
`subject_metadata` into one NWB file. `convert_all_sessions.py` batches this over every
`day_*/M*/` directory with both a `.h5` and a `.doric` file present, resolving each subject's
metadata via `get_subject_metadata()` (warning + fallback if missing), using
`ProcessPoolExecutor` and per-subject error capture to a file.

Dependencies (`pyproject.toml`): `neuroconv[dannce]` from `main` (the HERD and DANNCE changes are
not in a release yet), `pynwb>=4.0.0`, `nwbinspector`, `ndx-pose==0.4.0`,
`ndx-fiber-photometry==0.2.4`, `ndx-ophys-devices==0.3.1`, `ndx-hed==0.3.0`, `openpyxl`, `python-dateutil`,
`opencv-python-headless`.

## Metadata

- **`general_metadata.yaml`**: static `NWBFile` fields (experiment/session description,
  institution, lab, experimenter, keywords); `related_publications` left as a TODO comment (no
  manuscript yet).
- **`fiber_photometry.yaml`**: hardware catalogue (`DeviceModels`/`Devices` for the two excitation
  LEDs, the BFPD camera, and the NAc/TS optical fibers), fluorescent indicators (GRABDA3m,
  tdTomato), and the `FiberPhotometryTable` (4 rows: ROI × channel) plus per-series metadata for
  all 4 response series (raw ×2, processed ×2). Naming convention: metadata keys use functional
  roles (`control`/`dopamine_signal`, `NAc`/`TS`), not raw hardware channel names (`EXC1`/`EXC2`,
  `ROI01`/`ROI02`) — confirmed with the lab, 2026-07-23. `optical_fiber_{NAc,TS}`'s
  `fiber_insertion` carries only a placeholder hemisphere/ML sign (implant hemisphere is
  randomized per animal); `convert_session.py` overrides both per subject
  (`utils/subject_metadata.py::get_subject_fiber_hemispheres()`) from Hannah Phillips's confirmation ahead of the 2026-09-15 midway
  meeting — see Open Questions.
- **`utils/subject_metadata.py`**: `get_subject_metadata(subject_id, xlsx_path)` reads
  `Subject metadata.xlsx` (transposed: rows=fields, columns=subjects) and returns `subject_id`,
  `species`, `strain`, `genotype`, `sex`, `description`, and (when present) `date_of_birth` and
  `weight`.
- **`utils/constants.py`**: `SDANNCE_LANDMARK_NAMES` (23 rat23 joints, spelled out explicitly —
  e.g. `EarLeft`/`EarRight`, `SpineFront`/`SpineMiddle`/`SpineLow`, `TailBase`,
  `Shoulder`/`Elbow`/`Wrist`/`Hand` × `Left`/`Right`, `Hip`/`Knee`/`Ankle`/`Foot` × `Left`/`Right` —
  rather than the abbreviated rat23.mat originals) and
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

### Task, epoch and HED (Spyglass `TaskEpoch`)

Each file has one epoch and one task, in the layout Spyglass reads (checked against
`spyglass/common/common_task.py` on `master`, 2026-11-09):

- `epochs`: one row, 0 to the end of the pCampi recording, tagged `01_lone` or `01_social`.
  Spyglass names the `IntervalList` entry after the first tag and matches it to epoch 1.
- `processing/tasks/task_table`: `task_name` (`lone` / `social`), `task_description`,
  `task_environment` (`arena`), `camera_id`, `task_epochs` (`[1]`) and `HED`.
- `camera_id` is an empty string, which Spyglass reads as no cameras (`list(row.camera_id)`).
  Spyglass resolves camera IDs against ndx-franklab-novela `CameraDevice`s named
  `camera_device N` and raises on unknown IDs; the DANNCE cameras are `ndx_pose.CalibratedCamera`.
  `TaskEpoch.camera_name` is nullable, so the task still ingests. An empty ragged integer column
  would be the usual form, but NWB Inspector 0.7.1 (3 checks raise `IndexError`) and ndx-hed
  0.3.0's `HedNWBValidator` (`get_bids_dataframe` compares each cell to `""`) both crash on a
  zero-length column, so the string form is used.
- HED: `HedLabMetaData` holds schema 8.5.0 and two lab definitions, `Lone-condition` and
  `Social-condition`; the task row refers to one with `Def/...`. The implanted rat is the
  `Experiment-participant`, the partner an `Experiment-actor`. Spyglass's `Task` table has no HED
  field, so Spyglass does not ingest it yet (see TODOs).

Checked on stub files for M4 day_1 (lone and social), 2026-11-09:
- `HedNWBValidator` reports no issues on either file (and it does flag an invalid tag).
- NWB Inspector: only suggestions on the new objects (single-row `epochs` and `task_table`,
  non-standard module name `tasks`, which is the name Spyglass looks for).
- Reading `task_table` the way Spyglass does (`to_dataframe().itertuples()`) gives
  `camera_id -> []` and `task_epochs -> [1]`.
- Not yet tested with a Spyglass ingestion.

### Ontology annotation (HERD)

Every file carries machine-readable ontology references under `/general/external_resources`,
stored as HDMF HERD (External Resources Data). NeuroConv (`neuroconv.tools.external_resources`)
writes the terms stated in `metadata["ExternalResources"]` during `run_conversion()`. All of them are
stated in `general_metadata.yaml`, each map keyed by the exact string written in the file, because
HERD links a term to an object through that string. A term for a value the session does not have
(for example the skeleton nodes in a session without DANNCE data) is skipped.

| Map | NWB field(s) | Value in file | Term |
|---|---|---|---|
| `species` | `Subject.species` | `Rattus norvegicus` | NCBITaxon:10116 |
| `strain` | `Subject.strain` | `Long Evans` | RRID:RGD_2308852 (Crl:LE) |
| `experimenter` | `NWBFile.experimenter` | `Phillips, Hannah` | orcid:0000-0002-9093-0505 |
| `institution` | `NWBFile.institution` | `Harvard University` | ror:03vek6s52 |
| `anatomical_structures` | `FiberPhotometryTable.location` | `Nucleus Accumbens` | UBERON:0001882 (nucleus accumbens) |
| `anatomical_structures` | `FiberPhotometryTable.location` | `Tail of Striatum` | UBERON:0002435 (striatum) |
| `anatomical_structures` | DANNCE `Skeleton.nodes` | 23 rat23 landmarks | UBERON (see below) |

- **Strain**: the subject sheet writes `Long Evans` and records no supplier. The term is the
  Long-Evans RRID NeuroConv's strain table uses, which is Charles River's Crl:LE.
- **Brain regions**: rat has no dedicated Allen atlas, and NeuroConv's rat fallback list of UBERON
  terms covers neither structure.
  - Nucleus Accumbens (NAc, ROI01): exact UBERON match, checked against the
    [EBI Ontology Lookup Service](https://www.ebi.ac.uk/ols4).
  - Tail of Striatum (TS, ROI02): a subregion defined by its dopamine circuitry (Menegas et al.).
    Neither UBERON nor the Allen Mouse Brain Atlas has a term for it (checked 2026-08-12), so it
    is mapped to the broader "striatum" term. This approximation was accepted until a more specific
    term exists.
- **Skeleton anatomy**: all 23 rat23 nodes are mapped.
  - UBERON has no separate left/right terms, so both sides of a paired landmark share one term (for
    example `EarLeft`/`EarRight` -> UBERON:0001691, external ear), written once with a YAML anchor.
  - `SpineFront`/`SpineMiddle`/`SpineLow` all map to the vertebral column (UBERON:0001130).
  - `TailBase` maps to the tail (UBERON:0002415), because UBERON has no tail-base term.

To change or add a term, edit the `ExternalResources` block in `general_metadata.yaml`.

## Temporal Alignment

**Status: pCampi ↔ Doric offset alignment implemented (single scalar offset, from one edge pair).**
The original `rbfmc_frames` (pCampi channel 1, intended to carry Doric BBC300 Camera1 sync pulses)
is entirely zero for the full session in every `.h5` file inspected — per Hannah Phillips (2026-09-15
midway meeting), likely due to an old rig setting, not a per-session acquisition fault. The working
sync path was
found on the *Doric* side instead: `DigitalCh1` ("DIO BNC \| Ch.1", an external BNC digital input)
carries the same physical TTL pulse train as pCampi's `campy_trigger`, just sampled by Doric's own
independent 1 kHz clock instead of pCampi's NIDAQ.

**How it works** (all inline in `Phillips2025NWBConverter.temporally_align_data_interfaces()`, `nwbconverter.py`):

1. Each side's very first square wave is *not* part of the regular ~50 Hz camera-trigger train —
   it is a single, longer pulse that both systems emit once at the start of recording, before their
   regular trains begin (`campy_trigger`: rising ~3.2 s in, falling ~3 s later; `DigitalCh1`: the
   signal starts HIGH at t=0 and falls once, ~3 s in, before its own regular train starts ~5-8 s
   later). That first falling edge is the same physical event on both sides.
2. Edge detection reuses neuroconv's `get_falling_frames_from_ttl`/`get_rising_frames_from_ttl`
   (`neuroconv.tools.signal_processing`) rather than a local reimplementation. The Doric side is
   read directly off the already-instantiated `DoricControl` interface —
   `DoricFiberPhotometryInterface._get_stream_data()`/`_get_stream_timestamps()` with
   `stream_name=DORIC_SYNC_STREAM_NAME` ("BBC300_Signals_Series0001_DigitalIO_DigitalCh1") — and the
   pCampi side via `PCampiSyncInterface.get_digital_data()`.
3. The offset is `pcampi_marker_time - doric_marker_time`, from each side's first falling edge
   directly (~3.2 s in the inspected session). This
   was cross-checked (in an earlier version of this code) against averaging
   `pcampi_edge_time - doric_edge_time` over all 90,073 matched pulses of the regular train (after
   dropping each side's marker pulse): the two methods agree to within the ~20 ms clock drift
   measured over the session (~-12 ppm over ~30 minutes, consistent with independent clock
   crystals on the same physical pulse train), so the single-marker-pulse offset is used.
4. That offset is applied via `BaseTemporalAlignmentInterface.set_aligned_starting_time()` to the raw
   Doric interfaces, `DoricControl`/`DoricDopamineSignal` (native Doric clock).
5. `InterpolatedFPControlSignal`/`InterpolatedFPDopamineSignal` (and `DffDopamineSignal`, when
   enabled) get real per-sample timestamps instead of a nominal camera-rate approximation:
   `_compute_doric_trigger_pulse_timestamps()` (`nwbconverter.py`) reproduces the Uchida lab's own
   MATLAB alignment logic (`interpolate_campy_and_doric2_clean.m`, shared by Hannah Phillips at the
   2026-09-15 midway meeting) — the rising edges of `DigitalCh1`, with an extra implicit edge
   prepended at `t=0` because the signal is already HIGH at the very first Doric sample (mirroring
   the MATLAB script's `if dio1_triggers(1) == 1` branch). When this timestamp count matches
   `interpolated_campy_and_doric.mat`'s sample count exactly (verified true for 9 of the 12 sessions
   in the share, 2026-09-15), those timestamps (shifted by the same pCampi↔Doric offset) are written
   directly. For the 3 sessions where it doesn't match (see below), this falls back to the previous
   nominal-camera-rate `set_aligned_starting_time()` shift, with a runtime warning.
6. Separately, `DANNCE` (pose, timed as `sampleID` / camera frame rate, and all 6 videos, timed by
   each camera's `frametimes.npy` "elapsed seconds since recording start") is anchored via
   `set_aligned_starting_time()` to the first non-spurious **rising** edge of the pCampi
   `campy_trigger` train (`drop_spurious_leading_edges()`, defined in `nwbconverter.py`, applied to
   `get_rising_frames_from_ttl()` output, to skip past the marker pulse and land on the first real
   camera-trigger pulse) — the pCampi-clock time of that first real trigger. This is looped over
   every sub-interface of the `DANNCEConverter` (`dannce.data_interface_objects.values()`), so pose
   and all 6 videos stay mutually synchronized after the shift.

A further **frame-count mismatch** remains, currently unaddressed: pCampi `campy_trigger` pulses
(90,074, i.e. the camera-frame trigger) vs. actual saved camera frames (90,000) — the camera
dropped ~74 frames relative to trigger pulses. This does not block the `set_aligned_starting_time`
approach above (a single shared starting-time shift, not a per-frame correspondence), but would
matter for any future per-frame-accurate alignment. Checked across all 12 sessions in the share
(ad hoc analysis, not committed to the repo): every session shows the same small mismatch (clean
`campy_trigger` rising edges − saved frames = +68 to +78, mean +74), so this is systematic, not a
one-off for M4/day 1.

That same all-session check turned up an unrelated, more surprising discrepancy: in 9 of the 12
sessions, `interpolated_campy_and_doric.mat`'s `interpolated_data` sample count is not the saved
video frame count at all — it is `n_clean_campy_rising_edges + 1` (one sample per real trigger
pulse, plus an initial t=0 sample), diverging from the frame count by the same ~70-78. The other 3
sessions (`Lone/day_1/M7`, `Social/day_1/M4`, `Social/day_1/M7`) land exactly on the saved frame
count instead — confirmed **resolved as a lab-side inconsistency, not a bug in this repo**, after
Hannah Phillips shared the MATLAB alignment script at the 2026-09-15 midway meeting (see step 5
above and Open Questions): those 3 sessions' `.mat` files appear to have been produced by a
different pipeline run than the other 9. `ProcessedFiberPhotometryInterface`'s nominal-camera-rate
timestamps are now only a fallback for those 3 sessions, not the default for all of them.
See https://claude.ai/code/artifact/2979af36-32b7-4135-a869-ceab195a41a2

`NWBFile.session_start_time` is set from the pCampi filename (`PCampiSyncInterface` is the only
interface that provides it), and `campy_trigger`'s own clock (`starting_time=0.0` relative to that
filename timestamp) is the NWB time base every aligned stream above is shifted onto.

## Open Questions

Items that need input from the lab (Hannah Phillips) before they can be resolved:

- **ROI03.** The Doric files have a third ROI per excitation, but only 2 implants (NAc, TS) are
  confirmed. ROI03 is not converted.
- **dF/F (`processed_dff.mat`).** What `dff_resG`/`dff_resG2` represent and why their scale differs
  across sessions. The interface stays disabled until then.
- **SFARI grant number + CC-BY-4.0 license.** Ask Nao Uchida directly.
- **Contributors / publication DOI.** Defer to manuscript stage.
- **When the partner is in the arena.** In social day_1/M4 the partner track nearly matches the
  subject's (mean keypoint distance under 10 mm) for frames 0 to 29,804 and 78,126 to the end,
  about 596 s to 1,563 s of partner presence in a 30-minute session (checked 2026-11-09 on the full
  file). Video frames 1,000 and 85,000 show one rat, frame 45,000 shows two. So sDANNCE reports
  the subject twice when the partner is absent. Ask whether the partner is always added partway
  through, and whether the lab has the insertion and removal times. If so, they could be written
  as an intervals table, and the partner pose outside that window marked as not tracked.

### Storing the social partner rat

The Olveczky conversion writes one NWB file per rat, because both rats there are dataset subjects
with their own metadata and sDANNCE files. Here only the implanted rat is a subject with neural
data, so the options are:

1. One file per session, for the implanted subject. It holds the subject's pose and a second pose
   container for the partner, described as the partner's. The partner gets no `Subject` entry.
2. A second file per session for the partner (pose and the shared videos only), as in the
   Olveczky conversion. This only makes sense if the partner is an identified rat with metadata,
   and it adds partner subjects to the Dandiset that have no photometry.

Decided 2026-11-03: option 1. The partner is treated as an external stimulus, with no ID, sex,
strain or date of birth recorded. sDANNCE animal index 0 is the implanted subject and index 1 the
partner in all 6 social sessions, confirmed by Hannah Phillips from pose overlays on video frames
(the subject is the rat attached to the fiber cable).

Implementation: the partner is a second slot, `DANNCEPartner` (`DANNCEInterface`, `animal_index=1`),
registered after `DANNCE`. It writes a second `MultiCameraPoseEstimation`,
`PoseEstimationDANNCEPartner`, whose Skeleton has no `subject` link. It reuses the camera Devices
and videos that `DANNCEConverter` writes, its per-camera entries link those videos, and it gets the
same time shift as the subject's pose. The videos are written once.

## TODOs

Internal code/repo work, not blocked on the lab:

- Social day_1/M7 has calibration only for Camera3, Camera5 and Camera6, and no
  `calibration.json`. Those 3 are written as `CalibratedCamera`, the other 3 as plain `Device`
  (checked on a stub, 2026-11-03). Ask the lab whether the missing calibration files exist.
- Optionally report upstream, after asking the team: ndx-hed `HedNWBValidator` and NWB Inspector
  crash on a table with an empty ragged column. Worked around here (see Metadata → Task, epoch
  and HED); once fixed, `camera_id` can become an empty ragged integer column.
- Test Spyglass ingestion of `epochs` and `processing/tasks` on a converted file.
- Draft a feature request to Spyglass for an optional HED field on `Task`, filled from a
  `HedTags` column in the tasks table (for review before opening).
- Update the tutorial (`notebooks/dandi_001935_tutorial.ipynb`) with a section on the social
  partner (`PoseEstimationDANNCEPartner`) and a section on the task, epoch and HED annotations.
- Add a test suite.
- Replace the neuroconv `main` pin with a release, once one includes the HERD and DANNCE changes.
- Get the neuroconv fix that writes per-camera `PoseEstimation` descriptions.
- Re-convert all 12 sessions and run NWB Inspector on the full files.
- Upload to DANDI (Dandiset 001935, embargo mode planned) and submit the example notebook to
  `dandi/example-notebooks`.

Done: HERD ontology annotation (see Metadata → Ontology annotation); task, epoch and HED
annotation (see Metadata → Task, epoch and HED).
