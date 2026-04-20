"""Interface for raw Doric BBC300 fiber photometry data (.doric HDF5 files)."""
from copy import deepcopy
from datetime import datetime
from pathlib import Path

import h5py
import numpy as np
from pydantic import FilePath
from pynwb.file import NWBFile

from neuroconv.basedatainterface import BaseDataInterface
from neuroconv.utils import DeepDict, load_dict_from_file

# Doric BBC300 channel layout: 2 excitation channels × 3 ROIs
_EXCITATION_KEYS = ("CAM1EXC1", "CAM1EXC2")
_ROI_KEYS = ("ROI01", "ROI02", "ROI03")
_DORIC_CREATED_FMT = "%a %b %d %H:%M:%S %Y"

# Maps Doric HDF5 excitation key → series name suffix used in fiber_photometry.yaml
_EXC_KEY_TO_SUFFIX = {"CAM1EXC1": "EXC1", "CAM1EXC2": "EXC2"}


def add_fiberphotometry_table(nwbfile: NWBFile, metadata: dict):
    """Add all fiber photometry devices, indicators, and FiberPhotometryTable to nwbfile.

    Reads hardware and indicator metadata from ``metadata["Ophys"]["FiberPhotometry"]``
    and creates NWB objects in order:

    1. ExcitationSources and Photodetectors — added to ``nwbfile.devices``.
    2. OpticalFibers — each with an associated FiberInsertion; duplicates skipped.
    3. FiberPhotometryIndicators.
    4. FiberPhotometryTable — one row per channel, device name strings resolved to objects.
    5. FiberPhotometry lab_meta_data — wraps table and indicators; added to nwbfile.

    Parameters
    ----------
    nwbfile : NWBFile
        The NWB file to populate.
    metadata : dict
        Full metadata dict; fiber photometry section read from
        ``metadata["Ophys"]["FiberPhotometry"]``.

    Returns
    -------
    FiberPhotometryTable
        The newly created table instance (already registered in nwbfile).
    """
    from ndx_fiber_photometry import (
        FiberPhotometry,
        FiberPhotometryIndicators,
        FiberPhotometryTable,
    )
    from ndx_ophys_devices import (
        ExcitationSource,
        FiberInsertion,
        Indicator,
        OpticalFiber,
        Photodetector,
    )

    fp_meta = metadata["Ophys"]["FiberPhotometry"]

    # ── Excitation sources ────────────────────────────────────────────────────
    for exc_meta in fp_meta.get("ExcitationSources", []):
        if exc_meta["name"] not in nwbfile.devices:
            nwbfile.add_device(ExcitationSource(**exc_meta))

    # ── Photodetectors ────────────────────────────────────────────────────────
    for pd_meta in fp_meta.get("Photodetectors", []):
        if pd_meta["name"] not in nwbfile.devices:
            nwbfile.add_device(Photodetector(**pd_meta))

    # ── Optical fibers with FiberInsertion ────────────────────────────────────
    for of_meta in fp_meta.get("OpticalFibers", []):
        if of_meta["name"] not in nwbfile.devices:
            fi_kwargs = of_meta["fiber_insertion"]
            of_kwargs = {k: v for k, v in of_meta.items() if k != "fiber_insertion"}
            nwbfile.add_device(OpticalFiber(fiber_insertion=FiberInsertion(**fi_kwargs), **of_kwargs))

    # ── Indicators ────────────────────────────────────────────────────────────
    indicators_meta = fp_meta.get("FiberPhotometryIndicators", [])
    if not indicators_meta:
        raise ValueError("At least one FiberPhotometryIndicator must be defined in metadata.")
    name_to_indicator = {}
    for ind_meta in indicators_meta:
        ind = Indicator(**ind_meta)
        name_to_indicator[ind.name] = ind
    indicators = FiberPhotometryIndicators(indicators=list(name_to_indicator.values()))

    # ── FiberPhotometryTable ──────────────────────────────────────────────────
    table_meta = fp_meta["FiberPhotometryTable"]
    fp_table = FiberPhotometryTable(
        name=table_meta["name"],
        description=table_meta["description"],
    )

    device_fields = [
        "optical_fiber",
        "excitation_source",
        "photodetector",
        "dichroic_mirror",
        "excitation_filter",
        "emission_filter",
    ]
    for row_meta in table_meta["rows"]:
        row_data = {
            "location": row_meta["location"],
            "excitation_wavelength_in_nm": float(row_meta["excitation_wavelength_in_nm"]),
            "emission_wavelength_in_nm": float(row_meta["emission_wavelength_in_nm"]),
            "indicator": name_to_indicator[row_meta["indicator"]],
        }
        for field in device_fields:
            if field in row_meta:
                row_data[field] = nwbfile.devices[row_meta[field]]
        fp_table.add_row(**row_data)

    fp_obj = FiberPhotometry(
        name="fiber_photometry",
        fiber_photometry_table=fp_table,
        fiber_photometry_indicators=indicators,
    )
    nwbfile.add_lab_meta_data(fp_obj)
    return fp_table


class DoricFiberPhotometryInterface(BaseDataInterface):
    """Interface for raw Doric BBC300 fiber photometry data.

    Reads ROI-averaged fluorescence signals from the `.doric` HDF5 format produced
    by Doric Neuroscience Studio. Writes data to NWB using the ndx-fiber-photometry
    extension, following the metadata-driven pattern from the IBL fiber photometry
    conversion.

    All fiber photometry hardware metadata (excitation sources, photodetector,
    optical fibers, indicator, table rows, and response series) is defined in
    ``_metadata/fiber_photometry.yaml``.

    Timestamps are in the Doric internal clock on construction. They are replaced
    with pCampi-aligned timestamps by
    ``Phillips2025NWBConverter.temporally_align_data_interfaces()`` before writing.
    """

    keywords = ["fiber photometry", "fluorescence", "Doric"]

    def __init__(self, file_path: FilePath, verbose: bool = False):
        self.verbose = verbose
        super().__init__(file_path=file_path)
        self._load_timestamps()

    def _load_timestamps(self):
        """Pre-load per-channel timestamps and Camera1 sync pulses from the Doric file."""
        with h5py.File(self.source_data["file_path"], "r") as f:
            base = "DataAcquisition/BBC300/ROISignals/Series0001"
            self._timestamps = {
                exc: f[f"{base}/{exc}/Time"][:] for exc in _EXCITATION_KEYS
            }
            dio_base = "DataAcquisition/BBC300/Signals/Series0001/DigitalIO"
            cam1_trace = f[f"{dio_base}/Camera1"][:]
            cam1_time = f[f"{dio_base}/Time"][:]

        edges = np.where(np.diff((cam1_trace > 0.5).astype(np.int8)) > 0)[0]
        self._camera_pulse_times = cam1_time[edges]

    def get_camera_pulse_times(self) -> np.ndarray:
        """Return Doric Camera1 pulse rising-edge times (Doric clock, seconds)."""
        return self._camera_pulse_times

    def set_aligned_timestamps(self, aligned_timestamps: dict[str, np.ndarray]) -> None:
        """Replace internal timestamps with pCampi-aligned values.

        Parameters
        ----------
        aligned_timestamps : dict
            Keys "CAM1EXC1" and "CAM1EXC2", values are 1-D arrays in pCampi clock.
        """
        self._timestamps = aligned_timestamps

    def get_metadata(self) -> DeepDict:
        metadata = super().get_metadata()

        # Session start time from Doric file header
        with h5py.File(self.source_data["file_path"], "r") as f:
            created_str = f.attrs.get("Created", "")
        if created_str:
            try:
                metadata["NWBFile"]["session_start_time"] = datetime.strptime(
                    created_str, _DORIC_CREATED_FMT
                )
            except ValueError:
                pass

        # Fiber photometry hardware metadata — single source of truth
        fp_yaml = load_dict_from_file(
            Path(__file__).parent.parent / "_metadata" / "fiber_photometry.yaml"
        )
        metadata.deep_update(fp_yaml)
        return metadata

    def add_to_nwbfile(
        self,
        nwbfile: NWBFile,
        metadata: dict,
        stub_test: bool = False,
    ) -> None:
        from ndx_fiber_photometry import FiberPhotometryResponseSeries

        # Build devices and table (idempotent — skipped if already present)
        if "fiber_photometry" not in nwbfile.lab_meta_data:
            fp_table = add_fiberphotometry_table(nwbfile=nwbfile, metadata=metadata)
        else:
            fp_table = nwbfile.lab_meta_data["fiber_photometry"].fiber_photometry_table

        n_stubs = 100
        all_series_meta = metadata["Ophys"]["FiberPhotometry"].get(
            "FiberPhotometryResponseSeries", []
        )

        with h5py.File(self.source_data["file_path"], "r") as f:
            base = "DataAcquisition/BBC300/ROISignals/Series0001"

            for series_meta in all_series_meta:
                # Resolve which Doric channel this series corresponds to from the name,
                # e.g. "FiberPhotometry_EXC1_ROI01" → CAM1EXC1 / ROI01
                exc_key = next(
                    (ek for ek, suf in _EXC_KEY_TO_SUFFIX.items() if suf in series_meta["name"]),
                    None,
                )
                roi_key = next(
                    (rk for rk in _ROI_KEYS if rk in series_meta["name"]),
                    None,
                )
                if exc_key is None or roi_key is None:
                    continue  # not a raw-channel series — skip

                data = f[f"{base}/{exc_key}/{roi_key}"][:]
                timestamps = self._timestamps[exc_key].copy()

                if stub_test:
                    data = data[:n_stubs]
                    timestamps = timestamps[:n_stubs]

                region = fp_table.create_fiber_photometry_table_region(
                    region=series_meta["fiber_photometry_table_region"],
                    description=series_meta["fiber_photometry_table_region_description"],
                )
                nwbfile.add_acquisition(
                    FiberPhotometryResponseSeries(
                        name=series_meta["name"],
                        description=series_meta["description"],
                        data=data,
                        timestamps=timestamps,
                        unit=series_meta["unit"],
                        fiber_photometry_table_region=region,
                    )
                )
