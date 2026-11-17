# Spyglass ingestion

[Spyglass](https://github.com/LorenFrankLab/spyglass) is a DataJoint pipeline that stores what an NWB file holds in a
MySQL database, so sessions can be queried and analyzed together. The converted files can be ingested into a local
Spyglass database: session metadata, cameras and videos, fiber photometry, multi-camera 3D pose, and the HERD and HED
annotations.

Upstream Spyglass doesn't ingest most of this yet. The missing pieces are open pull requests on LorenFrankLab/spyglass
(section 5). Until they are merged, the environment installs Spyglass from the tag `uchida-example-v1` of the
[CatalystNeuro fork](https://github.com/catalystneuro/spyglass), which combines upstream `master` with those PRs.
Tables from open PRs can change in review; section 5 explains how to update.

Everything is in [spyglass/](../../../../spyglass/):

- `docker-compose.yml`: the local MySQL database;
- `spyglass-env.yaml` and `bootstrap_wsl.sh`: the conda environment;
- `dj_local_conf.example.json`: template of the connection and storage settings;
- `check_connection.py`: checks the connection;
- `insert_full_session.py`: ingests files and reports what was ingested;
- `notebooks/`: three notebooks that read the database (section 4);
- `spyglass-ingestion-notes.md`: the state of the PRs this depends on.

## 1. Set up

Spyglass can't be imported on native Windows, so on Windows it runs in WSL2 (Ubuntu 24.04), with the database in
Docker Desktop. You need:

- WSL2 with Ubuntu 24.04, and [Miniforge](https://github.com/conda-forge/miniforge) installed in it at
  `/opt/miniforge3` (the path `bootstrap_wsl.sh` expects);
- Docker Desktop, with WSL integration turned on.

### Database

From `spyglass/`:

```bash
docker compose up -d
```

This starts the `spyglass-uchida-db` container (MySQL 8.0) on port 3307, with its data in a Docker volume. Docker
Desktop doesn't start it again after a reboot; then run `docker start spyglass-uchida-db`.

### Environment

From a Windows terminal:

```bash
wsl -d Ubuntu-24.04 -- bash /mnt/c/<path to repo>/spyglass/bootstrap_wsl.sh
```

This creates the `spyglass-uchida-lab-env` conda env from `spyglass-env.yaml`, or updates it if it exists, and then
installs package versions that pip can't resolve together with Spyglass's own pins: pynwb 4.2 and hdmf 6.2 (the files
use NWB 2.11), ndx-pose 0.4, ndx-hed 0.3 with numpy 2, and ndx-optogenetics 0.4.1. The header of `spyglass-env.yaml`
explains each one. Pip prints warnings about these conflicts; they are expected.

To run the notebooks, register the env as a Jupyter kernel once:

```bash
conda activate spyglass-uchida-lab-env
python -m ipykernel install --user --name spyglass-uchida-lab-env
```

### Configuration

Copy `dj_local_conf.example.json` to `dj_local_conf.json` in `spyglass/` (the copy is not tracked by git), and replace
`/home/<user>/spyglass_data` with a folder inside WSL. Spyglass keeps the NWB files it ingests in `raw/` and its own
output files in `analysis/`. A folder on the Linux side (not under `/mnt/c`) is much faster. The database settings
match `docker-compose.yml`.

The scripts and notebooks load this file before importing Spyglass, because Spyglass connects to the database when it
is imported. Check the setup with:

```bash
conda activate spyglass-uchida-lab-env
cd /mnt/c/<path to repo>/spyglass
python check_connection.py
```

It prints the connection and the Spyglass schemas on the server.

## 2. Ingest the files

Copy the converted NWB files into the `raw` folder of `dj_local_conf.json`, then pass their names to
`insert_full_session.py`, from `spyglass/` in the activated env:

```bash
python insert_full_session.py sub-M4_ses-day-1-lone.nwb sub-M4_ses-day-1-social.nwb
```

To ingest every file in the folder:

```bash
python insert_full_session.py $(cd ~/spyglass_data/raw && ls sub-*.nwb | grep -v '_\.nwb')
```

For each file, the script runs Spyglass's `insert_sessions()`, prints the number of rows per table, and lists the
errors Spyglass logged in its `InsertError` table. A file ingested correctly has no `InsertError` rows. Spyglass
writes a copy of each file next to it, with `_` added to the name (`sub-M4_ses-day-1-lone_.nwb`); the database
refers to that copy. If a file is already in the database, the script deletes its entry first, so a file can be
ingested again after a change. All 12 sessions take about 1.5 minutes.

To start from an empty database, for example after the tables changed (section 5), run `docker compose down -v` and
`docker compose up -d` from `spyglass/`. This deletes the database volume and everything in it; the NWB files are not
touched.

## 3. What is ingested

Rows per session:

| Data in the NWB file | Spyglass tables | Lone | Social |
| --- | --- | --- | --- |
| Session metadata, task table | `Session`, `Session.Experimenter`, `TaskEpoch` | 1 each | 1 each |
| Epoch and series valid times | `IntervalList` | 6 | 7 |
| External videos (`ImageSeries` VideoCamera1-6) | `VideoFile` | 6 | 6 |
| Camera calibration (`CalibratedCamera` Camera1-6) | `CameraCalibration` | 6 | 6 |
| 3D pose (`MultiCameraPoseEstimation`, one per rat) | `ImportedMultiCameraPose` | 1 | 2 |
| 3D pose body parts | `ImportedMultiCameraPose.BodyPart` | 23 | 46 |
| Per-camera links of the pose to the video and calibration | `ImportedMultiCameraPose.Camera` | 6 | 12 |
| Fiber photometry setup (`FiberPhotometryTable` rows) | `FiberPhotometryConfig` | 4 | 4 |
| Raw and interpolated photometry series | `FiberPhotometryResponseSeries` (`.Fiber`) | 4 (8) | 4 (8) |
| HERD ontology references | `ExternalResources` (`.Reference`) | 1 (29) | 1 (52) |
| HED schema, definitions and the task table's HED column | `HedMetadata`, `HedAnnotation`, `HedAnnotation.Row` | 1 each | 1 each |

Tables shared across sessions hold the 3 subjects, 6 cameras (`CameraDevice`), 2 tasks, 2 brain regions, 2
indicators, 2 excitation sources, 1 photodetector, 2 optical fibers and 18 ontology terms (`OntologyTerm`).
`ImportedPose`, `PositionSource`, `RawPosition`, `DIOEvents` and `SensorData` stay empty, because the files have no
data of those kinds.

The database stores metadata and the object ids of the NWB data. The signals and pose coordinates stay in the NWB
files; the tables' fetch methods (such as `FiberPhotometryResponseSeries.fetch1_dataframe()` or
`ImportedMultiCameraPose.fetch_pose_dataframe()`) read them from the copy in `raw/`.

## 4. Notebooks

The notebooks in [spyglass/notebooks/](../../../../spyglass/notebooks/) read the database, so ingest the files first.
Open them with the `spyglass-uchida-lab-env` kernel, from Jupyter started in WSL or from VS Code connected to WSL. Each
loads `../dj_local_conf.json` in its first cell.

- [spyglass_fiber_photometry_tutorial.ipynb](../../../../spyglass/notebooks/spyglass_fiber_photometry_tutorial.ipynb):
  the photometry setup of each session (indicators, excitation sources, fibers and brain regions), the raw and
  interpolated traces, and a comparison of all sessions.
- [spyglass_pose_tutorial.ipynb](../../../../spyglass/notebooks/spyglass_pose_tutorial.ipynb): the pose entries,
  cameras, videos and calibrations of each session, the 3D keypoints of a lone and a social session, and the keypoints
  projected onto video frames. The frames are read from the videos on the lab data share: set `DATA_SHARE` in its
  setup cell to the folder that holds `Uchida-CN-data-share` (`/mnt/h` for the H: drive).
- [spyglass_hed_herd_tutorial.ipynb](../../../../spyglass/notebooks/spyglass_hed_herd_tutorial.ipynb): the ontology
  terms linked to subjects, brain regions and keypoints, and the HED annotation of each session's task condition,
  validated against the HED schema.

Before working with the data, each notebook checks that every session in the database has the expected rows.

## 5. Upstream status and updates

The tables used here come from these pull requests on LorenFrankLab/spyglass:

| Data | Pull request |
| --- | --- |
| Fiber photometry | [#1637](https://github.com/LorenFrankLab/spyglass/pull/1637) |
| Cameras, task epoch cameras and external videos | [#1721](https://github.com/LorenFrankLab/spyglass/pull/1721) |
| HERD external resources | [#1722](https://github.com/LorenFrankLab/spyglass/pull/1722) |
| HED annotations | [#1723](https://github.com/LorenFrankLab/spyglass/pull/1723) |
| Camera calibration and multi-camera 3D pose | [#1724](https://github.com/LorenFrankLab/spyglass/pull/1724) |

Upstream Spyglass also needs pynwb 4 to read these files
([#1694](https://github.com/LorenFrankLab/spyglass/issues/1694)); the bootstrap installs it over Spyglass's pins. The
current state of each PR is in [spyglass-ingestion-notes.md](../../../../spyglass/spyglass-ingestion-notes.md) and in
[issue #13](https://github.com/catalystneuro/uchida-lab-to-nwb/issues/13).

The pose tables of #1724 are the most likely to change: the PR asks the Spyglass team whether they should move onto
the camera and calibration tables of Spyglass's Position V2. When a PR changes, a new tag of the fork is made and the
environment files point to it. To update:

1. Pull this repository.
2. Run `bootstrap_wsl.sh` again.
3. Reset the database (`docker compose down -v`, then `docker compose up -d`) and ingest the files again (section 2).
4. Re-run the notebooks.

Once all the PRs are merged, the environment will install a Spyglass release, and the tag and the notes file will be
removed.

## Known limitations

- The camera trigger TTL (`SyncTTL_campy_trigger`, an acquisition `TimeSeries`) is not ingested. Spyglass has no table
  for a generic acquisition `TimeSeries`; `DIOEvents` reads only `BehavioralEvents`.
- In `sub-M7_ses-day-1-social`, cameras 1, 2 and 4 have no calibration in the NWB file. That session has 3
  `CameraCalibration` rows, and 3 of the 6 `.Camera` rows of each rat link the video without a calibration.
- In 8 of the 12 sessions, the interpolated photometry series start with one isolated sample about 8 s before the
  rest. The `IntervalList` of the series covers the gap; the photometry notebook shows how to skip it.
