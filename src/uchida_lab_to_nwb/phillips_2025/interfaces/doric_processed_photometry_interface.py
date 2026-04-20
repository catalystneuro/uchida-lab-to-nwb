"""Interface for lab-processed dF/F photometry data (interpolated_campy_and_doric_data.mat)."""
from pathlib import Path

import numpy as np
import scipy.io as sio
from pydantic import FilePath
from pynwb.file import NWBFile

from neuroconv.basedatainterface import BaseDataInterface
from neuroconv.tools.nwb_helpers import get_module
from neuroconv.utils import DeepDict


class DoricProcessedPhotometryInterface(BaseDataInterface):
    """Interface for lab-processed fiber photometry dF/F signals.

    Reads ``interpolated_campy_and_doric_data.mat`` produced by the Uchida lab's
    MATLAB preprocessing pipeline. Signals have been demodulated, baseline-corrected,
    and interpolated to the video frame rate (~50 Hz).

    This is a lab-specific derivative of the raw Doric data. Raw acquisition is
    handled by ``DoricFiberPhotometryInterface``, which must run first (it creates
    the ``fiber_photometry`` lab_meta_data and ``FiberPhotometryTable``).

    Timestamps are replaced with pCampi-aligned video frame times by
    ``Phillips2025NWBConverter.temporally_align_data_interfaces()``.
    """

    keywords = ["fiber photometry", "dF/F", "fluorescence", "processed"]

    def __init__(
        self,
        file_path: FilePath,
        frametimes_file_path: FilePath,
        verbose: bool = False,
    ):
        self.verbose = verbose
        super().__init__(file_path=file_path, frametimes_file_path=frametimes_file_path)
        frametimes = np.load(str(frametimes_file_path))  # (2, n_frames)
        self._timestamps = frametimes[1]  # row 1 = elapsed seconds from session start

    def set_aligned_timestamps(self, timestamps: np.ndarray) -> None:
        self._timestamps = timestamps

    def get_metadata(self) -> DeepDict:
        return super().get_metadata()

    def add_to_nwbfile(
        self,
        nwbfile: NWBFile,
        metadata: dict,
        stub_test: bool = False,
    ) -> None:
        from ndx_fiber_photometry import FiberPhotometryResponseSeries

        mat = sio.loadmat(
            self.source_data["file_path"],
            squeeze_me=True,
            struct_as_record=False,
        )

        n_frames = len(self._timestamps)
        n_stubs = 100
        timestamps = self._timestamps[:n_stubs] if stub_test else self._timestamps

        # FiberPhotometryTable is created by DoricFiberPhotometryInterface, which runs first.
        # Processed signals reference table row 0 as a placeholder until Hannah confirms
        # the exact indicator/ROI mapping for each processed signal.
        fp_table = nwbfile.lab_meta_data["fiber_photometry"].fiber_photometry_table

        ophys = get_module(nwbfile, "ophys", "Processed optical physiology data")

        def _add_series(mat_key, description):
            if mat_key not in mat or np.asarray(mat[mat_key]).size == 0:
                return
            data = mat[mat_key].astype(np.float32)[:n_frames]
            if stub_test:
                data = data[:n_stubs]
            region = fp_table.create_fiber_photometry_table_region(
                region=[0],  # TODO: update per-signal once ROI mapping is confirmed with Hannah
                description=f"Processed signal {mat_key}; exact ROI TBD.",
            )
            ophys.add(
                FiberPhotometryResponseSeries(
                    name=mat_key,
                    description=description,
                    data=data,
                    timestamps=timestamps,
                    unit="F",
                    fiber_photometry_table_region=region,
                )
            )

        _add_series(
            "dff_resG",
            "dF/F for green channel 1, baseline-corrected and interpolated to video rate.",
        )
        _add_series(
            "dff_resG2",
            "dF/F for green channel 2, baseline-corrected and interpolated to video rate.",
        )
        _add_series("rawG", "Raw green fluorescence (EXC1 channel), interpolated to video rate.")
        _add_series(
            "rawGR",
            "Raw green reference fluorescence (EXC2 isosbestic channel), interpolated to video rate.",
        )
        _add_series("rawR", "Raw red fluorescence, interpolated to video rate.")
        _add_series("rawTd", "Raw Td-Tomato / reference channel, interpolated to video rate.")
        _add_series("fit_baseG", "Fitted photobleaching baseline for green channel 1.")
        _add_series("fit_baseG2", "Fitted photobleaching baseline for green channel 2.")
