"""Convert a single Uchida Lab (Phillips 2025) session to NWB."""

import csv
import re
from datetime import date, datetime, time
from pathlib import Path
from typing import Union
from zoneinfo import ZoneInfo

from neuroconv.utils import dict_deep_update, load_dict_from_file

from uchida_lab_to_nwb.phillips_2025.nwbconverter import (
    Phillips2025NWBConverter,
)
from uchida_lab_to_nwb.phillips_2025.utils.constants import (
    SDANNCE_LANDMARK_NAMES,
    SDANNCE_SKELETON_EDGES,
)

# Harvard is in the Eastern timezone
_TIMEZONE = ZoneInfo("America/New_York")

# pCampi filename pattern: YYMMDD_HHMMSS_M{id}.h5
_PCAMPI_PATTERN = re.compile(r"(\d{6}_\d{6})_(M\d+)\.h5")

# Maps each raw-Doric-photometry interface slot (Phillips2025NWBConverter.data_interface_classes)
# to the Doric excitation channel's two ROI stream names (column-stacked into that interface's
# single FiberPhotometryResponseSeries) and the fiber_photometry.yaml metadata_key holding its
# response-series metadata.
_DORIC_INTERFACE_CONFIG = {
    "DoricControl": dict(
        stream_names=[
            "BBC300_ROISignals_Series0001_CAM1EXC1_ROI01",
            "BBC300_ROISignals_Series0001_CAM1EXC1_ROI02",
        ],
        metadata_key="fiber_photometry_control",
    ),
    "DoricDopamineSignal": dict(
        stream_names=[
            "BBC300_ROISignals_Series0001_CAM1EXC2_ROI01",
            "BBC300_ROISignals_Series0001_CAM1EXC2_ROI02",
        ],
        metadata_key="fiber_photometry_dopamine_signal",
    ),
}

# Maps each processed (interpolated) fiber-photometry interface slot to the Doric excitation
# channel name (as read from interpolated_campy_and_doric.mat) and its fiber_photometry.yaml
# metadata_key, mirroring _DORIC_INTERFACE_CONFIG above.
_PROCESSED_INTERFACE_CONFIG = {
    "InterpolatedFPControlSignal": dict(
        stream_name="CAM1EXC1", metadata_key="fiber_photometry_interpolated_control"
    ),
    "InterpolatedFPDopamineSignal": dict(
        stream_name="CAM1EXC2",
        metadata_key="fiber_photometry_interpolated_dopamine_signal",
    ),
}


def _read_camera_frame_rate(videos_folder_path: Path) -> float:
    """Read the ``frameRate`` field (Hz) from a campy ``metadata.csv`` file."""
    metadata_csv_path = videos_folder_path / "Camera1" / "metadata.csv"
    with open(metadata_csv_path, newline="") as f:
        for key, value in csv.reader(f):
            if key == "frameRate":
                return float(value)
    raise ValueError(f"'frameRate' not found in {metadata_csv_path}")


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
        - ``interpolated_campy_and_doric.mat``      — processed (interpolated) fiber photometry
        - ``DANNCE/save_data_AVG0.mat``    — DANNCE pose output
        - ``calibration/calibration.json`` — 6-camera calibration (+ hires_camN_params.mat)
        - ``videos/Camera{1..6}/0.mp4``    — per-camera videos
        - ``videos/Camera1/metadata.csv``  — camera acquisition metadata (frameRate, etc.)
    output_dir_path : str or Path
        Directory where the NWB file will be written.
    subject_metadata : dict, optional
        Per-subject NWB Subject fields (species, sex, age, strain, etc.).
        When not provided, placeholders from ``metadata/phillips_2025_metadata.yaml`` are used.
    stub_test : bool
        If True, write a small stub file for quick testing.
    overwrite : bool
        If True, overwrite an existing NWB file at the output path.
    verbose : bool
        Pass-through to converter interfaces.

    Notes
    -----
    Temporal alignment across streams is not yet implemented (see conversion_notes.md). Each
    stream currently writes timestamps on its own native/nominal clock. ``NWBFile.session_start_time``
    is set from the pCampi filename (``PCampiSyncInterface`` is the only interface that sets it);
    ``DoricFiberPhotometryInterface`` does not set its own session_start_time, so raw Doric
    photometry timestamps (Doric's own clock, not offset-corrected to pCampi) should not be
    interpreted as starting exactly at ``session_start_time``.
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

    processed_mat = session_dir_path / "interpolated_campy_and_doric.mat"
    dannce_mat = session_dir_path / "DANNCE" / "save_data_AVG0.mat"
    videos_folder_path = session_dir_path / "videos"

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

    # Raw Doric photometry (always present): one interface per channel, each writing a single
    # FiberPhotometryResponseSeries whose two columns are the NAc and TS ROIs (column-stacked
    # via a 2-element stream_names list; both ROIs under one excitation channel share the same
    # Doric "Time" array, so this is safe). Table region order matches column order: NAc, TS.
    # See fiber_photometry.yaml for the matching metadata_key entries.
    for key, config in _DORIC_INTERFACE_CONFIG.items():
        source_data[key] = dict(
            file_path=str(doric_file),
            stream_names=config["stream_names"],
            metadata_key=config["metadata_key"],
        )
        conversion_options[key] = dict(stub_test=stub_test)

    # Processed (interpolated) fiber photometry (present when pipeline has been run): one
    # interface per channel, mirroring the raw Doric interfaces above.
    if processed_mat.is_file() and videos_folder_path.is_dir():
        camera_frame_rate = _read_camera_frame_rate(videos_folder_path)
        for key, config in _PROCESSED_INTERFACE_CONFIG.items():
            source_data[key] = dict(
                file_path=str(processed_mat),
                sampling_rate=camera_frame_rate,
                stream_names=config["stream_name"],
                stream_indices=[0, 1],
                metadata_key=config["metadata_key"],
            )
            conversion_options[key] = dict(stub_test=stub_test)

    # DANNCE pose estimation + 6-camera video (combined via DANNCEConverter). No
    # frametimes_file_path is passed; instead DANNCE pose timestamps are computed
    # from sampleID / sampling_rate, and each camera's video keeps its own native
    # per-frame timestamps.
    pose_key = "PoseEstimationDANNCE"
    if dannce_mat.is_file() and videos_folder_path.is_dir():

        source_data["DANNCE"] = dict(
            file_path=str(dannce_mat),
            videos_folder_path=videos_folder_path,
            landmark_names=SDANNCE_LANDMARK_NAMES,
            subject_name=subject_id,
            metadata_key=pose_key,
            animal_index=0,
        )
        calibration_path = session_dir_path / "calibration"
        if calibration_path.is_dir():
            source_data["DANNCE"]["calibration_path"] = str(calibration_path)
        # DANNCEConverter writes video in full regardless of stub_test; only the DANNCE
        # pose predictions are truncated for quick smoke testing.
        conversion_options["DANNCE"] = dict(stub_test=stub_test)

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
    yaml_path = Path(__file__).parent / "general_metadata.yaml"
    editable_metadata = load_dict_from_file(yaml_path)
    metadata = dict_deep_update(metadata, editable_metadata)

    # Layer 3b: fiber photometry hardware metadata
    fp_yaml_path = Path(__file__).parent / "fiber_photometry.yaml"
    metadata = dict_deep_update(metadata, load_dict_from_file(fp_yaml_path))

    # Each DoricFiberPhotometryInterface seeds a placeholder "row0" FiberPhotometryTable row
    # and "indicator" FiberPhotometryIndicators entry by default (get_default_fiber_photometry_
    # metadata()); fiber_photometry.yaml defines the real rows/indicators under different keys
    # (row_{control,dopamine_signal}_{NAc,TS} for the table, GRABDA3m/tdTomato for indicators),
    # so the placeholders survive the deep-merge above, unreferenced by any series. Drop them.
    metadata["FiberPhotometry"]["FiberPhotometryTable"]["rows"].pop("row0", None)
    metadata["FiberPhotometry"]["FiberPhotometryIndicators"].pop("indicator", None)
    # Same default-scaffold placeholders exist for the top-level Devices/DeviceModels
    # registries added_fiber_photometry_devices() would otherwise write unreferenced.
    for _key in ("optical_fiber", "excitation_source", "photodetector"):
        metadata["Devices"].pop(_key, None)
    for _key in (
        "optical_fiber_model",
        "excitation_source_model",
        "photodetector_model",
    ):
        metadata["DeviceModels"].pop(_key, None)

    # dict_deep_update concatenates lists rather than replacing them, so each series'
    # fiber_photometry_table_region ends up as ["row0", "row_..."] after the merge above;
    # reset it to just the real rows now that "row0" itself has been dropped. Order matches
    # the column order of each interface's stream_names list (NAc, then TS).
    _fp_table_region_by_key = {
        "fiber_photometry_control": ["row_control_NAc", "row_control_TS"],
        "fiber_photometry_dopamine_signal": [
            "row_dopamine_signal_NAc",
            "row_dopamine_signal_TS",
        ],
        "fiber_photometry_interpolated_control": ["row_control_NAc", "row_control_TS"],
        "fiber_photometry_interpolated_dopamine_signal": [
            "row_dopamine_signal_NAc",
            "row_dopamine_signal_TS",
        ],
    }
    for _key, _region in _fp_table_region_by_key.items():
        metadata["FiberPhotometry"][_key]["fiber_photometry_table_region"] = _region

    # Layer 4: session-specific overrides
    metadata["NWBFile"]["session_id"] = session_id
    metadata["Subject"]["subject_id"] = subject_id

    # Per-subject metadata from caller (species, sex, DOB, strain, etc.)
    if subject_metadata:
        metadata["Subject"] = dict_deep_update(metadata["Subject"], subject_metadata)

    # Inject skeleton edges and DANNCE labels into Behavior/Pose metadata. DANNCEInterface's own
    # get_metadata() seeds Skeletons[pose_key] with nodes but an empty edges list (it has no
    # anatomical knowledge), so DANNCEInterface.add_to_nwbfile() looks up the skeleton by
    # pose_key (via PoseEstimations[pose_key]["skeleton_metadata_key"]) — the override below must
    # use that same pose_key as the dict key (not the Skeleton's descriptive "name" field) for the
    # deep-merge in add_to_nwbfile() to actually replace the empty default.
    if "DANNCE" in source_data:
        skeleton_name = f"Skeleton{pose_key}_{subject_id.capitalize()}"
        behavior_pose = metadata.setdefault("Behavior", {}).setdefault("Pose", {})
        behavior_pose.setdefault("Skeletons", {})[pose_key] = {
            "name": skeleton_name,
            "nodes": SDANNCE_LANDMARK_NAMES,
            "edges": SDANNCE_SKELETON_EDGES,
        }
        behavior_pose.setdefault("PoseEstimations", {})[pose_key] = {
            "name": pose_key,
            "source_software": "DANNCE",
            "scorer": "DANNCE",
            "description": "3D keypoint coordinates estimated using DANNCE.",
        }

    # Promote date_of_birth to datetime with timezone if loaded as a bare date
    # (PyYAML parses YYYY-MM-DD as datetime.date; PyNWB Subject requires datetime)
    dob = metadata["Subject"].get("date_of_birth")
    if isinstance(dob, date) and not isinstance(dob, datetime):
        metadata["Subject"]["date_of_birth"] = datetime.combine(dob, time.min).replace(
            tzinfo=_TIMEZONE
        )

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
    from uchida_lab_to_nwb.phillips_2025.utils.subject_metadata import (
        get_subject_metadata,
    )

    _subject_meta = get_subject_metadata(
        subject_id="M4", xlsx_path=Path("H:/Uchida-CN-data-share/Subject metadata.xlsx")
    )

    session_to_nwb(
        session_dir_path="H:/Uchida-CN-data-share/Hannah_data/M4-M7/Lone_data/day_1/M4",
        output_dir_path="H:/uchida-nwbfiles",
        subject_metadata=_subject_meta,
        stub_test=True,
        verbose=True,
    )
