# Uchida Lab to NWB — Project Tracker

**Lab**: Uchida Lab, Harvard University (PI: Prof. Naoshige Uchida)
**Point person**: Hannah Phillips
**Dataset**: SFARI ARC — Lone condition (M4, M5, M7 × 2 days = 6 sessions)
**Repo**: <https://github.com/catalystneuro/uchida-lab-to-nwb>

---

## Pre-Conversion

- [x] Repo scaffolded
- [x] Data inspection complete (`conversion_notes.md`)
- [x] Metadata YAML drafted (`phillips_2025_metadata.yaml`, `subject_metadata.yaml`, `fiber_photometry.yaml`)
- [x] Metadata request sent to lab (`hannah_metadata_request.md`)
- [x] Reply received from Hannah (2026-05-06) — most hardware metadata resolved
- [ ] Paper fetched and methods reviewed — no manuscript yet

---

## Conversion

### Fiber Photometry — Raw (Doric BBC300)

- [x] Interface implemented — uses `DoricFiberPhotometryInterface` from neuroconv (PR #2 on `reviews_part_1`)
- [ ] `fiber_photometry.yaml` updated with confirmed values (wavelengths, brain regions, indicator, coordinates)
- [ ] **Investigate ROI03**: Doric file has 3 ROIs per excitation but Hannah reports only 2 implants (NAc + TS)
- [ ] Tests pass — no test suite yet
- [ ] nwbinspector: zero CRITICAL

### Fiber Photometry — Interpolated Raw (MATLAB)

- [x] Interface implemented — `DoricProcessedPhotometryInterface` in [src/uchida_lab_to_nwb/phillips_2025/interfaces/doric_processed_photometry_interface.py](src/uchida_lab_to_nwb/phillips_2025/interfaces/doric_processed_photometry_interface.py)
- [ ] **Interface needs revision**: current `.mat` files contain old test artifacts (dF/F, baselines, etc.); Hannah will replace with clean interpolated-only files — update interface once received
- [ ] Tests pass — no test suite yet
- [ ] nwbinspector: zero CRITICAL

### Behavior — DANNCE 3D Pose Estimation

- [x] Interface implemented — uses `SDANNCEInterface` from neuroconv (`add-dannce-interface` branch, pending merge)
- [x] Lone session array shape confirmed: 90000 × 1 × 3 × 23 (`animal_index=0` correct)
- [ ] Social session support: array will be 90000 × 2 × 3 × 23 — both animals to be written
- [ ] Tests pass — no test suite yet
- [ ] nwbinspector: zero CRITICAL

### Behavior — Multi-Camera Video (6 cameras, H.264 MP4)

- [x] Interface implemented — uses `ExternalVideoInterface` × 6 in `Phillips2025NWBConverter`
- [ ] Tests pass — no test suite yet

### Sync — pCampi TTL (LabVIEW / NIDAQ)

- [x] Interface implemented — `PCampiSyncInterface` in [src/uchida_lab_to_nwb/phillips_2025/interfaces/pcampi_sync_interface.py](src/uchida_lab_to_nwb/phillips_2025/interfaces/pcampi_sync_interface.py)
- [x] Channel assignment confirmed by Hannah: Ch0 = campy_trigger, Ch1 = rbfmc_frames
- [ ] Tests pass — no test suite yet

### Temporal Synchronization

- [x] Sync plan documented in `conversion_notes.md`
- [x] `temporally_align_data_interfaces()` implemented in [src/uchida_lab_to_nwb/phillips_2025/phillips_2025_nwbconverter.py](src/uchida_lab_to_nwb/phillips_2025/phillips_2025_nwbconverter.py)

---

## Post-Conversion

- [x] Local example notebook (`notebooks/phillips_2025_demo.ipynb`)
- [ ] DANDI upload complete — Dandiset ID: `XXXXXX` (embargo mode planned)
- [ ] Example notebook PR submitted to `dandi/example-notebooks`

---

## Metadata Status

- [x] `hannah_metadata_request.md` sent to lab
- [x] Reply received 2026-05-06
- [x] pCampi channel assignment confirmed ✓
- [x] Fiber photometry hardware confirmed: EXC1=568 nm (tdTomato), EXC2=473 nm (GRABDA3m), 50 µW each, BBC300 at 0 dB gain
- [x] Fiber implant coordinates confirmed: ROI01=NAc (AP±1.15, ML±2.2, DV−6.3), ROI02=TS (AP±3.15, ML±5.2, DV−4.5)
- [x] Indicator identity confirmed: GRABDA3m (AAV9-hSyn-DA3m, WZ Biosciences) + tdTomato (AAV5-CAG-tdTomato, Addgene), co-injected
- [x] DANNCE array shapes confirmed: Lone=90000×1×3×23, Social=90000×2×3×23
- [x] Dataset scope confirmed: M4, M5, M7 only (M1–M3, M6 not in this dataset)
- [ ] Subject metadata (sex, DOB, weight, strain, surgery dates) — from attached `Subject metadata.xlsx`, not yet imported
- [ ] `subject_metadata.yaml` updated with real values
- [ ] `fiber_photometry.yaml` updated with confirmed values
- [ ] DANDI ORCIDs / contributors — defer to manuscript stage
- [ ] SFARI grant number + license (CC-BY-4.0) — ask Nao Uchida
- [ ] Publication DOI — no manuscript yet

---

## Open Dependencies

- [ ] `SDANNCEInterface` merged to neuroconv main (`add-dannce-interface` branch pending) — required to pin neuroconv release in `pyproject.toml`
- [ ] Clean `interpolated_campy_and_doric_data.mat` files from Hannah (old versions have test artifacts)
- [ ] Social data upload from Hannah (planned week of 2026-05-06)
- [ ] Clarification on ROI03 in Doric file (Hannah only has 2 implants)
- [ ] Write test suite (no tests exist yet)
