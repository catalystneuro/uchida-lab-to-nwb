# The conversion pipeline

This page explains how a conversion in this repository turns a lab's recordings into NWB files and shares them on
DANDI. Each conversion project has its own documentation next to its code; for the Phillips 2025 dataset, see
[phillips_2025/docs](../src/uchida_lab_to_nwb/phillips_2025/docs/).

## NWB and NeuroConv

[NWB](https://nwb-overview.readthedocs.io/) (Neurodata Without Borders) is a standard file format for neurophysiology
data. One NWB file holds the data of a session together with its metadata: subject, devices, surgery, and the
meaning and units of each signal. Files that follow the standard can be read by the same tools and shared on
[DANDI](https://dandiarchive.org), the archive for NWB data.

The conversions are built on [NeuroConv](https://neuroconv.readthedocs.io/), which reads acquisition formats and
writes them to NWB, and on NWB extensions for the data types the core standard does not cover (here
ndx-fiber-photometry, ndx-ophys-devices, ndx-pose and ndx-hed).

## Parts of a conversion

A conversion project is a folder under `src/uchida_lab_to_nwb/`, named after the first author and year of the
dataset it converts:

| Part | Role |
| --- | --- |
| data interfaces (`interfaces/`) | Each reads one data stream (for example the pCampi sync file, or the lab's resampled photometry) and adds it to an NWB file. NeuroConv provides interfaces for common formats (here Doric fiber photometry and DANNCE pose with video); the project adds its own for lab-specific files. |
| converter (`nwbconverter.py`) | Combines the interfaces of a session into one file and puts their times on one clock. |
| metadata files (`*.yaml`) | YAML files with the metadata that is not in the data files, such as devices, indicators, implant coordinates, tasks and ontology terms. |
| session conversion (`convert_session.py`) | Finds the files of one session, builds its metadata and runs the converter. |
| batch conversion (`convert_all_sessions.py`) | Lists every session of a data folder and converts them. |
| inspection and staging (`inspection.py`, `upload_to_DANDI.py`) | NWB Inspector reports after converting, and the upload to DANDI. |
| `docs/` and `notebooks/` | How to run the conversion, and a notebook that reads the files. |

## From recordings to DANDI

A conversion runs in these steps:

1. Convert: write one NWB file per session. Converting one session with `stub_test=True` first writes a small file
   that is quick to check.
2. Inspect: run [NWB Inspector](https://nwbinspector.readthedocs.io/) on each file, which checks it against the
   standard and its best practices.
3. Review: look at the files and the inspection summary, and fix the metadata or the code where needed.
4. Stage: organize the files as DANDI expects, validate them, and upload them to the draft of the dandiset.
   Publishing a version freezes the draft and gives it a DOI.

## Keeping a conversion correct

- Metadata lives in YAML files, so that it can be corrected and reviewed without changing code.
- NWB Inspector runs after converting and DANDI validation before uploading, so that problems in the files are found
  before they are shared.
- Ontology terms (species, strain, brain regions, skeleton landmarks, experimenter, institution) are written into the
  files, so that the values can be found by their standard identifiers.

To convert a new experiment, see [Building a new conversion pipeline](new_conversion_pipeline.md).
