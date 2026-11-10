# Spyglass ingestion notes

Status of ingesting the converted DANDI:001935 NWB files into Spyglass, and the pull requests and issues this depends on. Check the live state of each link before acting on it.

## Ingestion status

Checked on 2026-11-10: all 12 converted files (M4, M5, M7; day 1 and 2; lone and social) ingest with `insert_full_session.py` and no `InsertError` rows. A fresh env built from `spyglass-env.yaml` with `bootstrap_wsl.sh` ingested all 12 in about 1.5 minutes.

Rows per session:

| Table | Lone | Social | From the NWB file |
| --- | --- | --- | --- |
| `Session`, `Session.Experimenter`, `TaskEpoch` | 1 each | 1 each | session metadata, `tasks/task_table` |
| `IntervalList` | 6 | 7 | epochs and series valid times |
| `VideoFile` | 6 | 6 | `ImageSeries` VideoCamera1-6 |
| `CameraCalibration` | 6 | 6 | `CalibratedCamera` Camera1-6 |
| `ImportedMultiCameraPose` | 1 | 2 | `MultiCameraPoseEstimation` (subject, and partner in social sessions) |
| `ImportedMultiCameraPose.BodyPart` | 23 | 46 | 3D `PoseEstimationSeries` |
| `ImportedMultiCameraPose.Camera` | 6 | 12 | per-camera `PoseEstimation` linked to video and calibration |
| `FiberPhotometryConfig` | 4 | 4 | `FiberPhotometryTable` rows |
| `FiberPhotometryResponseSeries` (`.Fiber`) | 4 (8) | 4 (8) | raw and interpolated series |
| `ExternalResources` (`.Reference`) | 1 (29) | 1 (52) | `HERD` |
| `HedMetadata`, `HedAnnotation`, `HedAnnotation.Row` | 1 each | 1 each | `HedLabMetaData`, `HedTags` column of the task table |

`ImportedPose`, `ImportedEvents`, `PositionSource`, `RawPosition`, `DIOEvents` and `SensorData` stay empty because the files have no data of those kinds. Shared tables: 3 subjects, 6 camera devices, 2 tasks, 2 brain regions, 2 indicators, 2 excitation sources, 1 photodetector, 2 optical fibers, 18 ontology terms.

`notebooks/spyglass_fiber_photometry_tutorial.ipynb` was re-run on the same date; its completeness checks pass for all 12 sessions.

## Environment

`spyglass-env.yaml` plus `bootstrap_wsl.sh` build the `spyglass-uchida-lab-env` conda env inside WSL2 (Ubuntu-24.04). Spyglass is installed from the `uchida-integration` branch of https://github.com/catalystneuro/spyglass, which is upstream `master` with the branches listed below merged in. The yaml header explains each pin the bootstrap script adds on top of the yaml.

The database is the `spyglass-uchida-db` MySQL container from `docker-compose.yml`, on 127.0.0.1:3307. Docker Desktop does not start the container on boot; run `docker start spyglass-uchida-db` first.

Scripts in this folder:

- `check_connection.py`: connects and declares the Spyglass schemas.
- `insert_full_session.py`: runs `insert_sessions()` on the given files, then prints row counts per table and the `InsertError` log. Re-running a file deletes its previous entry first.
- `insert_fiber_photometry.py`, `dry_run_insertion.py`: earlier photometry-only scripts.
- `notebooks/spyglass_fiber_photometry_tutorial.ipynb`: reads the photometry data back out of the database.

## Pull requests and issues

### Spyglass branches on the CatalystNeuro fork

Each feature lives on its own branch off upstream `master`, with a PR against the fork's `master` for review before an upstream PR is opened. All are merged into `uchida-integration`.

| Branch | What it adds | Fork PR | Upstream PR |
| --- | --- | --- | --- |
| `ndx-pose-multicamera` | ndx-pose 0.4 `MultiCameraPoseEstimation` (`ImportedMultiCameraPose`, `CameraCalibration`), calibrated and plain-Device cameras for `VideoFile`/`TaskEpoch`, ndx-events `EventsTable` (`ImportedEvents`) | https://github.com/catalystneuro/spyglass/pull/1 | not opened |
| `herd-external-resources` | HERD external resources (`OntologyTerm`, `ExternalResources`) | https://github.com/catalystneuro/spyglass/pull/2 | not opened |
| `hed-annotations` | HED annotations (`HedMetadata`, `HedAnnotation`) | https://github.com/catalystneuro/spyglass/pull/3 | not opened |

### Upstream Spyglass (LorenFrankLab/spyglass)

| Link | Type | Author | Relevance |
| --- | --- | --- | --- |
| https://github.com/LorenFrankLab/spyglass/pull/1637 | PR, open | edeno | Fiber photometry ingestion (`common_photometry`). Merged into `uchida-integration` from branch `feature/fiber-photometry-ingestion`. |
| https://github.com/LorenFrankLab/spyglass/issues/1694 | issue, open | samuelbray32 | Compatibility with pynwb>=4. The converted files need pynwb 4.2 / hdmf 6.2; the bootstrap installs them over Spyglass's pins. |
| https://github.com/LorenFrankLab/spyglass/pull/1609 | PR, open | edeno | Spike sorting v2 on SpikeInterface 0.104. Spyglass pins `numpy<2` and `scipy<1.13` until this lands; the bootstrap overrides both because ndx-hed needs numpy 2. |
| https://github.com/LorenFrankLab/spyglass/issues/1383 | issue, open | alessandratrapani | Support for ndx-events data. Addressed by the `EventsTable` part of the `ndx-pose-multicamera` branch. |
| https://github.com/LorenFrankLab/spyglass/issues/1634 | issue, open | alessandratrapani | EEG support. Not needed for Uchida; tracked for gonzalez-sulser-lab-to-nwb, which reuses these branches. |

### ndx-franklab-novela (LorenFrankLab/ndx-franklab-novela)

novela pins `hdmf<5` and `ndx-optogenetics==0.3.0`, which blocks ndx-pose 0.4 and ndx-hed. Spyglass pins the same ndx-optogenetics version.

| Link | Type | Author | Relevance |
| --- | --- | --- | --- |
| https://github.com/LorenFrankLab/ndx-franklab-novela/pull/26 | PR, open | CBroz1 | Reworks pyproject, keeps `hdmf<5`. |
| https://github.com/LorenFrankLab/ndx-franklab-novela/pull/27 | PR, open | samuelbray32 | Bumps to `ndx-optogenetics>=0.4.1`. We commented on 2026-11-09 suggesting `<0.5` and a ndx-ophys-devices cap. |
| branch `relax-hdmf-pin-optogenetics-0.4.1` on https://github.com/catalystneuro/ndx-franklab-novela | branch, no PR | | Relaxes `hdmf<5`. Plan: after #26 merges, rebase to only the hdmf change and open the upstream PR. |

### Planned upstream PRs, in order

1. ndx-franklab-novela: relax `hdmf<5`.
2. Spyglass: pynwb>=4 / hdmf>=6 (#1694).
3. Spyglass: fiber photometry (#1637, maintained upstream).
4. Spyglass: multi-camera pose, cameras, ndx-events (`ndx-pose-multicamera`).
5. Spyglass: HED (`hed-annotations`).
6. Spyglass: HERD (`herd-external-resources`); independent of the others.

Ask the Spyglass and novela maintainers before opening any of these.

## Known gaps

- `SyncTTL_campy_trigger` (acquisition `TimeSeries`, the camera trigger TTL) is not ingested. Spyglass has no table for a generic acquisition `TimeSeries`; `DIOEvents` reads only `BehavioralEvents` in `processing/behavior`.
- `ImportedMultiCameraPose.Camera` links a pose camera to its video and calibration, so cameras without a `CalibratedCamera` are skipped there. In `sub-M7_ses-day-1-social`, cameras 1, 2 and 4 are plain `Device`s, so that session has 3 `CameraCalibration` rows and 6 `.Camera` rows (3 per animal). Their videos are still in `VideoFile`.
- In 8 of the 12 sessions the interpolated (camera-clock) photometry series start with one isolated sample about 8 s before the rest. `IntervalList` covers the gap; the notebook shows how to skip it.
