# Converting sessions

A session is one subject on one day in one condition and becomes one NWB file,
`sub-<subject>/sub-<subject>_ses-day-<N>-<condition>.nwb`. Sessions are converted with the scripts of the package
(see the [README](../../../../README.md#installation) to install it). Run them from the conda environment of the
package:

```bash
conda activate uchida-lab-to-nwb-env
```

Each script has an `if __name__ == "__main__":` block at the bottom with placeholder paths: the data share (see
[Data organization](data_organization.md)) and an output folder for the NWB files and reports. Edit them, then run the
file.

Keep the output folder on the same drive as the data share. The NWB files link the videos by a path relative to the
file, which is not possible across drives.

## 1. Convert one session as a stub

In `convert_session.py`, set `data_share_path`, `output_dir_path` and the session, set `stub_test=True`, and run:

```bash
python src/uchida_lab_to_nwb/phillips_2025/convert_session.py
```

A stub file holds the first 100 samples of each photometry series and of the pose, and the first 10 seconds of the
sync signal and the epoch, and is written to `<output folder>/nwb_stub/` (an existing stub is replaced). The videos
are linked in full. It is a quick way to check the metadata after a change; open it as shown in
[NWB file structure](nwb_file_structure.md).

## 2. Convert all sessions

In `convert_all_sessions.py`, set `data_share_path` and `output_dir_path`, and run:

```bash
python src/uchida_lab_to_nwb/phillips_2025/convert_all_sessions.py
```

This converts every session of `Lone_data` and `Social_data`: each `day_*/M*/` folder with a `.h5` and a `.doric`
file. The `__main__` block sets `overwrite=True`, so existing files are replaced; with `overwrite=False`, sessions
whose NWB file exists are skipped, which converts only new sessions after recordings are added to the share.
`max_workers` sets how many sessions are converted in parallel.

A session that fails does not stop the others: its arguments and traceback are written to
`<output folder>/exceptions/ERROR_<condition>_day_<N>_M<id>.txt`. See [Troubleshooting](troubleshooting.md).

## 3. Inspect

In `inspection.py`, set `output_dir_path`, and run:

```bash
python src/uchida_lab_to_nwb/phillips_2025/inspection.py
```

This runs NWB Inspector with the DANDI configuration on every `<output folder>/sub-*/*.nwb` file (stubs are left out)
and writes:

- `inspector_reports/<file name>.txt`: the report of each file.
- `inspection_summary.csv`: one row per file, with its subject, session, the number of inspector messages per
  importance level, and `herd_references`, the number of ontology references in the file.

A file with `CRITICAL` messages cannot be uploaded to DANDI.

## Output folder

```text
<output folder>/
├── sub-M4/
│   ├── sub-M4_ses-day-1-lone.nwb
│   └── ...
├── nwb_stub/                 stub files
├── exceptions/               one file per failed session
├── inspector_reports/
└── inspection_summary.csv
```

## Converting from Python

```python
from pathlib import Path

from uchida_lab_to_nwb.phillips_2025.convert_all_sessions import dataset_to_nwb
from uchida_lab_to_nwb.phillips_2025.convert_session import session_to_nwb
from uchida_lab_to_nwb.phillips_2025.inspection import inspect_output_folder
from uchida_lab_to_nwb.phillips_2025.utils.subject_metadata import get_subject_metadata

data_share_path = Path("<data share>")
output_dir_path = Path("<output folder>")

# One session
session_to_nwb(
    session_dir_path=data_share_path / "Hannah_data" / "M4-M7" / "Social_data" / "day_1" / "M4",
    output_dir_path=output_dir_path,
    subject_metadata=get_subject_metadata("M4", data_share_path / "Subject metadata.xlsx"),
    stub_test=True,
)

# All sessions of one condition, then the inspection
dataset_to_nwb(
    data_dir_path=data_share_path / "Hannah_data" / "M4-M7" / "Lone_data",
    output_dir_path=output_dir_path,
    subject_metadata_path=data_share_path / "Subject metadata.xlsx",
    max_workers=1,
)
summary = inspect_output_folder(output_dir_path)
```

`get_session_to_nwb_kwargs_per_session` in `convert_all_sessions.py` returns the arguments of every session of a
condition folder, as `dataset_to_nwb` uses them.
