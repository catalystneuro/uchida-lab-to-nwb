"""Interface for pCampi (LabVIEW) synchronization TTL pulse data (.h5 files)."""
import re
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
    """Interface for pCampi LabVIEW synchronization TTL pulses.

    Reads the H5 file written by pCampi (LabVIEW) containing NIDAQ digital input
    channels recorded at 1 kHz. The file has two channels:
      - Channel 0 (campy_trigger): Camera trigger pulses from the Arduino/campy system.
        Rising edges give the timestamp of each video frame in the pCampi clock.
      - Channel 1 (rbfmc_frames): Doric BBC300 Camera1 output pulses (60 Hz).
        Rising edges are used to align the Doric clock to the pCampi reference clock.

    The pCampi clock defines the NWB time base for this session. All other data streams
    are aligned to it in `Phillips2025NWBConverter.temporally_align_data_interfaces()`.
    """

    keywords = ["synchronization", "TTL", "pCampi", "LabVIEW"]

    def __init__(
        self,
        file_path: FilePath,
        sampling_rate: float = _DEFAULT_SAMPLING_RATE,
        verbose: bool = False,
    ):
        self.verbose = verbose
        self._sampling_rate = float(sampling_rate)
        super().__init__(file_path=file_path, sampling_rate=sampling_rate)
        self._load_data()

    def _load_data(self):
        with h5py.File(self.source_data["file_path"], "r") as f:
            self._digital_data = f["digital_input/data"][:]  # (N, 2) int16
            chan_names = f["digital_input/data"].attrs.get("channel_names", "")
        self._channel_names = [c.strip() for c in chan_names.split(",")]

    def get_digital_data(self) -> tuple[np.ndarray, float]:
        """Return the raw digital input array and its sampling rate."""
        return self._digital_data, self._sampling_rate

    def get_campy_trigger_rising_edges(self) -> np.ndarray:
        """Return timestamps (seconds) of campy_trigger rising edges (pCampi clock)."""
        ch = self._digital_data[:, 0]
        edges = np.where(np.diff((ch > 0).astype(np.int8)) > 0)[0]
        return (edges + 1) / self._sampling_rate

    def get_doric_frame_rising_edges(self) -> np.ndarray:
        """Return timestamps (seconds) of Doric rbfmc_frames rising edges (pCampi clock)."""
        ch = self._digital_data[:, 1]
        edges = np.where(np.diff((ch > 0).astype(np.int8)) > 0)[0]
        return (edges + 1) / self._sampling_rate

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
        n_stubs = int(self._sampling_rate * 10)  # first 10 seconds in stub mode
        n = n_stubs if stub_test else len(self._digital_data)

        for ch_idx, ch_name in enumerate(self._channel_names):
            data = self._digital_data[:n, ch_idx].astype(np.int16)
            series = TimeSeries(
                name=f"SyncTTL_{ch_name}",
                description=(
                    f"pCampi synchronization TTL channel: {ch_name}. "
                    "Recorded at 1 kHz by LabVIEW NIDAQ. "
                    + (
                        "Rising edges mark video frame capture times."
                        if "campy" in ch_name
                        else "Rising edges are Doric BBC300 Camera1 output pulses (60 Hz), "
                        "used to align the Doric clock to the pCampi reference clock."
                    )
                ),
                data=data,
                rate=self._sampling_rate,
                starting_time=0.0,
                unit="a.u.",
                resolution=-1.0,
            )
            nwbfile.add_acquisition(series)
