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
conda activate uchida_lab_to_nwb_env
```

Or with pip:

```bash
pip install -e ".[phillips_2025]"
```

## Usage

### Single session

```python
from uchida_lab_to_nwb.phillips_2025.phillips_2025_convert_session import session_to_nwb
from pathlib import Path

session_to_nwb(
    session_dir_path=Path("H:/Uchida-CN-data-share/Hannah_data/M4-M7/Lone_data/day_1/M4"),
    output_dir_path=Path("~/nwb_output"),
    stub_test=True,
)
```

### All sessions

```python
from uchida_lab_to_nwb.phillips_2025.phillips_2025_convert_all_sessions import dataset_to_nwb
from pathlib import Path

dataset_to_nwb(
    data_dir_path=Path("H:/Uchida-CN-data-share/Hannah_data/M4-M7/Lone_data"),
    output_dir_path=Path("~/nwb_output"),
    max_workers=1,
    stub_test=False,
)
```

## Repository structure

```
src/uchida_lab_to_nwb/
└── phillips_2025/
    ├── interfaces/
    │   ├── doric_fiber_photometry_interface.py   # Raw Doric .doric reader
    │   ├── doric_processed_photometry_interface.py  # Processed dF/F .mat reader
    │   ├── pcampi_sync_interface.py              # pCampi TTL H5 reader
    │   └── sdannce_interface.py                  # DANNCE 3D pose reader
    ├── phillips_2025_nwbconverter.py             # Main converter + sync logic
    ├── phillips_2025_convert_session.py          # Single-session conversion script
    ├── phillips_2025_convert_all_sessions.py     # Batch conversion script
    └── phillips_2025_metadata.yaml               # Lab/experiment metadata
```
