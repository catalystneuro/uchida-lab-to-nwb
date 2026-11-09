# uchida-lab-to-nwb

NWB conversion scripts for the [Uchida Lab](https://projects.iq.harvard.edu/uchidalab) data,
using [NeuroConv](https://github.com/catalystneuro/neuroconv).

**Project**: SFARI Autism Rat Models Consortium (ARC)
**Study**: Social behavior and observational fear learning in autism rat models
**PI**: Prof. Naoshige Uchida, Harvard University
**Dandiset**: [DANDI:001935](https://dandiarchive.org/dandiset/001935) (embargoed)

## Dataset

12 sessions: subjects M4, M5 and M7, 2 days each, in two conditions. In the lone condition the
implanted rat is alone in the arena; in the social condition a partner rat is with it. Each session
becomes one NWB file, `sub-<subject>/sub-<subject>_ses-day-<N>-<lone|social>.nwb`.

## Data streams

- Fiber photometry, raw (Doric BBC300, `.doric`): dopamine sensor GRABDA3m and tdTomato control in
  the nucleus accumbens and the tail of the striatum
- Fiber photometry resampled to the camera triggers by the lab's MATLAB pipeline
  (`interpolated_campy_and_doric.mat`)
- 6-camera behavioral video (Basler, `.mp4` via campy), linked as external files
- 3D pose estimation (DANNCE / social DANNCE, `.mat`, 23 keypoints); in social sessions also the
  partner rat's pose
- pCampi synchronization TTL pulses (LabVIEW, `.h5`), which set the session's time base
- One epoch and one task per session, in the layout Spyglass reads, annotated with HED
- Ontology terms (HERD) for species, strain, experimenter, institution and anatomy

The lab-computed dF/F (`processed_dff.mat`) is not converted until the lab confirms what it
holds; its interface is ready but disabled. See
[conversion_notes.md](src/uchida_lab_to_nwb/phillips_2025/documentation/conversion_notes.md).

## Installation

```bash
conda env create -f make_env.yml
conda activate uchida-lab-to-nwb-env
```

Or with pip:

```bash
pip install -e .
```

NeuroConv is installed from its `main` branch, which holds the HERD and DANNCE features this
conversion needs and which are not released yet.

## Usage

Each script has an `if __name__ == "__main__":` block at the bottom with the paths used for the
conversion (data share on `H:/Uchida-CN-data-share`, output in `H:/uchida-nwbfiles`). Edit the paths
there and run the file. Keep the output folder on the same drive as the data share: the NWB files
link the videos by a path relative to the file, which is not possible across drives.

1. Convert: `convert_all_sessions.py` converts every session of `Lone_data` and `Social_data`.
   `convert_session.py` converts one session; set `stub_test=True` for a quick small file.
2. Inspect: `inspection.py` runs NWB Inspector (DANDI configuration) on every converted file. It
   writes one report per file to `inspector_reports/` and a table, `inspection_summary.csv`, to the
   output folder.
3. Upload: `upload_to_DANDI.py` copies the files into a local dandiset folder organized as DANDI
   expects, prints how they compare with the files already on the draft, and uploads them once
   `upload = True` is set. It needs a DANDI API key in the `DANDI_API_KEY` environment variable.

The same steps from Python:

```python
from uchida_lab_to_nwb.phillips_2025.convert_all_sessions import dataset_to_nwb
from uchida_lab_to_nwb.phillips_2025.inspection import inspect_output_folder

dataset_to_nwb(
    data_dir_path="H:/Uchida-CN-data-share/Hannah_data/M4-M7/Lone_data",
    output_dir_path="H:/uchida-nwbfiles",
    subject_metadata_path="H:/Uchida-CN-data-share/Subject metadata.xlsx",
    max_workers=1,
)
inspect_output_folder("H:/uchida-nwbfiles")
```

## Example notebook

[notebooks/dandi_001935_tutorial.ipynb](notebooks/dandi_001935_tutorial.ipynb) loads a session and
shows each data stream. See [notebooks/README.md](notebooks/README.md).

## Repository structure

```text
src/uchida_lab_to_nwb/
└── phillips_2025/
    ├── interfaces/
    │   ├── pcampi_sync_interface.py                 # pCampi TTL channels (.h5), session start time
    │   ├── processed_fiber_photometry_interface.py  # Lab-resampled photometry (interpolated_campy_and_doric.mat)
    │   ├── task_epoch_interface.py                  # Epoch, Spyglass task table and HED
    │   └── dff_fiber_photometry_interface.py        # Lab dF/F (processed_dff.mat), disabled
    ├── utils/
    │   ├── constants.py                             # rat23 skeleton landmarks and edges
    │   └── subject_metadata.py                      # Subject metadata from Subject metadata.xlsx
    ├── nwbconverter.py                              # Converter class and temporal alignment
    ├── convert_session.py                           # Converts one session
    ├── convert_all_sessions.py                      # Converts all sessions of a condition
    ├── inspection.py                                # NWB Inspector on the converted files
    ├── upload_to_DANDI.py                           # Organize and upload to DANDI
    ├── general_metadata.yaml                        # Lab, experiment, task, HED and ontology metadata
    ├── fiber_photometry.yaml                        # Fiber photometry hardware metadata
    └── documentation/
        ├── conversion_notes.md                      # Data streams, decisions, open questions
        ├── project_track.md                         # Progress tracker
        └── explore_sync_signals.py                  # Exploration of the pCampi and Doric sync signals
notebooks/
├── dandi_001935_tutorial.ipynb                      # Example notebook
└── environment.yml
```

Raw Doric fiber photometry (`DoricFiberPhotometryInterface`) and DANNCE pose with the multi-camera
video (`DANNCEConverter`, `DANNCEInterface`) are used directly from NeuroConv.
