# uchida-lab-to-nwb

Conversion of the Uchida Lab's fiber photometry and behavior recordings to the
[Neurodata Without Borders](https://nwb-overview.readthedocs.io/) (NWB) format, built on
[NeuroConv](https://neuroconv.readthedocs.io/).

The `phillips_2025` conversion covers recordings from the SFARI Autism Rat Models Consortium (ARC) project on social
behavior and observational fear learning in autism rat models (Uchida Lab, Harvard University). Rats behave freely in
an arena, alone (lone condition) or with a partner rat (social condition), while dopamine is recorded by fiber photometry
in the nucleus accumbens and the tail of the striatum. Each NWB file holds one session: the raw and processed
photometry, the 3D pose of the rat (and of the partner in social sessions) with the 6 camera videos, the sync pulses,
the session's task and epoch, and the subject and device metadata. The files are shared in
[DANDI:001935](https://dandiarchive.org/dandiset/001935) (embargoed).

## Installation

Install [git](https://github.com/git-guides/install-git) and [conda](https://docs.conda.io/en/latest/miniconda.html),
then, from a terminal:

```bash
git clone https://github.com/catalystneuro/uchida-lab-to-nwb
cd uchida-lab-to-nwb
conda env create --file make_env.yml
conda activate uchida-lab-to-nwb-env
```

This creates a conda environment with the package installed in editable mode, so that changes to the code and
metadata files apply without installing again. Without conda, use Python 3.11 or 3.12 and run `pip install --editable .`
in the cloned folder.

NeuroConv is installed from its `main` branch, which holds the HERD and DANNCE features this conversion needs and
which are not released yet.

## Quick start

Set the data share and output folder paths in the `if __name__ == "__main__":` block of each script, then:

```bash
python src/uchida_lab_to_nwb/phillips_2025/convert_all_sessions.py
python src/uchida_lab_to_nwb/phillips_2025/inspection.py
```

The first writes one NWB file per session to the output folder; the second inspects them with NWB Inspector. See
[Converting sessions](src/uchida_lab_to_nwb/phillips_2025/docs/converting_sessions.md).

## Documentation

The conversion pipeline in general, in [docs/](docs/):

- [The conversion pipeline](docs/conversion_pipeline.md): NWB, NeuroConv, the parts of a conversion and the steps from
  recordings to DANDI.
- [Building a new conversion pipeline](docs/new_conversion_pipeline.md): converting another experiment to NWB.

The Phillips 2025 conversion, in [phillips_2025/docs/](src/uchida_lab_to_nwb/phillips_2025/docs/):

- [Data organization](src/uchida_lab_to_nwb/phillips_2025/docs/data_organization.md): the data share layout, conditions, subjects and lab files.
- [Converting sessions](src/uchida_lab_to_nwb/phillips_2025/docs/converting_sessions.md): converting sessions, and the output files.
- [Data streams](src/uchida_lab_to_nwb/phillips_2025/docs/data_streams.md): raw and processed signals, pose and video, and how their times are aligned.
- [Metadata](src/uchida_lab_to_nwb/phillips_2025/docs/metadata.md): editing the metadata files, adding a subject or a condition, ontology terms.
- [NWB file structure](src/uchida_lab_to_nwb/phillips_2025/docs/nwb_file_structure.md): what is stored where, and how to read a file.
- [Spyglass ingestion](src/uchida_lab_to_nwb/phillips_2025/docs/spyglass_ingestion.md)
- [DANDI staging](src/uchida_lab_to_nwb/phillips_2025/docs/dandi_staging.md): organizing, validating and uploading the files.
- [Troubleshooting](src/uchida_lab_to_nwb/phillips_2025/docs/troubleshooting.md): conversion errors and known issues.

The notebook [notebooks/dandi_001935_tutorial.ipynb](notebooks/dandi_001935_tutorial.ipynb) reads a session from
DANDI or from disk and shows each data stream (see [notebooks/README.md](notebooks/README.md)).

## Repository layout

```text
src/uchida_lab_to_nwb/phillips_2025/
├── convert_session.py        conversion of one session
├── convert_all_sessions.py   conversion of all sessions
├── nwbconverter.py           NWBConverter of the dataset and time alignment
├── interfaces/               data interfaces (pCampi sync, processed photometry, dF/F, task and epoch)
├── utils/                    subject metadata and the rat23 skeleton
├── inspection.py             NWB Inspector reports and inspection summary
├── upload_to_DANDI.py        organizing and uploading to DANDI
├── general_metadata.yaml     experiment, tasks, HED and ontology terms
├── fiber_photometry.yaml     fiber photometry devices, indicators and series
└── docs/                     documentation of this conversion
docs/                         documentation of the conversion pipeline in general
notebooks/                    example notebook
```

## Citation

If you use these files, please cite [NeuroConv](https://github.com/catalystneuro/neuroconv) and
[NWB](https://www.nwb.org/) for the conversion.

## License

See [LICENSE](LICENSE).
