# Metadata

The metadata of the NWB files that is not in the data files (experiment description, experimenter, devices,
indicators, implant coordinates, tasks, ontology terms) is kept in YAML files in
`src/uchida_lab_to_nwb/phillips_2025/`, so that it can be corrected without changing code. After editing a file,
convert the sessions again (see [Converting sessions](converting_sessions.md)).

## Files

| File | Content |
| --- | --- |
| `general_metadata.yaml` | experiment description, institution, lab, experimenter, keywords; the task of each condition (`Tasks`); the HED schema and definitions (`HED`); ontology terms (`ExternalResources`) |
| `fiber_photometry.yaml` | LED, photodetector and optical fiber models and devices, implant coordinates, indicators, the fiber photometry table and the name, description and unit of each photometry series |
| `utils/subject_metadata.py` | reads `Subject metadata.xlsx`; holds the fiber implant hemisphere of each subject (`_SUBJECT_FIBER_HEMISPHERES`) |
| `utils/constants.py` | the 23 rat23 landmark names and skeleton edges |

## How a session's metadata is built

For each session, `session_to_nwb` merges, in this order:

1. The metadata of the interfaces: the session start time from the pCampi file name (in America/New_York), and the
   defaults of the photometry and DANNCE interfaces.
2. `general_metadata.yaml`, then `fiber_photometry.yaml`.
3. The fiber implant hemisphere of the subject: `hemisphere` and the sign of the ML coordinate of
   `optical_fiber_NAc` and `optical_fiber_TS` (positive for right, negative for left).
4. Values set by the code: session ID and description, the subject fields from the sheet, the skeleton, and the
   descriptions of the pose containers and cameras.

## Editing the metadata

Find the value in the YAML file and change it.

- `fiber_photometry.yaml` uses functional names for its keys: `control` (EXC1, 568 nm, tdTomato) and
  `dopamine_signal` (EXC2, 473 nm, GRABDA3m); `NAc` (ROI01) and `TS` (ROI02). Each series lists its rows of the
  fiber photometry table in `fiber_photometry_table_region`, in the order of its columns (NAc, then TS).
- The fiber hemisphere in `fiber_photometry.yaml` is a placeholder (`unknown`, ML coordinate without sign); the real
  one comes from `_SUBJECT_FIBER_HEMISPHERES`.
- `related_publications` in `general_metadata.yaml` is commented out until there is a publication.

## Adding a subject

1. Add a column for the subject to `Subject metadata.xlsx`, with the same row labels.
2. Add its fiber hemispheres to `_SUBJECT_FIBER_HEMISPHERES` in `utils/subject_metadata.py`:

   ```python
   "M8": {"NAc": "left", "TS": "right"},
   ```

3. If its strain is new, add it under `ExternalResources: strain` in `general_metadata.yaml`.
4. Convert one of its sessions with `stub_test=True`.

## Tasks and HED

Each condition has a task under `Tasks` in `general_metadata.yaml`, keyed by the condition name (the folder name
without `_data`, in lower case), with `task_name`, `task_description`, `task_environment` and `hed`. `hed` refers to a
definition under `HED: definitions`, written in [HED](https://www.hedtags.org/) (Hierarchical Event Descriptors) with
schema 8.5.0. The implanted rat is the `Experiment-participant`; in the social condition the partner is an
`Experiment-actor`.

To add a condition, for example a `Fear_data` folder:

1. Add a `fear` task under `Tasks`, and a `Definition/Fear-condition` under `HED: definitions` that its `hed` refers
   to as `Def/Fear-condition`.
2. In `session_to_nwb`, check where the condition's pose file is (`dannce_mat`: lone sessions use `DANNCE/`, every
   other condition `sDANNCE/predict05/`) and whether a partner is tracked (the `if condition == "social"` block).
3. Convert one session as a stub and validate the HED annotation of its task with ndx-hed, as the
   [example notebook](../../../../notebooks/dandi_001935_tutorial.ipynb) does:

   ```python
   from ndx_hed.utils.hed_nwb_validator import HedNWBValidator
   from pynwb import NWBHDF5IO

   with NWBHDF5IO("<stub file>.nwb", "r") as io:
       nwbfile = io.read()
       validator = HedNWBValidator(nwbfile.lab_meta_data["hed_schema"])
       issues = validator.validate_vector(nwbfile.processing["tasks"]["task_table"]["HED"])
   ```

   An empty `issues` list means the annotation is valid.

## Ontology terms

`ExternalResources` in `general_metadata.yaml` maps values of the files to ontology terms, which NeuroConv writes into
each NWB file as HERD references (the `herd_references` column of the inspection summary counts them). Each map is
keyed by the exact string it annotates; a term for a value that a session does not have (for example the skeleton
nodes of a session without pose data) is skipped.

| Map | NWB field | Value | Term |
| --- | --- | --- | --- |
| `species` | `Subject.species` | `Rattus norvegicus` | NCBITaxon:10116 |
| `strain` | `Subject.strain` | `Long Evans` | RRID:RGD_2308852 (Crl:LE) |
| `experimenter` | `NWBFile.experimenter` | `Phillips, Hannah` | ORCID iD |
| `institution` | `NWBFile.institution` | `Harvard University` | ror:03vek6s52 |
| `anatomical_structures` | `FiberPhotometryTable.location` | `Nucleus Accumbens` | UBERON:0001882 |
| `anatomical_structures` | `FiberPhotometryTable.location` | `Tail of Striatum` | UBERON:0002435 (striatum) |
| `anatomical_structures` | `Skeleton.nodes` | 23 rat23 landmarks | UBERON |

- Strain: the subject sheet records no supplier; the term is the Long-Evans RRID of NeuroConv's strain table (Charles
  River Crl:LE).
- Tail of Striatum has no term in UBERON or the Allen Mouse Brain Atlas, so it is mapped to striatum.
- Skeleton: UBERON has no left and right terms, so both sides of a paired landmark share one term, written once with
  a YAML anchor. The three spine points map to the vertebral column and `TailBase` to the tail.

A new location string, landmark or experimenter needs an entry with exactly the same spelling. Look up terms in the
[EBI Ontology Lookup Service](https://www.ebi.ac.uk/ols4) (UBERON, NCBITaxon), [SciCrunch](https://scicrunch.org/)
(RRID), [ORCID](https://orcid.org) and [ROR](https://ror.org).
