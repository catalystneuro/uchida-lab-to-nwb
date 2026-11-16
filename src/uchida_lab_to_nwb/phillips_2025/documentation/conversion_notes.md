# Conversion notes: Phillips 2025

Reference for how the raw data of the Phillips 2025 dataset maps to NWB, and the reasons behind
each choice. For installing, running and extending the conversion, see the
[README](../../../../README.md).

## Experiment

Fiber photometry, 3D pose and 6-camera video of rats behaving freely in an arena, from the Uchida
Lab (Harvard University), part of the SFARI Autism Rat Models Consortium (ARC). Dopamine is
recorded with GRABDA3m (tdTomato as control) in the nucleus accumbens (NAc) and the tail of the
striatum (TS).

- Lone condition (`Lone_data`): the implanted rat is alone in the arena, about 30 minutes.
- Social condition (`Social_data`): a partner rat shares the arena, about 35 minutes. Only the
  implanted rat has fiber photometry; the partner appears only in the pose data.
- Subjects M4, M5 and M7, 2 days per condition: 12 sessions, one NWB file each.
- Synchronization: pCampi (LabVIEW) records the camera trigger TTL on a NIDAQ at 1 kHz. Times are in
  America/New_York.

## Source data layout

One subject-session directory per session:

```text
<data share>/Hannah_data/M4-M7/
  Lone_data/
    day_{1,2}/
      M{4,5,7}/
        YYMMDD_HHMMSS_M{id}.h5                # pCampi sync (NIDAQ digital input, 1 kHz)
        BBC300_Acq_*.doric                     # raw Doric fiber photometry (HDF5)
        interpolated_campy_and_doric.mat       # lab-processed photometry, resampled to the camera triggers
        processed_dff.mat                      # lab dF/F, not converted
        DANNCE/save_data_AVG0.mat              # 3D pose (23 keypoints)
        calibration/
          calibration.json                     # 6-camera intrinsics and extrinsics
          hires_camN_params.mat                # per-camera DANNCE calibration
        videos/
          Camera{1..6}/
            0.mp4                              # H.264, 1920x1200 at 50 fps
            frametimes.npy                     # (2, n_frames): frame index, elapsed seconds
            metadata.csv                       # campy acquisition metadata, incl. frameRate
  Social_data/
    day_{1,2}/
      M{4,5,7}/
        ...                                    # same as Lone_data, except:
        sDANNCE/predict05/save_data_AVG0.mat   # 3D pose of both rats, plus other DANNCE outputs
<data share>/Subject metadata.xlsx            # per-subject metadata
```

In `save_data_AVG0.mat`, `pred` has shape `(n_frames, 1, 3, 23)` in lone sessions and
`(n_frames, 2, 3, 23)` in social sessions. In social sessions, animal index 0 is the implanted
subject (the rat attached to the fiber cable) and index 1 the partner.
`M{id}day{n}_save_data_AVG0.mat` in the same folder is an identical copy and is not read.

## Sessions and subjects

- Subject ID: the session folder name (`M4`).
- Session ID: from the folder path, `<Condition>_data/day_<N>/M<id>` gives `day-<N>-<condition>`,
  for example `Lone_data/day_1/M4` gives `day-1-lone`. The file is
  `sub-M4/sub-M4_ses-day-1-lone.nwb`.
- `session_start_time`: parsed from the pCampi file name, `YYMMDD_HHMMSS_M{id}.h5`.
- Subject fields: read from `Subject metadata.xlsx` by `utils/subject_metadata.get_subject_metadata()`.
  The sheet is transposed (rows are fields, columns are subjects) with the rows `Subject ID`,
  `Species`, `Strain / genotype`, `Sex`, `Date of birth`, `Weight at time of experiment`,
  `Experimental group` and `Surgery date`. `Long Evans WT` is split into strain `Long Evans` and
  genotype `WT`; group and surgery date go into the description.
- Fiber implant hemisphere: randomized per animal and not in the sheet, so it is set in
  `_SUBJECT_FIBER_HEMISPHERES` in `utils/subject_metadata.py`.
- Social partner: not one of the subjects, has no photometry and no entry in the sheet. It is
  treated as part of the task (an external stimulus): its pose is written, but it has no `Subject`.

## Data streams and interfaces

The converter, `Phillips2025NWBConverter` in `nwbconverter.py`, has one slot per stream:

| Slot | Interface | Reads | Writes |
| --- | --- | --- | --- |
| `DANNCE` | `DANNCEConverter` (NeuroConv) | `save_data_AVG0.mat`, `videos/`, `calibration/` | `MultiCameraPoseEstimation` `PoseEstimationDANNCE` (ndx-pose) in `processing/behavior`, 6 external-file `ImageSeries`, one camera `Device` per camera |
| `DANNCEPartner` | `DANNCEInterface` (NeuroConv) | social `save_data_AVG0.mat`, animal index 1 | `PoseEstimationDANNCEPartner` in `processing/behavior`, linked to the same cameras and videos |
| `DoricControl`, `DoricDopamineSignal` | `DoricFiberPhotometryInterface` (NeuroConv) | `.doric` | `FiberPhotometryResponseSeries` in `acquisition`, 2 columns (NAc, TS); the shared `FiberPhotometryTable`, devices and indicators |
| `InterpolatedFPControlSignal`, `InterpolatedFPDopamineSignal` | `ProcessedFiberPhotometryInterface` | `interpolated_campy_and_doric.mat` | `FiberPhotometryResponseSeries` in `processing/ophys`, 2 columns (NAc, TS) |
| `DffDopamineSignal` | `DffFiberPhotometryInterface` | `processed_dff.mat` | disabled, see below |
| `PCampiSyncCampyTrigger`, `PCampiSyncRbfmcFrames` | `PCampiSyncInterface` | `.h5`, one digital channel each | `TimeSeries` `SyncTTL_<channel>` in `acquisition`; sets `session_start_time` |
| `TaskEpoch` | `TaskEpochInterface` | `.h5` (recording length) | one row in `epochs`, `processing/tasks/task_table`, `HedLabMetaData` |

`DANNCE` is listed first on purpose. NeuroConv's `add_fiber_photometry_devices()` creates a plain
`Device` for every entry of `metadata["Devices"]`, including the cameras. Running `DANNCE` first
creates the calibrated camera devices before the fiber photometry interfaces can create plain ones
under the same names.

`convert_session.py::session_to_nwb()` builds the source data for one session directory:

- pCampi: one `PCampiSyncInterface` per channel found in the `.h5` file, mapped to a slot by
  `_PCAMPI_CHANNEL_TO_INTERFACE_KEY`. An unknown channel name raises. `rbfmc_frames` is all zero in
  this dataset, so the interface skips it with a warning.
- Raw photometry: Doric streams `CAM1EXC1` (control, 568 nm, tdTomato) and `CAM1EXC2` (dopamine
  signal, 473 nm, GRABDA3m), ROI01 (NAc) and ROI02 (TS), set in `_DORIC_INTERFACE_CONFIG`. ROI03 has
  no fiber implant and is not converted.
- Processed photometry and DANNCE: added only when their files and the `videos/` folder exist.
  The camera frame rate is read from `videos/Camera1/metadata.csv`.
- Metadata: merged in layers, interface defaults, then `general_metadata.yaml`, then
  `fiber_photometry.yaml`, then the per-subject fields and hemispheres, then the session
  description, skeleton and camera descriptions.

`convert_all_sessions.py::dataset_to_nwb()` runs `session_to_nwb()` on every `day_*/M*/` directory
of one condition folder that has a `.h5` and a `.doric` file. A session whose subject is not in the
sheet is skipped with a warning. A session that fails writes its traceback to `exceptions/` in the
output folder and does not stop the others.

### Not converted

- `processed_dff.mat` (`dff_resG`, and `dff_resG2` in M5 and M7 sessions): what the traces are and
  why their scale differs across sessions is not known. `DffFiberPhotometryInterface` is ready but
  disabled. To enable it, uncomment the three "DffDopamineSignal" blocks in `convert_session.py`
  (import, source data, table region) and the `fiber_photometry_dff_dopamine_signal` block at the
  end of `fiber_photometry.yaml`. Its row mapping (`dff_resG` to NAc, `dff_resG2` to TS) is an
  assumption to check first.
- `Channels.csv`: a derived envelope/RMS feature used for sleep and seizure scoring, not raw data.
- Doric ROI03 (see above).

## Metadata

- `general_metadata.yaml`: `NWBFile` fields (experiment description, institution, lab,
  experimenter, keywords), the task of each condition (`Tasks`), the HED schema and definitions
  (`HED`) and the ontology terms (`ExternalResources`).
- `fiber_photometry.yaml`: excitation LEDs, photodetector and optical fibers (`DeviceModels`,
  `Devices`), indicators, the `FiberPhotometryTable` (4 rows: NAc and TS, control and dopamine
  signal) and the metadata of each response series. Keys use functional roles (`control`,
  `dopamine_signal`, `NAc`, `TS`) instead of hardware channel names (`EXC1`, `ROI01`). The fiber
  hemisphere is a placeholder that `session_to_nwb()` sets per subject.
- `utils/constants.py`: the 23 rat23 landmark names and skeleton edges. The edges come from
  `rat23.mat` in [Label3D](https://github.com/diegoaldarondo/Label3D), converted to 0-based indices.
  `DANNCEInterface` writes the nodes with no edges, so `session_to_nwb()` sets the skeleton under
  the same key as the pose container (`pose_key`).

### Task, epoch and HED

Each file has one epoch and one task, in the layout Spyglass reads into `IntervalList`, `Task` and
`TaskEpoch` (`spyglass/common/common_task.py`):

- `epochs`: one row from 0 to the end of the pCampi recording, tagged `01_lone` or `01_social`.
  Spyglass names the interval after the first tag and matches it to epoch 1.
- `processing/tasks/task_table`: `task_name` (`lone` or `social`), `task_description`,
  `task_environment` (`arena`), `camera_id`, `task_epochs` (`[1]`) and `HED`.
- `camera_id` is a ragged integer column with the camera IDs, `[1, 2, 3, 4, 5, 6]`: the trailing
  digits of the camera device names `Camera1` to `Camera6`. Spyglass matches each ID to a camera
  device and raises on an unknown one. A session without DANNCE data has no camera devices and
  writes `camera_id` as an empty string, which Spyglass reads as no cameras. An empty ragged column
  would be the usual form, but NWB Inspector and the ndx-hed validator crash on a zero-length
  column.
- HED: `HedLabMetaData` holds schema 8.5.0 and two definitions, `Lone-condition` and
  `Social-condition`, and the task row refers to one with `Def/...`. The implanted rat is the
  `Experiment-participant`, the partner an `Experiment-actor`. Spyglass's `Task` table has no HED
  field, so Spyglass does not read it.

### Ontology terms (HERD)

Every file holds ontology references under `/general/external_resources` (HDMF HERD). NeuroConv
writes the terms listed under `ExternalResources` in `general_metadata.yaml`. Each map is keyed by
the exact string written in the file, because HERD links a term to an object through that string.
A term for a value the session does not have (for example the skeleton nodes of a session without
DANNCE data) is skipped.

| Map | NWB field | Value | Term |
| --- | --- | --- | --- |
| `species` | `Subject.species` | `Rattus norvegicus` | NCBITaxon:10116 |
| `strain` | `Subject.strain` | `Long Evans` | RRID:RGD_2308852 (Crl:LE) |
| `experimenter` | `NWBFile.experimenter` | `Phillips, Hannah` | ORCID iD |
| `institution` | `NWBFile.institution` | `Harvard University` | ror:03vek6s52 |
| `anatomical_structures` | `FiberPhotometryTable.location` | `Nucleus Accumbens` | UBERON:0001882 |
| `anatomical_structures` | `FiberPhotometryTable.location` | `Tail of Striatum` | UBERON:0002435 (striatum) |
| `anatomical_structures` | DANNCE `Skeleton.nodes` | 23 rat23 landmarks | UBERON |

- Strain: the sheet records no supplier; the term is the Long-Evans RRID used by NeuroConv's strain
  table (Charles River Crl:LE).
- Tail of Striatum has no term in UBERON or the Allen Mouse Brain Atlas, so it is mapped to
  striatum.
- Skeleton: UBERON has no left and right terms, so both sides of a paired landmark share one term
  (written once with a YAML anchor). The three spine points map to the vertebral column and
  `TailBase` to the tail.

## Temporal alignment

All streams are aligned to the pCampi clock in
`Phillips2025NWBConverter.temporally_align_data_interfaces()`.

The pCampi channel `rbfmc_frames`, meant to carry the Doric camera sync, is all zero. The Doric
digital input `DigitalCh1` ("DIO BNC | Ch.1", stream
`BBC300_Signals_Series0001_DigitalIO_DigitalCh1`) records the same camera trigger pulses as the
pCampi channel `campy_trigger`, on Doric's own 1 kHz clock. Before the regular 50 Hz trigger train,
both systems record one longer start-of-recording pulse; its falling edge is the same event on
both clocks.

1. Raw photometry (`DoricControl`, `DoricDopamineSignal`): the offset between the two clocks is
   the first `campy_trigger` falling edge minus the first `DigitalCh1` falling edge. The series
   keep their Doric timestamps, shifted by that offset.
2. Processed photometry (`InterpolatedFP*`, and `DffDopamineSignal` when enabled): the lab's MATLAB
   script `interpolate_campy_and_doric2_clean.m` resamples the photometry onto the rising edges of
   `DigitalCh1`, counting the already-high first sample as an extra edge.
   `_compute_doric_trigger_pulse_timestamps()` reproduces those times. When their number matches the
   sample count of `interpolated_campy_and_doric.mat`, they are written, shifted by the offset.
   Otherwise the series gets nominal timestamps at the camera frame rate, shifted by the offset, and
   a warning is raised.
3. DANNCE pose and video: pose times are frame index divided by the camera frame rate, and each
   video uses its `frametimes.npy`. Both are shifted to the first rising edge of the regular
   `campy_trigger` train (`drop_spurious_leading_edges()` skips the start-of-recording pulse). The
   partner pose gets the same shift.

Two features of the data matter for this:

- In 9 of the 12 sessions the processed photometry has one sample per trigger pulse plus one, as
  above. In `Lone_data/day_1/M7`, `Social_data/day_1/M4` and `Social_data/day_1/M7` it has one
  sample per saved video frame instead, so those 3 sessions use the nominal timestamps.
- Every session has about 74 more `campy_trigger` pulses than saved video frames (68 to 78). The
  alignment uses a single shift, so this does not affect it, but per-frame alignment would have to
  account for it.

## Inspection and DANDI upload

`inspection.py` runs NWB Inspector with the DANDI configuration on every `<output folder>/sub-*/*.nwb`
file (stubs in `nwb_stub/` are left out). It writes one report per file to
`<output folder>/inspector_reports/` and a summary, `inspection_summary.csv`, with the number of
messages per importance level and the number of HERD references per file.

Keep the output folder on the same drive as the data share. The videos are linked by a path relative
to the NWB file, which is not possible across drives; NWB Inspector then reports
`check_image_series_external_file_relative` for each video.

`upload_to_DANDI.py` uploads to Dandiset 001935 in two steps:

1. `organize_nwbfiles()` downloads the draft's `dandiset.yaml` and runs `dandi organize` in copy mode
   into `<dandiset folder>/001935`. Files are renamed `sub-M4_ses-day-1-lone_image.nwb` (dandi adds
   `_image` for the linked videos), and each file's videos are copied to a folder of the same name
   with the links updated. The conversion output is not changed.
2. `report_draft_assets()` lists each draft asset as replaced, superseded or not reconverted, and
   each new file. `upload_organized_files()` validates the files and the dandiset metadata, and
   uploads only if there are no errors.

The `__main__` block prints the report and uploads only once `upload = True` is set. Uploading needs
a DANDI API key in the `DANDI_API_KEY` environment variable. Re-uploaded videos get new file names
(dandi names them by the ID of the video series), so earlier videos stay on the draft as superseded
until they are deleted.

## Known limitations

- The per-camera `PoseEstimation` descriptions are set in the metadata but not written by NeuroConv
  yet; NWB Inspector reports them as suggestions.
- `Social_data/day_1/M7` has calibration files only for Camera3, Camera5 and Camera6, and no
  `calibration.json`. Those 3 cameras are written as calibrated cameras, the other 3 as plain
  devices.
- In social sessions, sDANNCE reports the subject's pose for the partner while the partner is not in
  the arena. In `Social_data/day_1/M4` the partner track matches the subject (mean keypoint distance
  under 10 mm) for frames 0 to 29,804 and 78,126 to the end. If the times the partner is placed in
  and removed from the arena are known, they could be written as an intervals table.
- The ndx-hed validator (`HedNWBValidator`) raises on the 6-value `camera_id` cell of the task table.
  NWB Inspector reports nothing on it, and the HED annotation itself is valid.
- Spyglass ingestion of the epochs and task table has not been tested on these files.
- There is no test suite.
- Not in the metadata yet: grant number, license, contributors and related publications (no
  manuscript yet; `related_publications` is a TODO in `general_metadata.yaml`).
