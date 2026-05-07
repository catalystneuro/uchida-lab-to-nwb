"""Convert a single Uchida Lab (Phillips 2025) session to NWB."""

import re
from datetime import date, datetime, time
from pathlib import Path
from typing import Union
from zoneinfo import ZoneInfo

from neuroconv.utils import dict_deep_update, load_dict_from_file

from uchida_lab_to_nwb.phillips_2025.phillips_2025_nwbconverter import (
    Phillips2025NWBConverter,
)

# Harvard is in the Eastern timezone
_TIMEZONE = ZoneInfo("America/New_York")

# pCampi filename pattern: YYMMDD_HHMMSS_M{id}.h5
_PCAMPI_PATTERN = re.compile(r"(\d{6}_\d{6})_(M\d+)\.h5")


def session_to_nwb(
    session_dir_path: Union[str, Path],
    output_dir_path: Union[str, Path],
    subject_metadata: dict | None = None,
    stub_test: bool = False,
    overwrite: bool = False,
    verbose: bool = False,
) -> None:
    """Convert one subject-session directory to an NWB file.

    Parameters
    ----------
    session_dir_path : str or Path
        Path to a single subject-session directory, e.g.
        ``Lone_data/day_1/M4``.
        Expected contents:
        - ``YYYYMMDD_HHMMSS_M{id}.h5``    — pCampi sync file
        - ``BBC300_Acq_*.doric``           — raw Doric photometry
        - ``interpolated_campy_and_doric_data.mat`` — processed dF/F
        - ``DANNCE/save_data_AVG0.mat``    — DANNCE pose output
        - ``calibration/calibration.json`` — 6-camera calibration
        - ``videos/Camera{1..6}/0.mp4``    — per-camera videos
        - ``videos/Camera1/frametimes.npy``— per-frame timestamps
    output_dir_path : str or Path
        Directory where the NWB file will be written.
    subject_metadata : dict, optional
        Per-subject NWB Subject fields (species, sex, age, strain, etc.).
        When not provided, placeholders from ``_metadata/phillips_2025_metadata.yaml`` are used.
    stub_test : bool
        If True, write a small stub file for quick testing.
    overwrite : bool
        If True, overwrite an existing NWB file at the output path.
    verbose : bool
        Pass-through to converter interfaces.
    """
    session_dir_path = Path(session_dir_path)
    output_dir_path = Path(output_dir_path)
    if stub_test:
        output_dir_path = output_dir_path / "nwb_stub"
    output_dir_path.mkdir(parents=True, exist_ok=True)

    # ── Discover files ────────────────────────────────────────────────────────
    pcampi_files = list(session_dir_path.glob("*.h5"))
    assert len(pcampi_files) == 1, f"Expected one .h5 sync file, found: {pcampi_files}"
    pcampi_file = pcampi_files[0]

    doric_files = list(session_dir_path.glob("*.doric"))
    assert len(doric_files) == 1, f"Expected one .doric file, found: {doric_files}"
    doric_file = doric_files[0]

    processed_mat = session_dir_path / "interpolated_campy_and_doric_data.mat"
    dannce_mat = session_dir_path / "DANNCE" / "save_data_AVG0.mat"
    frametimes_npy = session_dir_path / "videos" / "Camera1" / "frametimes.npy"

    # ── Parse session_id and subject_id from pCampi filename ─────────────────
    m = _PCAMPI_PATTERN.match(pcampi_file.name)
    if m:
        datetime_str, subject_id = m.group(1), m.group(2)
        session_id = f"{datetime_str}_{subject_id}"
    else:
        subject_id = session_dir_path.name  # fallback
        session_id = session_dir_path.name

    nwbfile_path = output_dir_path / f"sub-{subject_id}_ses-{session_id}.nwb"
    if nwbfile_path.exists() and not overwrite and not stub_test:
        print(
            f"Skipping {nwbfile_path} (already exists). Pass overwrite=True to overwrite."
        )
        return

    # ── Build source_data ────────────────────────────────────────────────────
    source_data = {}
    conversion_options = {}

    # pCampi sync (always present)
    source_data["PCampiSync"] = dict(file_path=str(pcampi_file))
    conversion_options["PCampiSync"] = dict(stub_test=stub_test)

    # Raw Doric photometry (always present)
    source_data["DoricPhotometry"] = dict(file_path=str(doric_file))
    conversion_options["DoricPhotometry"] = dict(stub_test=stub_test, timing_source="aligned_timestamps")

    # Processed dF/F (present when pipeline has been run)
    if processed_mat.is_file() and frametimes_npy.is_file():
        source_data["DoricProcessed"] = dict(
            file_path=str(processed_mat),
            frametimes_file_path=str(frametimes_npy),
        )
        conversion_options["DoricProcessed"] = dict(stub_test=stub_test)

    # DANNCE pose estimation
    if dannce_mat.is_file() and frametimes_npy.is_file():
        source_data["DANNCE"] = dict(
            file_path=str(dannce_mat),
            frametimes_file_path=str(frametimes_npy),
            subject_name=subject_id,
            animal_index=0,
        )
        conversion_options["DANNCE"] = dict(stub_test=stub_test)

    # 6-camera video
    for cam_idx in range(1, 7):
        mp4 = session_dir_path / "videos" / f"Camera{cam_idx}" / "0.mp4"
        if mp4.is_file():
            key = f"VideoCamera{cam_idx}"
            source_data[key] = dict(
                file_paths=[str(mp4)],
                video_name=f"VideoCamera{cam_idx}",
            )
            # ExternalVideoInterface stores video as a file path reference — no stub needed
            conversion_options[key] = dict()

    # ── Instantiate converter ────────────────────────────────────────────────
    converter = Phillips2025NWBConverter(source_data=source_data, verbose=verbose)

    # ── Build metadata (layered) ─────────────────────────────────────────────
    # Layer 1: auto-extracted (session_start_time from pCampi filename)
    metadata = converter.get_metadata()

    # Layer 2: add timezone to session_start_time
    if metadata["NWBFile"].get("session_start_time"):
        metadata["NWBFile"]["session_start_time"] = metadata["NWBFile"][
            "session_start_time"
        ].replace(tzinfo=_TIMEZONE)

    # Layer 3: lab-level YAML metadata
    yaml_path = Path(__file__).parent / "_metadata" / "phillips_2025_metadata.yaml"
    editable_metadata = load_dict_from_file(yaml_path)
    metadata = dict_deep_update(metadata, editable_metadata)

    # Layer 3b: fiber photometry hardware metadata
    fp_yaml_path = Path(__file__).parent / "_metadata" / "fiber_photometry.yaml"
    metadata = dict_deep_update(metadata, load_dict_from_file(fp_yaml_path))

    # Layer 4: session-specific overrides
    metadata["NWBFile"]["session_id"] = session_id
    metadata["Subject"]["subject_id"] = subject_id

    # Per-subject metadata from caller (species, sex, DOB, strain, etc.)
    if subject_metadata:
        metadata["Subject"] = dict_deep_update(metadata["Subject"], subject_metadata)

    # Promote date_of_birth to datetime with timezone if loaded as a bare date
    # (PyYAML parses YYYY-MM-DD as datetime.date; PyNWB Subject requires datetime)
    dob = metadata["Subject"].get("date_of_birth")
    if isinstance(dob, date) and not isinstance(dob, datetime):
        metadata["Subject"]["date_of_birth"] = datetime.combine(dob, time.min).replace(tzinfo=_TIMEZONE)

    # ── Run conversion ───────────────────────────────────────────────────────
    converter.run_conversion(
        nwbfile_path=nwbfile_path,
        metadata=metadata,
        conversion_options=conversion_options,
        overwrite=overwrite or stub_test,
    )
    if verbose:
        print(f"Wrote {nwbfile_path}")


if __name__ == "__main__":
    from uchida_lab_to_nwb.phillips_2025.phillips_2025_convert_all_sessions import (
        load_subject_metadata_from_xlsx,
    )

    _all_subjects = load_subject_metadata_from_xlsx(
        "H:/Uchida-CN-data-share/Subject metadata.xlsx"
    )
    _subject_meta = _all_subjects.get("M4", {})

    session_to_nwb(
        session_dir_path="H:/Uchida-CN-data-share/Hannah_data/M4-M7/Lone_data/day_1/M4",
        output_dir_path="H:/uchida-nwbfiles",
        subject_metadata=_subject_meta,
        stub_test=True,
        verbose=True,
    )
