# Uchida Lab to NWB — Project Tracker

**Lab**: Uchida Lab, Harvard University (PI: Prof. Naoshige Uchida)
**Point person**: Hannah Phillips
**Dataset**: SFARI ARC, subjects M4, M5, M7 × 2 days × Lone and Social conditions = 12 sessions
**Repo**: <https://github.com/catalystneuro/uchida-lab-to-nwb>
**Last updated**: 2026-11-03

---

## Pre-Conversion

- [x] Repo scaffolded
- [x] Data inspection complete (`conversion_notes.md`)
- [x] Metadata YAML drafted (`general_metadata.yaml`, `fiber_photometry.yaml`); per-subject metadata read from `Subject metadata.xlsx`
- [x] Metadata request sent to lab, reply received from Hannah (2026-05-06)
- [x] Midway review meeting with the lab (2026-09-15)
- [ ] Paper fetched and methods reviewed: no manuscript yet

---

## Conversion

### Fiber Photometry — Raw (Doric BBC300)

- [x] Interface: `DoricFiberPhotometryInterface` from neuroconv, one instance per excitation channel
- [x] `fiber_photometry.yaml` filled with confirmed values (wavelengths, brain regions, indicators, coordinates, per-subject implant hemisphere)
- [ ] **ROI03**: the Doric file has 3 ROIs per excitation, but Hannah reports only 2 implants (NAc + TS). ROI03 is not converted; its purpose is still unknown
- [ ] Tests

### Fiber Photometry — Interpolated Raw (MATLAB)

- [x] Interface: `ProcessedFiberPhotometryInterface` in [interfaces/processed_fiber_photometry_interface.py](../interfaces/processed_fiber_photometry_interface.py)
- [x] Real per-sample timestamps from Doric trigger pulses (9 of 12 sessions); nominal camera-rate fallback for the other 3
- [ ] Tests

### Fiber Photometry — dF/F (`processed_dff.mat`)

- [x] Interface `DffFiberPhotometryInterface` ready but disabled, as agreed at the 2026-09-15 midway meeting, until the lab confirms what `dff_resG`/`dff_resG2` represent

### Behavior — DANNCE 3D Pose Estimation + Multi-Camera Video

- [x] `DANNCEConverter` from neuroconv main: pose, 6 external videos, calibrated camera devices
- [x] Lone sessions: `pred` shape `(90000, 1, 3, 23)`, `animal_index=0`
- [x] **Social sessions**: `pred` shape `(90000, 2, 3, 23)`. Index 0 = implanted subject, index 1 = partner (confirmed by Hannah from pose overlays, 2026-11-03). One file per session; the partner's pose is a second container (`PoseEstimationDANNCEPartner`, slot `DANNCEPartner`) sharing the subject's videos and cameras, treated as an external stimulus with no subject metadata
- [ ] Social day_1/M7: calibration only for Camera3, 5, 6 (no `calibration.json`); the other 3 are written as uncalibrated devices. Ask the lab whether the files exist
- [x] Skeleton edges and HERD terms for the 23 rat23 nodes
- [ ] Per-camera `PoseEstimation` descriptions: set in metadata, not yet written by neuroconv (upstream fix needed)
- [ ] Tests

### Sync — pCampi TTL (LabVIEW / NIDAQ)

- [x] Interface: `PCampiSyncInterface` in [interfaces/pcampi_sync_interface.py](../interfaces/pcampi_sync_interface.py)
- [x] Channels confirmed by Hannah: Ch0 = `campy_trigger`, Ch1 = `rbfmc_frames` (all zero, skipped)
- [ ] Tests

### Temporal Synchronization

- [x] `temporally_align_data_interfaces()` in [nwbconverter.py](../nwbconverter.py): pCampi `campy_trigger` matched against Doric `DigitalCh1` for a single offset
- [ ] Frame-count mismatch (about 74 more `campy_trigger` pulses than saved frames, in every session): not blocking, unaddressed

### Metadata and Ontologies

- [x] HERD: species, strain, experimenter (ORCID), institution (ROR), anatomical structures (<https://github.com/catalystneuro/uchida-lab-to-nwb/pull/6>)
- [ ] HED table

---

## Post-Conversion

- [x] Example notebook: [notebooks/dandi_001935_tutorial.ipynb](../../../../notebooks/dandi_001935_tutorial.ipynb)
- [ ] Re-convert all 12 sessions with the current code (files in `H:/uchida-nwbfiles` date from August and September 2026)
- [ ] NWB Inspector on the full files: zero CRITICAL
- [ ] DANDI upload to Dandiset 001935 (embargo mode planned)
- [ ] Example notebook PR submitted to `dandi/example-notebooks`

---

## Metadata Status

- [x] pCampi channel assignment confirmed
- [x] Fiber photometry hardware confirmed: EXC1 = 568 nm (tdTomato), EXC2 = 473 nm (GRABDA3m), 50 µW each, BBC300 at 0 dB gain
- [x] Fiber implant coordinates confirmed: ROI01 = NAc (AP±1.15, ML±2.2, DV−6.3), ROI02 = TS (AP±3.15, ML±5.2, DV−4.5)
- [x] Indicators confirmed: GRABDA3m (AAV9-hSyn-DA3m, WZ Biosciences) + tdTomato (AAV5-CAG-tdTomato, Addgene), co-injected
- [x] Dataset scope confirmed: M4, M5, M7 only
- [x] Subject metadata (sex, DOB, weight, strain, genotype) read from `Subject metadata.xlsx`
- [x] Experimenter ORCID confirmed
- [x] Social partner rat: treated as an external stimulus, no subject metadata (decided 2026-11-03)
- [ ] SFARI grant number + license (CC-BY-4.0): ask Nao Uchida
- [ ] DANDI contributors and publication DOI: defer to manuscript stage

---

## Open Dependencies

- [ ] neuroconv release including the HERD and DANNCE changes, to replace the pin to `main` in `pyproject.toml`
- [ ] neuroconv fix forwarding per-camera `PoseEstimation` metadata (description, etc.)
- [ ] Lab answer on ROI03
- [ ] Test suite (none yet)
