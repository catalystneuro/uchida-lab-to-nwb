"""sDANNCE 3D pose estimation interface for the Uchida Lab (adapted from olveczky-lab-to-nwb).

Wraps the NeuroConv DANNCEInterface to load per-frame timestamps from
frametimes.npy files rather than computing them from a fixed sampling rate.

frametimes.npy layout (shape: 2 × n_frames):
    row 0 — 1-based frame indices
    row 1 — elapsed seconds from session start (campy/Arduino clock)
"""
from pathlib import Path

import numpy as np
from pydantic import FilePath, validate_call

from neuroconv.datainterfaces.behavior.dannce.danncedatainterface import DANNCEInterface

# Placeholder keypoint names for the standard DANNCE 23-joint rat skeleton.
# UPDATE once the lab confirms the ordered joint list.
SDANNCE_LANDMARK_NAMES_PLACEHOLDER = [f"landmark_{i}" for i in range(23)]


class SDANNCEInterface(DANNCEInterface):
    """DANNCE / social-DANNCE 3D pose estimation interface for the Uchida Lab.

    Extends :class:`DANNCEInterface` with support for loading per-frame timestamps
    directly from a ``frametimes.npy`` file (the campy/pCampi standard) rather than
    from video metadata or a fixed sampling rate.

    Parameters
    ----------
    file_path : FilePath
        Path to the DANNCE prediction file (``save_data_AVG0.mat``).
    frametimes_file_path : FilePath
        Path to ``frametimes.npy`` for Camera1 (shape 2 × n_frames;
        row 1 = elapsed seconds from session start).
    landmark_names : list of str, optional
        Ordered keypoint names matching the 23 joints in the ``pred`` array.
        Defaults to ``["landmark_0", …, "landmark_22"]`` until the lab provides the list.
    subject_name : str
        Identifier for this rat within the session (e.g. "M4").
    verbose : bool
        Verbosity flag passed to the parent class.
    """

    def _load_dannce_data(self, file_path) -> None:
        super()._load_dannce_data(file_path)
        # sDANNCE output has an extra animal-index axis: (n_frames, n_animals, 3, n_landmarks)
        # DANNCEInterface expects (n_frames, 3, n_landmarks) — squeeze the animal dim.
        if self._pred.ndim == 4:
            self._pred = self._pred[:, 0, :, :]
        if self._p_max.ndim == 3:
            self._p_max = self._p_max[:, 0, :]

    @validate_call
    def __init__(
        self,
        file_path: FilePath,
        frametimes_file_path: FilePath,
        landmark_names: list[str] | None = None,
        subject_name: str = "rat",
        verbose: bool = False,
    ):
        if landmark_names is None:
            landmark_names = SDANNCE_LANDMARK_NAMES_PLACEHOLDER

        pose_estimation_metadata_key = (
            f"PoseEstimationDANNCE_{subject_name}"
        )

        super().__init__(
            file_path=file_path,
            landmark_names=landmark_names,
            subject_name=subject_name,
            pose_estimation_metadata_key=pose_estimation_metadata_key,
            verbose=verbose,
        )

        frametimes = np.load(str(frametimes_file_path))  # (2, n_video_frames)
        all_timestamps = frametimes[1]  # row 1 = elapsed seconds, 0-based columns
        frame_indices = self._sample_id.astype(int)  # 0-based frame indices
        self.set_aligned_timestamps(all_timestamps[frame_indices])

    def get_metadata(self) -> dict:
        metadata = super().get_metadata()
        # NWB Inspector requires the full word "millimeters" not the abbreviation "mm"
        container_key = self.pose_estimation_metadata_key
        series_meta = (
            metadata.get("PoseEstimation", {})
            .get("PoseEstimationContainers", {})
            .get(container_key, {})
            .get("PoseEstimationSeries", {})
        )
        for series in series_meta.values():
            if series.get("unit") == "mm":
                series["unit"] = "millimeters"
        return metadata

    def get_conversion_options_schema(self) -> dict:
        schema = super().get_conversion_options_schema()
        schema["properties"]["stub_test"] = {
            "type": "boolean",
            "default": False,
            "description": "If True, write only the first 100 frames for quick testing.",
        }
        return schema

    def add_to_nwbfile(self, nwbfile, metadata: dict | None = None, stub_test: bool = False) -> None:
        if stub_test:
            _pred, _pmax, _sid, _ts = self._pred, self._p_max, self._sample_id, self._timestamps
            n = 100
            self._pred = _pred[:n]
            self._p_max = _pmax[:n]
            self._sample_id = _sid[:n]
            self._timestamps = _ts[:n] if _ts is not None else None
            try:
                super().add_to_nwbfile(nwbfile=nwbfile, metadata=metadata)
            finally:
                self._pred, self._p_max, self._sample_id, self._timestamps = _pred, _pmax, _sid, _ts
        else:
            super().add_to_nwbfile(nwbfile=nwbfile, metadata=metadata)
