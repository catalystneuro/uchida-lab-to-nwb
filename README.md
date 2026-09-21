# uchida-lab-to-nwb

NWB conversion scripts for the [Uchida Lab](https://projects.iq.harvard.edu/uchidalab) data,
using [NeuroConv](https://github.com/catalystneuro/neuroconv).

**Project**: SFARI Autism Rat Models Consortium (ARC)
**Study**: Social behavior and observational fear learning in autism rat models
**PI**: Prof. Naoshige Uchida, Harvard University

## Data streams

- Fiber photometry (Doric BBC300, raw `.doric` HDF5 and processed MATLAB dF/F)
- 6-camera behavioral video (Basler, `.mp4` via campy)
- 3D pose estimation (DANNCE / social-DANNCE, `.mat`)
- pCampi synchronization TTL pulses (LabVIEW, `.h5`)

## Installation

```bash
conda env create -f make_env.yml
conda activate uchida-lab-to-nwb-env
```

Or with pip:

```bash
pip install -e .
```

## Usage

### Single session

```python
from uchida_lab_to_nwb.phillips_2025.convert_session import session_to_nwb
from uchida_lab_to_nwb.phillips_2025.utils.subject_metadata import get_subject_metadata
from pathlib import Path

subject_metadata = get_subject_metadata(
    subject_id="M4", xlsx_path=Path("H:/Uchida-CN-data-share/Subject metadata.xlsx")
)

session_to_nwb(
    session_dir_path=Path("H:/Uchida-CN-data-share/Hannah_data/M4-M7/Lone_data/day_1/M4"),
    output_dir_path=Path("~/nwb_output"),
    subject_metadata=subject_metadata,
    stub_test=True,
)
```

### All sessions

```python
from uchida_lab_to_nwb.phillips_2025.convert_all_sessions import dataset_to_nwb
from pathlib import Path

dataset_to_nwb(
    data_dir_path=Path("H:/Uchida-CN-data-share/Hannah_data/M4-M7/Lone_data"),
    output_dir_path=Path("~/nwb_output"),
    subject_metadata_path=Path("H:/Uchida-CN-data-share/Subject metadata.xlsx"),
    max_workers=1,
    stub_test=False,
)
```

## Repository structure

```text
src/uchida_lab_to_nwb/
└── phillips_2025/
    ├── interfaces/
    │   ├── pcampi_sync_interface.py              # pCampi TTL H5 reader
    │   └── processed_fiber_photometry_interface.py  # Lab-processed (interpolated) photometry reader
    ├── utils/
    │   └── subject_metadata.py                   # Per-subject metadata lookup (from Subject metadata.xlsx)
    ├── nwbconverter.py                           # Main converter class
    ├── convert_session.py                        # Single-session conversion script
    ├── convert_all_sessions.py                   # Batch conversion script
    ├── general_metadata.yaml                     # Lab/experiment metadata
    ├── fiber_photometry.yaml                     # Fiber photometry hardware metadata
    └── documentation/
        ├── conversion_notes.md                   # Detailed notes on data streams and conversion decisions
        └── project_track.md                      # Conversion progress tracker
```

Raw Doric fiber photometry (`DoricFiberPhotometryInterface`) and DANNCE pose + multi-camera
video (`DANNCEConverter`) are used directly from `neuroconv`, not reimplemented here.
