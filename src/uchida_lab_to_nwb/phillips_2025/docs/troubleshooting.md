# Troubleshooting

This page lists the errors and warnings of the conversion, with what to do. A session that fails in
`convert_all_sessions.py` writes its traceback to `<output folder>/exceptions/`; the other sessions are still
converted.

## Conversion errors

| Message | Meaning | What to do |
| --- | --- | --- |
| "Expected one .h5 sync file, found: ..." | the session folder has no pCampi file, or several | keep one `.h5` file in the folder |
| "Expected one .doric file, found: ..." | the session folder has several `.doric` files | keep one `.doric` file in the folder |
| "Unrecognized pCampi channel ..." | the `.h5` file has a channel other than `campy_trigger` and `rbfmc_frames` | add the channel to `_PCAMPI_CHANNEL_TO_INTERFACE_KEY` in `convert_session.py` and a matching slot to `data_interface_classes` in `nwbconverter.py` |
| "No confirmed fiber implant hemisphere for subject ..." | the subject has no entry in `_SUBJECT_FIBER_HEMISPHERES` | add it (see [Metadata](metadata.md#adding-a-subject)) |
| "'frameRate' not found in .../metadata.csv" | the campy metadata of Camera1 has no frame rate | check `videos/Camera1/metadata.csv` |
| "FiberPhotometryTable is provided but response series ... has no fiber_photometry_table_region" | the dF/F interface was enabled without its metadata | uncomment the `fiber_photometry_dff_dopamine_signal` block of `fiber_photometry.yaml` too (see [Data streams](data_streams.md#not-converted)) |

## Warnings

| Message | Meaning | What to do |
| --- | --- | --- |
| "[WARNING] Subject '...' not found in ...; skipping ..." | the subject is not in `Subject metadata.xlsx`, so its sessions are skipped | add a column for it to the sheet |
| "pCampi channel 'rbfmc_frames' ... never changes value ... skipping" | the channel is all zero and is not written | nothing; this is expected in this dataset |
| "...: interpolated_campy_and_doric.mat has N samples but M Doric Campy-trigger pulses were found ..." | the processed photometry was resampled to the video frames, not the trigger pulses, so it is written at the camera frame rate | nothing for `Lone_data/day_1/M7`, `Social_data/day_1/M4` and `Social_data/day_1/M7` (see [Data streams](data_streams.md#time-alignment)); for another session, check its `.mat` file with the lab |
| "Skipping ... (already exists). Pass overwrite=True to overwrite." | the NWB file exists and `overwrite=False` | set `overwrite=True` to convert it again |

## NWB files

- `herd_references` is 0 in the inspection summary: the ontology terms were not written. Check that each value has
  an entry under `ExternalResources` in `general_metadata.yaml`, with the same spelling (see
  [Metadata](metadata.md#ontology-terms)).
- NWB Inspector reports `check_image_series_external_file_relative`: the output folder is on another drive than the
  data share, so the video paths are absolute. Convert again to a folder on the same drive.
- NWB Inspector messages: the report of each file is in `inspector_reports/`. `CRITICAL` and `ERROR` messages must be
  fixed before uploading; `BEST_PRACTICE_SUGGESTION` messages can be reviewed case by case. The files are expected to
  have suggestions for the single-row `epochs` and `task_table`, the processing module name `tasks` (the name Spyglass
  reads), and the per-camera pose containers without a description.

## Staging

- `inspect_output_folder` raises "No NWB files found": the output folder has no `sub-*/` folders. Check the path.
- `organize_nwbfiles` raises "holds stub files (nwb_stub/)": move or delete the `nwb_stub/` folder of the output
  folder.
- `organize_nwbfiles` raises "already holds organized NWB files": remove the dandiset folder, or choose a new one,
  and run it again.
- `upload_organized_files` raises "validation errors ..., nothing uploaded": fix the files or the dandiset metadata,
  then organize and upload again.

## Known issues

- The per-camera `PoseEstimation` containers are written without a description: `session_to_nwb` sets one, but
  NeuroConv does not write it yet.
- `Social_data/day_1/M7` has calibration files only for Camera3, Camera5 and Camera6, and no `calibration.json`. Those
  3 cameras are written with their calibration, the other 3 as plain devices.
- In social sessions, sDANNCE reports the subject's pose for the partner while the partner is not in the arena. In
  `Social_data/day_1/M4` the partner track matches the subject (mean distance under 10 mm) for frames 0 to 29,804 and
  78,126 to the end.
- ndx-hed's `HedNWBValidator.validate_file` raises on the `camera_id` cell of the task table, which holds 6 values.
  Validating the `HED` column alone (see [Metadata](metadata.md#tasks-and-hed)) works, and NWB Inspector reports
  nothing on the column.
- NeuroConv is installed from its `main` branch, for its HERD and DANNCE features. Its `add_fiber_photometry_devices()`
  creates a plain device for every entry of the metadata's devices, including the cameras, so `DANNCE` is the first
  slot of the converter and creates the calibrated cameras first.
