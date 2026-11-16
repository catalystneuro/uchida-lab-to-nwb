# Data streams

Each NWB file holds the streams below. `session_to_nwb` in `convert_session.py` adds each one when its files are in
the session folder (see [Data organization](data_organization.md)), and `Phillips2025NWBConverter` in
`nwbconverter.py` registers one interface slot per stream.

| Stream | Slot | Interface | Source file |
| --- | --- | --- | --- |
| raw fiber photometry, control | `DoricControl` | `DoricFiberPhotometryInterface` (NeuroConv) | `.doric` |
| raw fiber photometry, dopamine signal | `DoricDopamineSignal` | `DoricFiberPhotometryInterface` (NeuroConv) | `.doric` |
| processed fiber photometry, control | `InterpolatedFPControlSignal` | `ProcessedFiberPhotometryInterface` | `interpolated_campy_and_doric.mat` |
| processed fiber photometry, dopamine signal | `InterpolatedFPDopamineSignal` | `ProcessedFiberPhotometryInterface` | `interpolated_campy_and_doric.mat` |
| lab dF/F (disabled) | `DffDopamineSignal` | `DffFiberPhotometryInterface` | `processed_dff.mat` |
| pose and 6 videos | `DANNCE` | `DANNCEConverter` (NeuroConv) | `save_data_AVG0.mat`, `videos/`, `calibration/` |
| partner pose (social only) | `DANNCEPartner` | `DANNCEInterface` (NeuroConv) | `sDANNCE/predict05/save_data_AVG0.mat` |
| sync pulses | `PCampiSyncCampyTrigger`, `PCampiSyncRbfmcFrames` | `PCampiSyncInterface` | `.h5` |
| epoch and task | `TaskEpoch` | `TaskEpochInterface` | `.h5` (recording length) |

The interfaces of this package are in `interfaces/`.

## Raw fiber photometry

Two series, one per excitation channel, each with two columns, NAc and TS:

- control: 568 nm excitation of tdTomato (Doric `CAM1EXC1`);
- dopamine signal: 473 nm excitation of GRABDA3m (Doric `CAM1EXC2`).

The values are the demodulated fluorescence of the Doric software, at its own sampling times. The stream names are set
in `_DORIC_INTERFACE_CONFIG` in `convert_session.py`. Both series point to the rows of one fiber photometry table that
describe the fiber, LED, photodetector and indicator of each column (see [Metadata](metadata.md)).

## Processed fiber photometry

The same two channels from `interpolated_campy_and_doric.mat`, resampled by the lab's MATLAB script to the camera
trigger pulses (about 50 Hz). They are raw fluorescence, not dF/F, and are written to the `ophys` processing module.

## Pose and video

`DANNCEConverter` writes:

- the 3D pose of the implanted rat: one series per landmark of the 23-point rat23 skeleton, in millimeters;
- the 6 camera videos as external files: the NWB file holds the path to each `0.mp4`, relative to the NWB file, and
  its frame times from `frametimes.npy`;
- one camera device per camera, with its calibration (intrinsics and extrinsics) when the `calibration/` folder has
  it.

The pose file has no table that maps each prediction to a video frame, so the pose times are the frame index divided
by the camera frame rate (`frameRate` in `videos/Camera1/metadata.csv`).

In social sessions, `DANNCEPartner` writes the partner's pose (animal index 1) from the same file, as a second pose
container that uses the same cameras and videos. The partner is treated as part of the task: it has no `Subject`, and
its skeleton is not linked to the subject of the file.

## Sync pulses

`PCampiSyncInterface` writes one channel of the pCampi `.h5` file per instance, as a `TimeSeries` at 1 kHz.
`convert_session.py` adds one instance per channel found in the file. `rbfmc_frames` is all zero in this dataset and
is skipped with a warning. The pCampi file also gives the session start time.

## Epoch and task

`TaskEpochInterface` writes one epoch spanning the pCampi recording and one task row, in the layout Spyglass reads
(see [NWB file structure](nwb_file_structure.md#epoch-and-task)). The task text and its HED annotation come from
`general_metadata.yaml` (see [Metadata](metadata.md#tasks-and-hed)).

## Time alignment

All streams are put on the pCampi clock by `temporally_align_data_interfaces()` in `nwbconverter.py`.

The camera trigger pulses are recorded twice: by pCampi (`campy_trigger`) and by the Doric digital input `DigitalCh1`,
each on its own 1 kHz clock. Before the regular 50 Hz train, both record one longer start-of-recording pulse; its
falling edge is the same event on both clocks.

1. Raw photometry: the offset between the clocks is the first `campy_trigger` falling edge minus the first
   `DigitalCh1` falling edge. The series keep their Doric times, shifted by that offset.
2. Processed photometry: the lab's MATLAB script resamples the photometry onto the rising edges of `DigitalCh1`,
   counting the already-high first sample as an extra edge. `_compute_doric_trigger_pulse_timestamps()` reproduces
   those times. When their number matches the number of samples in the `.mat` file, they are written, shifted by the
   offset. Otherwise the series is written at the camera frame rate from its first sample, shifted by the offset, with
   a warning.
3. Pose and video: shifted so that their time 0 is the first rising edge of the regular `campy_trigger` train
   (`drop_spurious_leading_edges()` skips the start-of-recording pulse). The partner pose gets the same shift.

In 9 of the 12 sessions the processed photometry has one sample per trigger pulse, as in step 2. In
`Lone_data/day_1/M7`, `Social_data/day_1/M4` and `Social_data/day_1/M7` it has one sample per saved video frame, so
these 3 sessions use the camera frame rate.

Every session has about 74 more `campy_trigger` pulses than saved video frames (68 to 78). The alignment uses one shift
per stream, so this does not affect it, but an alignment of each frame to its pulse would have to account for it.

## Not converted

- `processed_dff.mat`: what `dff_resG` and `dff_resG2` hold, and why their scale differs across sessions, is not
  known. `DffFiberPhotometryInterface` is ready but disabled. To enable it, uncomment the three "DffDopamineSignal"
  blocks in `convert_session.py` (the import, the source data and the table region) and the
  `fiber_photometry_dff_dopamine_signal` block at the end of `fiber_photometry.yaml`, all together. Its mapping of
  `dff_resG` to NAc and `dff_resG2` to TS is an assumption to check first.
- Doric ROI03: no fiber implant.
- pCampi `rbfmc_frames`: all zero.
- `Channels.csv`: a derived envelope feature used for sleep and seizure scoring, not raw data.
