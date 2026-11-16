# Data organization

The conversion reads the lab's data share as it is organized on the lab server. This page describes the layout it
expects, so that new recordings can be added and converted without changing the code.

## The experiment

Rats implanted with optical fibers in the nucleus accumbens (NAc) and the tail of the striatum (TS) behave freely in
an arena. Dopamine is recorded with the sensor GRABDA3m, with tdTomato as a control, by a Doric BBC300 fiber
photometry system. Behavior is recorded with 6 Basler cameras (campy) and tracked in 3D with DANNCE. pCampi
(LabVIEW) records the camera trigger pulses on a NIDAQ at 1 kHz; its clock is the time base of each file.

## Folder layout

```text
<data share>/
├── Subject metadata.xlsx                     one column per subject
└── Hannah_data/M4-M7/
    ├── Lone_data/
    │   └── day_<N>/
    │       └── M<id>/                        one session
    │           ├── YYMMDD_HHMMSS_M<id>.h5             pCampi sync
    │           ├── BBC300_Acq_*.doric                  raw Doric fiber photometry
    │           ├── interpolated_campy_and_doric.mat    lab-processed photometry
    │           ├── processed_dff.mat                   lab dF/F, not converted
    │           ├── DANNCE/save_data_AVG0.mat           3D pose
    │           ├── calibration/
    │           │   ├── calibration.json                camera intrinsics and extrinsics
    │           │   └── hires_cam<N>_params.mat         per-camera DANNCE calibration
    │           └── videos/
    │               └── Camera<1..6>/
    │                   ├── 0.mp4                       H.264, 1920x1200 at 50 fps
    │                   ├── frametimes.npy              frame index and elapsed seconds per frame
    │                   └── metadata.csv                campy acquisition settings, incl. frameRate
    └── Social_data/
        └── day_<N>/M<id>/                    same as Lone_data, except the pose:
            └── sDANNCE/predict05/save_data_AVG0.mat    3D pose of both rats
```

- A session folder needs exactly one `.h5` and one `.doric` file; folders without both are skipped.
- The processed photometry and the pose are converted only when their file and the `videos/` folder exist.
- The pCampi file name gives the session start time, in America/New_York, whatever the time zone of the computer
  running the conversion.
- The `sDANNCE/predict05/` folder also holds other DANNCE outputs (`init_save_data_AVG.mat`, `com3d_used.mat`,
  `M<id>day<n>_save_data_AVG0.mat`, a log); they are not read.

## Conditions

The condition is the name of the folder above the days, without `_data`, in lower case.

| Condition | Folder | Session | Pose file |
| --- | --- | --- | --- |
| lone | `Lone_data` | the implanted rat alone in the arena, about 30 minutes | `DANNCE/save_data_AVG0.mat` |
| social | `Social_data` | the implanted rat with a partner rat, about 35 minutes | `sDANNCE/predict05/save_data_AVG0.mat` |

In social sessions only the implanted rat has fiber photometry. The partner is not one of the subjects and has no
entry in the subject sheet; it appears only in the pose data. In `save_data_AVG0.mat`, `pred` has shape
`(n_frames, 1, 3, 23)` in lone sessions and `(n_frames, 2, 3, 23)` in social sessions, where animal index 0 is the
implanted rat (the one attached to the fiber cable) and index 1 the partner.

## Subjects and sessions

The dataset has subjects M4, M5 and M7, 2 days per condition: 12 sessions.

- The subject ID is the session folder name (`M4`).
- The session ID comes from the folder path: `Lone_data/day_1/M4` gives `day-1-lone`.

`Subject metadata.xlsx` is transposed: each row is a field and each column a subject. The conversion reads the rows
`Subject ID`, `Species`, `Strain / genotype`, `Sex`, `Date of birth`, `Weight at time of experiment`,
`Experimental group` and `Surgery date`. `Strain / genotype` is split at its last word, so `Long Evans WT` gives
strain `Long Evans` and genotype `WT`. A session whose subject is not in the sheet is skipped.

## Doric file

The conversion reads these streams of the `.doric` file:

| Stream | Signal |
| --- | --- |
| `BBC300_ROISignals_Series0001_CAM1EXC1_ROI01`, `..._ROI02` | control (568 nm, tdTomato), NAc and TS |
| `BBC300_ROISignals_Series0001_CAM1EXC2_ROI01`, `..._ROI02` | dopamine signal (473 nm, GRABDA3m), NAc and TS |
| `BBC300_Signals_Series0001_DigitalIO_DigitalCh1` | camera trigger pulses, used to align the times |

The file also has an ROI03 per excitation channel, which has no fiber implant and is not converted.

## pCampi file

The `.h5` file holds the NIDAQ digital inputs at 1 kHz in `digital_input/data`, with the channel names in its
`channel_names` attribute: `campy_trigger` (the camera trigger pulses) and `rbfmc_frames` (all zero in this dataset,
so it is not written). A channel with another name stops the conversion; see [Troubleshooting](troubleshooting.md).

## Lab processed photometry (.mat)

`interpolated_campy_and_doric.mat` is written by the lab's MATLAB script `interpolate_campy_and_doric2_clean.m`. Its
struct `interpolated_data` holds `channel_names` (`CAM1EXC1`, `CAM1EXC2`) and `roi_traces_interpolated`, one
`(n_samples, 3)` array of ROI fluorescence per channel, resampled to the camera trigger pulses. These are raw
fluorescence values, not dF/F. The first two columns (NAc, TS) are converted.

`processed_dff.mat` holds `dff_resG`, and `dff_resG2` in M5 and M7 sessions. It is not converted (see
[Data streams](data_streams.md#not-converted)).
