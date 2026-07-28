"""Interface for a single pCampi (LabVIEW) synchronization TTL channel (.h5 files)."""

import re
import warnings
from datetime import datetime
from pathlib import Path

import h5py
import numpy as np
from pydantic import FilePath
from pynwb import TimeSeries
from pynwb.file import NWBFile

from neuroconv.basedatainterface import BaseDataInterface
from neuroconv.utils import DeepDict

# pCampi records at exactly 1 kHz on the NIDAQ
_DEFAULT_SAMPLING_RATE = 1000.0

# Filename pattern: YYYYMMDD_HHMMSS_M{id}.h5
_FILENAME_PATTERN = re.compile(r"(\d{6}_\d{6})_M\d+\.h5")


class PCampiSyncInterface(BaseDataInterface):
    """Interface for a single pCampi LabVIEW synchronization TTL channel.

    Reads one digital channel from the H5 file written by pCampi (LabVIEW), out of the NIDAQ
    digital input channels recorded at 1 kHz. This interface writes a single ``TimeSeries`` per
    instance -- it does not assume how many channels exist or what they are named. If an NWB
    file needs more than one TTL channel written, instantiate this interface once per channel
    (each with a different ``channel_name``); call :meth:`get_available_channels` to discover
    the channel names present in a given file.

    The pCampi clock defines the NWB time base for this session (``session_start_time`` is
    parsed from the filename by whichever instance's ``get_metadata()`` runs). Cross-stream
    alignment of other data streams to this clock is handled elsewhere (see
    ``Phillips2025NWBConverter.temporally_align_data_interfaces()``).
    """

    keywords = ["synchronization", "TTL", "pCampi", "LabVIEW"]

    def __init__(
        self,
        file_path: FilePath,
        channel_name: str,
        sampling_rate: float = _DEFAULT_SAMPLING_RATE,
        verbose: bool = False,
    ):
        """Initialize the interface for one TTL channel.

        Parameters
        ----------
        file_path : FilePath
            Path to the pCampi ``.h5`` file.
        channel_name : str
            Name of the digital channel to read (as listed in the file's
            ``digital_input/data`` attribute ``channel_names``). Call
            :meth:`get_available_channels` to discover valid values for a given file.
        sampling_rate : float, default: 1000.0
            NIDAQ sampling rate (Hz).
        verbose : bool, default: False
            Whether to print status messages.
        """
        self.verbose = verbose
        self._sampling_rate = float(sampling_rate)
        self._channel_name = channel_name
        super().__init__(
            file_path=file_path, channel_name=channel_name, sampling_rate=sampling_rate
        )
        self._load_data()

    @classmethod
    def get_available_channels(cls, file_path: FilePath) -> list[str]:
        """Return the digital channel names available in a pCampi ``.h5`` file.

        Parameters
        ----------
        file_path : FilePath
            Path to the pCampi ``.h5`` file.

        Returns
        -------
        list[str]
            Channel names in column order (matching ``digital_input/data`` columns).
        """
        with h5py.File(file_path, "r") as f:
            chan_names_raw = f["digital_input/data"].attrs.get("channel_names", "")
        return [name.strip() for name in chan_names_raw.split(",") if name.strip()]

    def _load_data(self):
        with h5py.File(self.source_data["file_path"], "r") as f:
            dataset = f["digital_input/data"]
            channel_names = [
                name.strip()
                for name in dataset.attrs.get("channel_names", "").split(",")
            ]
            if self._channel_name not in channel_names:
                raise ValueError(
                    f"Channel {self._channel_name!r} not found in "
                    f"{self.source_data['file_path']}. Available channels: {channel_names}"
                )
            channel_index = channel_names.index(self._channel_name)
            self._data = dataset[:, channel_index]

    def get_digital_data(self) -> tuple[np.ndarray, float]:
        """Return the raw digital input array for this channel and its sampling rate."""
        return self._data, self._sampling_rate

    def has_meaningful_signal(self) -> bool:
        """Return False if this channel never changes value (e.g. stuck at zero)."""
        return bool(np.any(self._data != self._data[0]))

    def get_metadata(self) -> DeepDict:
        metadata = super().get_metadata()
        # Extract session start time from filename: YYYYMMDD_HHMMSS_M{id}.h5
        fname = Path(self.source_data["file_path"]).name
        m = _FILENAME_PATTERN.match(fname)
        if m:
            try:
                metadata["NWBFile"]["session_start_time"] = datetime.strptime(
                    m.group(1), "%y%m%d_%H%M%S"
                )
            except ValueError:
                pass
        return metadata

    def add_to_nwbfile(
        self,
        nwbfile: NWBFile,
        metadata: dict,
        stub_test: bool = False,
    ) -> None:
        if not self.has_meaningful_signal():
            warnings.warn(
                f"pCampi channel {self._channel_name!r} in "
                f"{self.source_data['file_path']} never changes value (constant "
                f"{self._data[0]}) -- skipping, not writing to the NWB file."
            )
            return

        n_stubs = int(self._sampling_rate * 10)  # first 10 seconds in stub mode
        n = n_stubs if stub_test else len(self._data)

        series = TimeSeries(
            name=f"SyncTTL_{self._channel_name}",
            description=(
                f"pCampi synchronization TTL channel: {self._channel_name}. "
                "Recorded at 1 kHz by LabVIEW NIDAQ."
            ),
            data=self._data[:n].astype(np.int16),
            rate=self._sampling_rate,
            starting_time=0.0,
            unit="a.u.",
            resolution=-1.0,
        )
        nwbfile.add_acquisition(series)
