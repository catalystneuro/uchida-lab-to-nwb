"""Interface for lab-processed fiber photometry data (interpolated_campy_and_doric.mat)."""

import numpy as np
from pydantic import FilePath, validate_call

from neuroconv.datainterfaces.fiber_photometry.basefiberphotometryinterface import (
    BaseFiberPhotometryInterface,
)
from neuroconv.tools.fiber_photometry import (
    add_fiber_photometry_devices,
    add_fiber_photometry_lab_metadata,
    get_fiber_photometry_table_region,
)
from neuroconv.tools.nwb_helpers import get_module


class ProcessedFiberPhotometryInterface(BaseFiberPhotometryInterface):
    """Interface for lab-processed fiber photometry signals.

    Reads ``interpolated_campy_and_doric.mat`` produced by the Uchida lab's MATLAB
    preprocessing pipeline: for each Doric excitation channel (``CAM1EXC1`` = control/tdTomato,
    ``CAM1EXC2`` = dopamine_signal/GRABDA3m), the raw demodulated ROI fluorescence (still 3 ROI
    columns, matching the raw ``.doric`` file) has been resampled/interpolated to the video frame
    rate (~50 Hz). These are raw fluorescence values, not dF/F.

    This is a lab-specific derivative of the raw Doric data (``DoricFiberPhotometryInterface``
    must still run to create the shared ``fiber_photometry`` lab_meta_data / FiberPhotometryTable
    this interface reuses). Unlike the raw interfaces, this writes its response series to the
    ``processing/ophys`` module rather than ``acquisition``, since the data is a processed
    derivative.

    Timestamps are not embedded in the ``.mat`` file (the lab pipeline interpolated to the video
    frame grid but did not record it); pass ``frametimes_file_path`` (a ``frametimes.npy``, shape
    ``(2, n_frames)``, row 1 = elapsed seconds) for the initial timestamps. These are typically
    replaced with the pCampi-aligned video frame times by
    ``Phillips2025NWBConverter.temporally_align_data_interfaces()``.
    """

    display_name = "ProcessedFiberPhotometry"
    info = "Data interface for lab-processed (interpolated) fiber photometry signals."
    associated_suffixes = ("mat",)
    keywords = ("fiber photometry", "processed", "interpolated")

    @validate_call
    def __init__(
        self,
        *,
        file_path: FilePath,
        frametimes_file_path: FilePath,
        stream_names: str | list[str],
        metadata_key: str | None = None,
        stream_indices: list[int] | None = None,
        verbose: bool = False,
    ):
        """Initialize the ProcessedFiberPhotometryInterface.

        Parameters
        ----------
        file_path : FilePath
            Path to ``interpolated_campy_and_doric.mat``.
        frametimes_file_path : FilePath
            Path to the corresponding ``frametimes.npy`` (shape ``(2, n_frames)``; row 1 = elapsed
            seconds from session start), used for the initial (pre-alignment) timestamps.
        stream_names : str or list of str
            Doric excitation-channel name(s) (e.g. ``"CAM1EXC1"``) whose ROI traces are
            column-stacked into this interface's single ``FiberPhotometryResponseSeries``. Call
            :meth:`get_available_streams` to discover them.
        metadata_key : str, optional
            Key under ``metadata["FiberPhotometry"]`` holding this interface's response-series
            metadata. When ``None`` (default), it is generated from ``stream_names``.
        stream_indices : list of int, optional
            Column indices selecting which ROI columns to keep (e.g. ``[0, 1]`` for NAc, TS,
            dropping the still-unidentified third ROI column).
        verbose : bool, default: False
            Whether to print status messages.
        """
        super().__init__(
            file_path=file_path,
            frametimes_file_path=frametimes_file_path,
            stream_names=stream_names,
            metadata_key=metadata_key,
            stream_indices=stream_indices,
            verbose=verbose,
        )
        self._streams: dict[str, int] = self._discover_streams(self.source_data["file_path"])
        frametimes = np.load(str(self.source_data["frametimes_file_path"]))
        self._video_timestamps = frametimes[1]

    # ------------------------------------------------------------------
    # Stream discovery
    # ------------------------------------------------------------------

    @staticmethod
    def _decode_matlab_char_dataset(dataset) -> str:
        """Decode a MATLAB v7.3 char array (stored as uint16 codes) into a str."""
        return "".join(chr(code) for code in np.asarray(dataset).flatten())

    @classmethod
    def get_available_streams(cls, file_path) -> list[str]:
        """Return the Doric excitation-channel names available in the ``.mat`` file.

        Parameters
        ----------
        file_path : FilePath
            Path to ``interpolated_campy_and_doric.mat``.

        Returns
        -------
        list[str]
            Sorted list of channel names (e.g. ``["CAM1EXC1", "CAM1EXC2"]``).
        """
        return sorted(cls._discover_streams(file_path))

    @classmethod
    def _discover_streams(cls, file_path) -> dict:
        """Return channel_name -> index into ``interpolated_data/roi_traces_interpolated``.

        The ``.mat`` file (MATLAB v7.3 / HDF5) holds one struct, ``interpolated_data``, with two
        parallel fields: ``channel_names`` (one entry per Doric excitation channel) and
        ``roi_traces_interpolated`` (one ``(n_frames, n_rois)`` array per channel, same order).
        """
        import h5py

        streams: dict[str, int] = {}
        with h5py.File(file_path, "r") as f:
            struct = f["interpolated_data"]
            channel_name_refs = struct["channel_names"][:].flatten()
            for index, ref in enumerate(channel_name_refs):
                channel_name = cls._decode_matlab_char_dataset(f[ref])
                streams[channel_name] = index
        return streams

    # ------------------------------------------------------------------
    # Per-stream data / timestamps
    # ------------------------------------------------------------------

    def _get_stream_data(self, *, stream_name: str) -> np.ndarray:
        import h5py

        index = self._streams[stream_name]
        with h5py.File(self.source_data["file_path"], "r") as f:
            struct = f["interpolated_data"]
            trace_ref = struct["roi_traces_interpolated"][:].flatten()[index]
            return np.asarray(f[trace_ref][:])

    def _get_stream_timestamps(self, *, stream_name: str) -> np.ndarray:
        # All channels share the same video-rate timestamps (interpolated to a common frame grid).
        return self._video_timestamps

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
        strict: bool = False,
    ) -> None:
        from ndx_fiber_photometry import FiberPhotometryResponseSeries

        metadata = metadata or self.get_metadata()
        fiber_photometry_metadata = metadata["FiberPhotometry"]
        self._warn_about_placeholder_metadata(fiber_photometry_metadata, strict=strict)

        def stub(array: np.ndarray) -> np.ndarray:
            return array[: min(stub_samples, len(array))] if stub_test else array

        add_fiber_photometry_devices(nwbfile=nwbfile, metadata=metadata)
        fiber_photometry_table = add_fiber_photometry_lab_metadata(
            nwbfile=nwbfile,
            fiber_photometry_metadata=fiber_photometry_metadata,
            devices_metadata=metadata["Devices"],
        )

        data = stub(self._read_response_data())
        timestamps = stub(self.get_timestamps())
        timing_kwargs = self._timing_kwargs_from_timestamps(timestamps, always_write_timestamps)

        series_metadata = fiber_photometry_metadata[self.metadata_key]
        table_region = get_fiber_photometry_table_region(
            fiber_photometry_table=fiber_photometry_table,
            table_rows_metadata=fiber_photometry_metadata["FiberPhotometryTable"]["rows"],
            row_metadata_keys=series_metadata["fiber_photometry_table_region"],
            description=series_metadata["fiber_photometry_table_region_description"],
        )
        response_series = FiberPhotometryResponseSeries(
            name=series_metadata["name"],
            description=series_metadata["description"],
            data=data,
            unit=series_metadata["unit"],
            fiber_photometry_table_region=table_region,
            **timing_kwargs,
        )

        ophys = get_module(nwbfile, "ophys", "Processed optical physiology data")
        ophys.add(response_series)
