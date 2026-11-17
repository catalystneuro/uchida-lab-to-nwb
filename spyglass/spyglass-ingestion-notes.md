# Spyglass ingestion notes

Tracks the Spyglass pull requests and issues that ingesting the DANDI:001935 files depends on, while they are under development. Remove this file once they are all merged into LorenFrankLab/spyglass and the environment installs a Spyglass release. How to set up Spyglass, ingest the files and run the notebooks is in [docs/spyglass_ingestion.md](../src/uchida_lab_to_nwb/phillips_2025/docs/spyglass_ingestion.md). The overview for the Spyglass team is https://github.com/catalystneuro/uchida-lab-to-nwb/issues/13.

Check the live state of each link before acting on it.

## Current build

`spyglass-env.yaml` and `bootstrap_wsl.sh` install the tag `uchida-example-v1` of https://github.com/catalystneuro/spyglass (`87b32300`). It is upstream `master` (`da36473c`) with these branches merged, in order: the #1637 branch (`feature/fiber-photometry-ingestion`), `camera-devices`, `multicam-pose-preview`, `herd-external-resources` and `hed-annotations`. The branches have since gained test-only and changelog commits that the tag does not include; they don't change ingestion.

Checked on 2026-11-17 against a freshly reset database, with an env built by `bootstrap_wsl.sh`: all 12 files ingest with no `InsertError` rows, and the three notebooks run. The old build is kept as the tag `uchida-integration-2026-11-10`.

## Spyglass PRs from the CatalystNeuro fork

Each data stream has its own branch off upstream `master` and its own PR on LorenFrankLab/spyglass. The PR texts name no lab, so the same PRs can serve the Olveczky and Gonzalez-Sulser ingestions. They were opened as drafts on 2026-11-17, and their CI waits for a maintainer's approval (first-time contributor).

| Branch | What it adds | Upstream PR |
| --- | --- | --- |
| `camera-devices` | ndx-pose `CalibratedCamera` and plain-Device cameras for `CameraDevice`, `TaskEpoch` and `VideoFile`; rate-based external videos | https://github.com/LorenFrankLab/spyglass/pull/1721 |
| `herd-external-resources` | HERD external resources (`OntologyTerm`, `ExternalResources`) | https://github.com/LorenFrankLab/spyglass/pull/1722 |
| `hed-annotations` | HED annotations (`HedMetadata`, `HedAnnotation`) | https://github.com/LorenFrankLab/spyglass/pull/1723 |
| `multicam-pose-preview` | `CameraCalibration`, `ImportedMultiCameraPose` (`.BodyPart`, `.Camera` with optional calibration). Merges `camera-devices`. The PR asks whether to move it onto Position V2 (#1649) | https://github.com/LorenFrankLab/spyglass/pull/1724 |
| `imported-events` | NWB core `EventsTable` (`ImportedEvents`). Not used by these files; kept for the Olveczky ingestion | not opened |

On upstream's CI setup (pynwb 3, `numpy<2`) the HERD, HED and pose tests skip, and so does the `CalibratedCamera` case of #1721: they need pynwb 4 or ndx-pose 0.4 (#1694).

The fork PRs used before (https://github.com/catalystneuro/spyglass/pull/1, /2 and /3) were closed on 2026-11-17. Branch `ndx-pose-multicamera` (fork PR #1) is retired; its code is split between `camera-devices`, `multicam-pose-preview` and `imported-events`.

## Other upstream work these files depend on

| Link | State | Relevance |
| --- | --- | --- |
| https://github.com/LorenFrankLab/spyglass/pull/1637 | PR, open (edeno) | Fiber photometry ingestion (`common_photometry`). In the current build unchanged. Its review may change the photometry tables. |
| https://github.com/LorenFrankLab/spyglass/pull/1649 | PR, open (CBroz1) | Position V2 camera rig and calibration tables. #1724 asks whether the pose import should use them. |
| https://github.com/LorenFrankLab/spyglass/issues/1694 | issue, open | pynwb>=4 / hdmf>=6. The files need pynwb 4.2 / hdmf 6.2; the bootstrap installs them over Spyglass's pins. To do: ask on the issue whether the maintainers want a PR from us. |
| https://github.com/LorenFrankLab/spyglass/pull/1609 | PR, open (edeno) | Spyglass pins `numpy<2` and `scipy<1.13` until this lands; the bootstrap overrides both because ndx-hed needs numpy 2. |
| https://github.com/LorenFrankLab/ndx-franklab-novela/pull/26 | PR, open (CBroz1) | Reworks pyproject, keeps `hdmf<5`. |
| https://github.com/LorenFrankLab/ndx-franklab-novela/pull/27 | PR, open (samuelbray32) | Bumps to `ndx-optogenetics>=0.4.1`. We commented on 2026-11-09 suggesting `<0.5` and a ndx-ophys-devices cap. |
| branch `relax-hdmf-pin-optogenetics-0.4.1` on https://github.com/catalystneuro/ndx-franklab-novela | branch, no PR | Relaxes novela's `hdmf<5`. To do: after #26 merges, rebase to only the hdmf change and open the upstream PR. |
| https://github.com/LorenFrankLab/spyglass/issues/1383 | issue, open | Support for ndx-events data. Addressed for core `EventsTable` by `imported-events`. |

## When a PR changes or merges

1. Rebuild the integration branch `uchida-integration` on the fork from upstream `master` and the PR branches still open, and tag it (`uchida-example-v2`, ...).
2. Point `spyglass-env.yaml` and `bootstrap_wsl.sh` at the new tag, or at a Spyglass release once everything is merged.
3. Rebuild the env, reset the database, ingest the 12 files and re-run the notebooks, as in the docs. Update the notebooks if table names or fetchers changed.
4. Update this file, the docs and https://github.com/catalystneuro/uchida-lab-to-nwb/issues/13.
