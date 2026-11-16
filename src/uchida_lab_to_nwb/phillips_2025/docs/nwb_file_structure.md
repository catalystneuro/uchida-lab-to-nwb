# NWB file structure

Each file holds one session. This page lists where each part of the session is stored. Times are in seconds from the
start of the pCampi recording (`session_start_time`, in America/New_York).

| Path in the file | Content |
| --- | --- |
| `acquisition/FiberPhotometryRawControlSignal` | raw control fluorescence (568 nm, tdTomato), columns NAc and TS |
| `acquisition/FiberPhotometryRawDopamineSignal` | raw dopamine signal fluorescence (473 nm, GRABDA3m), columns NAc and TS |
| `acquisition/SyncTTL_campy_trigger` | pCampi camera trigger pulses at 1 kHz |
| `acquisition/VideoCamera<1..6>` | the camera videos, as links to the `.mp4` files, with their frame times |
| `processing/ophys/FiberPhotometryInterpolatedControl` | control fluorescence resampled to the camera triggers, columns NAc and TS |
| `processing/ophys/FiberPhotometryInterpolatedDopamineSignal` | dopamine signal fluorescence resampled to the camera triggers, columns NAc and TS |
| `processing/behavior/PoseEstimationDANNCE` | 3D pose of the implanted rat, one series per landmark |
| `processing/behavior/PoseEstimationDANNCEPartner` | 3D pose of the partner rat (social sessions) |
| `processing/behavior/Skeletons` | the rat23 skeleton of each pose container |
| `processing/tasks/task_table` | the task of the session |
| `intervals/epochs` | one epoch spanning the recording |
| `general/fiber_photometry` | fiber photometry table and indicators |
| `general/hed_schema` | HED schema version and the lab's HED definitions |
| `general/devices` | cameras (with calibration), LEDs, photodetector, optical fibers |
| `general/subject` | subject ID, species, strain, genotype, sex, description, and date of birth and weight when the sheet has them |
| `general/external_resources` | ontology terms (HERD) |

The processed photometry and the pose are present when their files were in the session folder (see
[Data streams](data_streams.md)).

## Fiber photometry series

All photometry series are `FiberPhotometryResponseSeries` (ndx-fiber-photometry) with two columns, NAc then TS. Each
points to its rows of the fiber photometry table, which give the location, wavelengths, indicator, optical fiber,
LED and photodetector of each column. The raw series have the Doric sampling times; the processed series have the
times of the camera trigger pulses.

## Pose and video

`PoseEstimationDANNCE` is a `MultiCameraPoseEstimation` (ndx-pose) that holds one `PoseEstimationSeries` per landmark,
with x, y, z in millimeters, and one `PoseEstimation` per camera that links the camera device and its video. The
camera devices are `CalibratedCamera` objects with the intrinsics and extrinsics of the calibration. The videos are
`ImageSeries` with an external file path, relative to the NWB file; keep the videos next to the file as organized for
DANDI (see [DANDI staging](dandi_staging.md)).

## Epoch and task

The layout follows what Spyglass reads into `IntervalList`, `Task` and `TaskEpoch`:

- `epochs`: one row from 0 to the end of the pCampi recording, tagged `01_lone` or `01_social`.
- `processing/tasks/task_table`: one row with `task_name` (`lone` or `social`), `task_description`,
  `task_environment` (`arena`), `camera_id` (the camera numbers, `[1, 2, 3, 4, 5, 6]`), `task_epochs` (`[1]`) and
  `HED`, a `Def/` reference to a definition in `general/hed_schema`. A session without pose data has no camera devices
  and an empty `camera_id`.

## Reading a file

```python
from pynwb import NWBHDF5IO

with NWBHDF5IO("sub-M4_ses-day-1-social.nwb", "r") as io:
    nwbfile = io.read()

    dopamine = nwbfile.acquisition["FiberPhotometryRawDopamineSignal"]
    dopamine_nac, dopamine_times = dopamine.data[:, 0], dopamine.timestamps[:]

    pose = nwbfile.processing["behavior"]["PoseEstimationDANNCE"]
    snout = pose.pose_estimation_series["PoseEstimationSeriesSnout"]
    snout_xyz, pose_times = snout.data[:], snout.get_timestamps()[:]

    task = nwbfile.processing["tasks"]["task_table"].to_dataframe()
    epochs = nwbfile.epochs.to_dataframe()
```

The [example notebook](../../../../notebooks/dandi_001935_tutorial.ipynb) shows each stream, the pose projected onto a
video frame, the partner rat, the ontology terms and the HED annotation. Files on DANDI can also be opened in the
browser with [Neurosift](https://neurosift.app).
