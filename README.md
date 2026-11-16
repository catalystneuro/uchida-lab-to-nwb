# uchida-lab-to-nwb

NWB conversion of [Uchida Lab](https://projects.iq.harvard.edu/uchidalab) data, built on
[NeuroConv](https://github.com/catalystneuro/neuroconv).

- Project: SFARI Autism Rat Models Consortium (ARC)
- Study: social behavior and observational fear learning in autism rat models
- PI: Prof. Naoshige Uchida, Harvard University
- Dandiset: [DANDI:001935](https://dandiarchive.org/dandiset/001935) (embargoed)

Each conversion lives in its own folder under `src/uchida_lab_to_nwb/`. There is one so far,
`phillips_2025`.

## Dataset (phillips_2025)

12 sessions: subjects M4, M5 and M7, 2 days each, in two conditions. In the lone condition the
implanted rat is alone in the arena; in the social condition a partner rat is with it. Each session
becomes one NWB file, `sub-<subject>/sub-<subject>_ses-day-<N>-<lone|social>.nwb`.

Data streams:

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

The lab-computed dF/F (`processed_dff.mat`) is not converted; its interface is ready but disabled.
[conversion_notes.md](src/uchida_lab_to_nwb/phillips_2025/documentation/conversion_notes.md)
describes how each stream maps to NWB, how the streams are aligned in time, and the known
limitations.

## Installation

```bash
git clone https://github.com/catalystneuro/uchida-lab-to-nwb
cd uchida-lab-to-nwb
conda env create -f make_env.yml
conda activate uchida-lab-to-nwb-env
```

Or, in an existing Python 3.11 or 3.12 environment, `pip install -e .`

NeuroConv is installed from its `main` branch, which holds the HERD and DANNCE features this
conversion needs and which are not released yet.

## Running the conversion

Each script has an `if __name__ == "__main__":` block at the bottom with placeholder paths
(`/path/to/Uchida-CN-data-share`, `/path/to/nwbfiles`). Set them to your copy of the data share and
to an output folder, then run the file. Keep the output folder on the same drive as the data share:
the NWB files link the videos by a path relative to the file, which is not possible across drives.

1. Convert: `convert_all_sessions.py` converts every session of `Lone_data` and `Social_data`.
   `convert_session.py` converts one session; set `stub_test=True` for a quick small file.
2. Inspect: `inspection.py` runs NWB Inspector (DANDI configuration) on every converted file. It
   writes one report per file to `inspector_reports/` and a table, `inspection_summary.csv`, to the
   output folder.
3. Upload: `upload_to_DANDI.py` copies the files into a local dandiset folder organized as DANDI
   expects, prints how they compare with the files already on the draft, and uploads them once
   `upload = True` is set. It needs a DANDI API key in the `DANDI_API_KEY` environment variable.
   Use `dandi_instance = "dandi-sandbox"` to try an upload on the sandbox first.

The same steps from Python:

```python
from uchida_lab_to_nwb.phillips_2025.convert_all_sessions import dataset_to_nwb
from uchida_lab_to_nwb.phillips_2025.inspection import inspect_output_folder

dataset_to_nwb(
    data_dir_path="/path/to/Uchida-CN-data-share/Hannah_data/M4-M7/Lone_data",
    output_dir_path="/path/to/nwbfiles",
    subject_metadata_path="/path/to/Uchida-CN-data-share/Subject metadata.xlsx",
    max_workers=1,
)
inspect_output_folder("/path/to/nwbfiles")
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
    │   └── subject_metadata.py                      # Subject metadata and fiber hemispheres
    ├── nwbconverter.py                              # Converter class and temporal alignment
    ├── convert_session.py                           # Converts one session
    ├── convert_all_sessions.py                      # Converts all sessions of a condition
    ├── inspection.py                                # NWB Inspector on the converted files
    ├── upload_to_DANDI.py                           # Organize and upload to DANDI
    ├── general_metadata.yaml                        # Lab, experiment, task, HED and ontology metadata
    ├── fiber_photometry.yaml                        # Fiber photometry hardware metadata
    └── documentation/
        └── conversion_notes.md                      # Data mapping, alignment, known limitations
notebooks/
├── dandi_001935_tutorial.ipynb                      # Example notebook
└── environment.yml
```

Raw Doric fiber photometry (`DoricFiberPhotometryInterface`) and DANNCE pose with the multi-camera
video (`DANNCEConverter`, `DANNCEInterface`) come from NeuroConv. The other interfaces are in
`interfaces/`.

## Extending the phillips_2025 conversion

How the pieces fit together: `session_to_nwb()` in `convert_session.py` finds the files of one
session directory, builds `source_data` (one entry per interface slot) and the metadata, and runs
`Phillips2025NWBConverter` (`nwbconverter.py`). The converter lists its interface slots in
`data_interface_classes` and aligns all streams to the pCampi clock in
`temporally_align_data_interfaces()`. Static metadata is in the two YAML files.

Add sessions or subjects:

- Put each session in the same layout, `<Condition>_data/day_<N>/M<id>/`, with the same file names.
  `convert_all_sessions.py` finds every `day_*/M*/` folder that has a `.h5` and a `.doric` file.
- Add each new subject to `Subject metadata.xlsx`, and its fiber implant hemispheres to
  `_SUBJECT_FIBER_HEMISPHERES` in `utils/subject_metadata.py`. A subject missing from the sheet is
  skipped with a warning; one missing from the hemispheres fails, with the error written to
  `exceptions/` in the output folder.

Add a behavioral condition (a new `<Name>_data` folder):

- Add a task under `Tasks` in `general_metadata.yaml`, keyed by the lower-case condition name
  (`<name>`), and a HED definition for it under `HED`.
- In `session_to_nwb()`, set where the condition's DANNCE file is (`dannce_mat`; lone sessions use
  `DANNCE/`, every other condition `sDANNCE/predict05/`), and whether a partner is tracked (the
  `if condition == "social"` block).

Change metadata: edit `general_metadata.yaml` (experiment, experimenters, keywords, tasks, HED,
ontology terms) or `fiber_photometry.yaml` (hardware, indicators, response series). Values that
change per session or subject are set in `session_to_nwb()`.

Add a data stream:

1. Look for an interface in NeuroConv first
   ([supported formats](https://neuroconv.readthedocs.io/en/main/conversion_examples_gallery/index.html)).
   If there is none, write one in `interfaces/` and export it from `interfaces/__init__.py`. Subclass
   NeuroConv's `BaseDataInterface`, or a base class for the data type such as
   `BaseFiberPhotometryInterface`; the interfaces in `interfaces/` are examples of both.
2. Register a slot for it in `data_interface_classes` in `nwbconverter.py`.
3. In `session_to_nwb()`, add its entry to `source_data` and `conversion_options`, only when its
   files exist.
4. Add its metadata to a YAML file, or a new YAML file merged in `session_to_nwb()` like
   `fiber_photometry.yaml`.
5. If it is not recorded on the pCampi clock, align it in `temporally_align_data_interfaces()`.
6. Convert a stub (`stub_test=True`), open the file, then run `inspection.py` on full files.

Enable the lab dF/F: uncomment the three "DffDopamineSignal" blocks in `convert_session.py` and the
`fiber_photometry_dff_dopamine_signal` block at the end of `fiber_photometry.yaml` (see
conversion_notes.md, Not converted).

## Starting a new conversion

For a new dataset (another paper or experiment), add a new folder next to `phillips_2025`, named
`<first author last name>_<year>`, with the same layout:

1. Copy `phillips_2025/` and rename it. Rename the converter class (`Phillips2025NWBConverter`) and
   the imports of `uchida_lab_to_nwb.phillips_2025`.
2. In `nwbconverter.py`, keep the slots for the streams the new dataset has and delete the rest.
   Delete or rewrite `temporally_align_data_interfaces()` for the new synchronization setup.
3. Rewrite `session_to_nwb()` for the new folder layout and session naming, and
   `convert_all_sessions.py` for how sessions are found.
4. Replace the metadata in the YAML files and the subject metadata reader.
5. Convert one stub session, check it with NWB Inspector and in
   [Neurosift](https://neurosift.app), then convert the full dataset.
6. Write an example notebook that loads a file and shows each stream, like
   `notebooks/dandi_001935_tutorial.ipynb`.

Useful references: the [NeuroConv documentation](https://neuroconv.readthedocs.io), the
[NWB documentation](https://nwb.org/), and the
[DANDI documentation](https://docs.dandiarchive.org) for creating a Dandiset and uploading.
