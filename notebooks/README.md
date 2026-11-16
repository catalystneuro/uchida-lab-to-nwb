# Uchida Lab (Phillips 2025) Example Notebook

`dandi_001935_tutorial.ipynb` shows how to load and visualize the NWB files from the Uchida Lab
(Harvard) Phillips 2025 / SFARI ARC dataset, published as
[DANDI:001935](https://dandiarchive.org/dandiset/001935). Each file is one session of a rat
recorded alone (lone) or with a partner rat (social).

## What the notebook covers

- Subject metadata and the file structure
- Fiber photometry hardware: the `FiberPhotometryTable`, fibers and implant coordinates, light
  sources, photodetector and indicators
- Raw fiber photometry (Doric BBC300): dopamine signal (GRABDA3m) and control (tdTomato), 2
  columns each for the nucleus accumbens and the tail of the striatum
- Photometry interpolated to the video frame rate by the lab's MATLAB pipeline
- The 6 behavior videos, stored as external files
- 3D pose estimation (DANNCE, 23 keypoints, 50 Hz), the skeleton, and the pose projected onto a
  video frame through the camera calibration
- Social sessions: the partner rat's pose, when the partner is in the arena, and both rats
  overlaid on a video frame
- Ontology terms (HERD) linked to the metadata
- The session's epoch and task, and their HED annotation, expanded and validated

## Loading a session

Set `USE_DANDI` in the "Choose which source to explore" cell.

- `USE_DANDI = True` streams the file from the DANDI Archive with `remfile`, without downloading
  it. The loader calls `dandi_authenticate()`, so it needs a DANDI API token (set the
  `DANDI_API_KEY` environment variable) while the Dandiset is embargoed.
- `USE_DANDI = False` reads a file from disk. Set `local_directory` to the folder holding the
  subject's files, named `sub-<subject>_ses-<session>.nwb` as written by `convert_session.py`.

The social partner section loads the social session of the same subject, so both the lone and
the social file need to be available.

## Installing the dependencies

```bash
conda env create --file environment.yml
conda activate uchida_demo
```

## Running the notebook

```bash
jupyter notebook dandi_001935_tutorial.ipynb
```
