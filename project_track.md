# Uchida Lab to NWB — Project Tracker

**Lab**: Uchida Lab, Harvard University (PI: Prof. Naoshige Uchida)
**Point person**: Hannah Phillips
**Dataset**: SFARI ARC — Lone condition (M4, M5, M7 × 2 days = 6 sessions)
**Repo**: https://github.com/catalystneuro/uchida-lab-to-nwb

---

## Pre-Conversion
- [x] Repo scaffolded
- [x] Data inspection complete (`conversion_notes.md`)
- [x] Metadata YAML drafted (`phillips_2025_metadata.yaml`, `subject_metadata.yaml`, `fiber_photometry.yaml`)
- [x] Metadata request sent to lab (`hannah_metadata_request.md`)
- [ ] Paper fetched and methods reviewed (manuscript not yet available)

---

## Conversion

### Fiber Photometry — Raw (Doric BBC300)
- [x] Interface implemented — uses `DoricFiberPhotometryInterface` imported from neuroconv (PR #2 on `reviews_part_1`)
- [ ] Tests pass — no test suite yet
- [ ] nwbinspector: zero CRITICAL

### Fiber Photometry — Processed (dF/F from MATLAB)
- [x] Interface implemented — `DoricProcessedPhotometryInterface` in [src/uchida_lab_to_nwb/phillips_2025/interfaces/doric_processed_photometry_interface.py](src/uchida_lab_to_nwb/phillips_2025/interfaces/doric_processed_photometry_interface.py) — PR #2 on `reviews_part_1`
- [ ] Tests pass — no test suite yet
- [ ] nwbinspector: zero CRITICAL

### Behavior — DANNCE 3D Pose Estimation
- [x] Interface implemented — uses `SDANNCEInterface` imported from neuroconv (imported from `add-dannce-interface` branch, pending merge to neuroconv main)
- [ ] Tests pass — no test suite yet
- [ ] nwbinspector: zero CRITICAL

### Behavior — Multi-Camera Video (6 cameras, H.264 MP4)
- [x] Interface implemented — uses `ExternalVideoInterface` × 6 in `Phillips2025NWBConverter`
- [ ] Tests pass — no test suite yet

### Sync — pCampi TTL (LabVIEW / NIDAQ)
- [x] Interface implemented — `PCampiSyncInterface` in [src/uchida_lab_to_nwb/phillips_2025/interfaces/pcampi_sync_interface.py](src/uchida_lab_to_nwb/phillips_2025/interfaces/pcampi_sync_interface.py) — PR #2 on `reviews_part_1`
- [ ] Tests pass — no test suite yet

### Temporal Synchronization
- [x] Sync plan documented in `conversion_notes.md` (pCampi 1 kHz NIDAQ as NWB reference clock; rising-edge alignment for Doric and video)
- [x] `temporally_align_data_interfaces()` implemented in [src/uchida_lab_to_nwb/phillips_2025/phillips_2025_nwbconverter.py](src/uchida_lab_to_nwb/phillips_2025/phillips_2025_nwbconverter.py) — PR #2 on `reviews_part_1`

---

## Post-Conversion
- [x] Local example notebook (`notebooks/phillips_2025_demo.ipynb`) — PR #2 on `reviews_part_1`
- [ ] DANDI upload complete — Dandiset ID: `XXXXXX` (embargo mode planned)
- [ ] Example notebook PR submitted to `dandi/example-notebooks`

---

## Metadata Status
- [x] `hannah_metadata_request.md` sent to lab
- [ ] Subject metadata resolved (species ✓, sex TBD, strain TBD, DOB TBD, weight TBD, experimental group TBD)
- [ ] Fiber photometry hardware resolved (LED wavelengths TBD, fiber implant coordinates TBD, brain regions TBD, indicator identity TBD)
- [ ] pCampi channel assignment confirmed (campy_trigger vs. rbfmc_frames)
- [ ] Processed photometry variable legend confirmed (rawG, rawGR, rawR, rawTd meanings)
- [ ] DANDI upload metadata resolved (ORCIDs, funding, license, related publication DOI)
- [ ] `fiber_photometry.yaml` updated with real values (currently all coordinates/wavelengths/regions marked TODO)
- [ ] `subject_metadata.yaml` updated with real values (currently all fields TBD)

---

## Open Dependencies
- [ ] `SDANNCEInterface` merged to neuroconv main (`add-dannce-interface` branch pending) — required to pin neuroconv release in `pyproject.toml`
- [ ] Write test suite (no tests exist yet)
