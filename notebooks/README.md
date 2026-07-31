# Uchida Lab — Phillips 2025 Example Notebook

This notebook demonstrates how to load and visualize the NWB data produced by the
Uchida Lab (Harvard) conversion pipeline for the Phillips 2025 / SFARI ARC dataset,
published as [DANDI:001935](https://dandiarchive.org/dandiset/001935).

**Two ways to load a session** (see Section 1 of the notebook):

- **Option A — Stream from DANDI**: reads directly from the archive over HTTP via
  `remfile`, no download needed. DANDI:001935 is currently embargoed, so this requires a
  DANDI API token with dataset access until the dataset is made public.
- **Option B — Read a local file**: reads an NWB file already on disk (e.g. output of
  `convert_session.py`, or a `dandi download`ed asset).

**Data streams covered:**

- Raw fiber photometry (Doric BBC300, 2 excitation channels × 3 ROIs)
- Processed dF/F traces (lab MATLAB pipeline, interpolated to video rate)
- 3D pose estimation via DANNCE (23 keypoints, ~50 Hz)
- Synchronization TTL channels (pCampi LabVIEW)
- Multi-camera behavioral video references (6 cameras)

## Installing the dependencies

```bash
conda env create --file environment.yml
conda activate uchida_demo
```

## Running the notebook

```bash
jupyter notebook phillips_2025_demo.ipynb
```

Run either the Option A (DANDI streaming) or Option B (local file) cell in Section 1 —
not both. For Option B, update `NWB_FILE_PATH` to point to your converted NWB file.
