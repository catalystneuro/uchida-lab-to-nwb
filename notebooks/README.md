# Uchida Lab — Phillips 2025 Example Notebook

This notebook demonstrates how to load and visualize the NWB data produced by the
Uchida Lab (Harvard) conversion pipeline for the Phillips 2025 / SFARI ARC dataset.

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

Update `NWB_FILE_PATH` in the first code cell to point to your converted NWB file.
