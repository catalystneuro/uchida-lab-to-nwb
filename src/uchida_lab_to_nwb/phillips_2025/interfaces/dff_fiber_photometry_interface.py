"""Ad hoc interface for the lab-computed dF/F trace(s) in ``processed_dff.mat``."""

import numpy as np
from pydantic import FilePath, validate_call

from neuroconv.datainterfaces.fiber_photometry.basefiberphotometryinterface import (
    BaseFiberPhotometryInterface,
)


class DffFiberPhotometryInterface(BaseFiberPhotometryInterface):
    """Ad hoc interface for the lab-computed dF/F trace(s) in ``processed_dff.mat``.

    Reads ``processed_dff.mat`` (MATLAB v7.3 / HDF5): one flat top-level variable per fiber
    site, ``dff_resG`` and, where present, ``dff_resG2`` -- each stored as a single row/column
    vector (shape ``(1, n_samples)`` or ``(n_samples, 1)``). Column-stacked (via the inherited
    ``stream_names``/``stream_indices`` mechanism) into this interface's single
    ``FiberPhotometryResponseSeries``, written to ``processing/ophys`` since the data is a
    processed derivative, not raw acquisition.

    No embedded timestamps; like ``ProcessedFiberPhotometryInterface``, generates a nominal
    regular series from a caller-supplied ``sampling_rate`` (e.g. the video frame rate).

    See the module docstring for why this interface is not part of the main conversion.
    """

    display_name = "DffFiberPhotometry"
    info = (
        "Ad hoc interface for the lab-computed processed_dff.mat dF/F trace(s) -- excluded from "
        "the main conversion pending lab confirmation of trace identity and scale."
    )
    associated_suffixes = ("mat",)
    keywords = ("fiber photometry", "dF/F", "ad hoc")

    @validate_call
    def __init__(
        self,
        *,
        file_path: FilePath,
        sampling_rate: float,
        stream_names: str | list[str],
        metadata_key: str | None = None,
        stream_indices: list[int] | None = None,
        verbose: bool = False,
    ):
        """Initialize the DffFiberPhotometryInterface.

        Parameters
        ----------
        file_path : FilePath
            Path to ``processed_dff.mat``.
        sampling_rate : float
            Nominal sampling rate (Hz) used to generate a regular timestamps array
            (``starting_time=0.0``, ``rate=sampling_rate``) on this interface's own, unaligned
            clock -- e.g. the camera's ``frameRate`` from ``metadata.csv``.
        stream_names : str or list of str
            Variable name(s) to column-stack into this interface's single
            ``FiberPhotometryResponseSeries``, e.g. ``["dff_resG", "dff_resG2"]``. Call
            :meth:`get_available_streams` to discover what a given file actually contains --
            ``dff_resG2`` is absent for M4 sessions.
        metadata_key : str, optional
            Key under ``metadata["FiberPhotometry"]`` holding this interface's response-series
            metadata. When ``None`` (default), it is generated from ``stream_names``.
        stream_indices : list of int, optional
            Column indices selecting which columns of the column-stacked data to keep. ``None``
            (default) keeps all columns.
        verbose : bool, default: False
            Whether to print status messages.
        """
        super().__init__(
            file_path=file_path,
            stream_names=stream_names,
            metadata_key=metadata_key,
            stream_indices=stream_indices,
            verbose=verbose,
        )
        self._sampling_rate = float(sampling_rate)
        available_streams = self.get_available_streams(self.source_data["file_path"])
        missing_streams = [name for name in self.stream_names if name not in available_streams]
        if missing_streams:
            raise ValueError(
                f"Requested stream(s) {missing_streams} not found in "
                f"{self.source_data['file_path']!r}; available: {available_streams}."
            )

    # ------------------------------------------------------------------
    # Stream discovery
    # ------------------------------------------------------------------

    @classmethod
    def get_available_streams(cls, file_path) -> list[str]:
        """Return the dF/F variable names present in the ``.mat`` file.

        Parameters
        ----------
        file_path : FilePath
            Path to ``processed_dff.mat``.

        Returns
        -------
        list[str]
            Sorted list of variable names -- ``["dff_resG"]`` or ``["dff_resG", "dff_resG2"]``.
        """
        import h5py

        with h5py.File(file_path, "r") as f:
            return sorted(f.keys())

    # ------------------------------------------------------------------
    # Per-stream data / timestamps
    # ------------------------------------------------------------------

    def _get_stream_data(self, *, stream_name: str) -> np.ndarray:
        import h5py

        with h5py.File(self.source_data["file_path"], "r") as f:
            return np.asarray(f[stream_name][:]).flatten()

    def _get_stream_timestamps(self, *, stream_name: str) -> np.ndarray:
        # No real clock available for this stream (see class docstring); generate a nominal
        # regular timestamps array on this interface's own, unaligned clock.
        n_samples = self._get_stream_data(stream_name=stream_name).shape[0]
        return np.arange(n_samples) / self._sampling_rate

    # ------------------------------------------------------------------
    # NWB conversion (writes to processing/ophys instead of acquisition)
    # ------------------------------------------------------------------

    def add_to_nwbfile(
        self,
        nwbfile,
        metadata: dict | None = None,
        *,
        stub_test: bool = False,
        stub_samples: int = 100,
        always_write_timestamps: bool = False,
    ) -> None:
        super().add_to_nwbfile(
            nwbfile,
            metadata=metadata,
            stub_test=stub_test,
            stub_samples=stub_samples,
            always_write_timestamps=always_write_timestamps,
            parent_container="processing/ophys",
        )
