"""Primary NWBConverter class for the Uchida Lab phillips_2025 conversion."""

import numpy as np
from neuroconv import NWBConverter
from neuroconv.converters import DANNCEConverter
from neuroconv.datainterfaces import DoricFiberPhotometryInterface
from neuroconv.tools.signal_processing import (
    get_falling_frames_from_ttl,
    get_rising_frames_from_ttl,
)

from uchida_lab_to_nwb.phillips_2025.interfaces import (
    PCampiSyncInterface,
    ProcessedFiberPhotometryInterface,
)

# Interfaces whose native timestamps are on the Doric BBC300 clock (raw fiber photometry) or a
# nominal clock derived from it (processed/interpolated photometry) -- see
# temporally_align_data_interfaces().
_DORIC_ALIGNED_INTERFACE_KEYS = (
    "DoricControl",
    "DoricDopamineSignal",
    "InterpolatedFPControlSignal",
    "InterpolatedFPDopamineSignal",
)

DORIC_SYNC_STREAM_NAME = "BBC300_Signals_Series0001_DigitalIO_DigitalCh1"


def drop_spurious_leading_edges(edge_times: np.ndarray) -> np.ndarray:
    """Drop leading edges whose spacing to the next edge is far from the train's nominal ISI.

    Used to find the first edge of the *regular* ~50 Hz train (e.g. for DANNCE alignment, anchored
    to ``campy_trigger``'s first real rising edge) -- distinct from the start-of-recording marker
    pulse itself, whose first falling edge ``temporally_align_data_interfaces()`` reads directly
    (via ``get_falling_frames_from_ttl``) to compute the pCampi<->Doric offset.
    """
    edge_times = np.asarray(edge_times)
    if len(edge_times) < 2:
        return edge_times
    nominal_isi = np.median(np.diff(edge_times))
    clean = edge_times
    while len(clean) > 1 and abs(clean[1] - clean[0] - nominal_isi) > nominal_isi:
        clean = clean[1:]
    return clean


class Phillips2025NWBConverter(NWBConverter):
    """Primary conversion class for the Uchida Lab SFARI ARC dataset.

    Data streams:
    - Doric{Control,DopamineSignal}: raw fiber photometry from Doric BBC300 (.doric), one
      ``DoricFiberPhotometryInterface`` per channel (2 total). Each writes a single
      ``FiberPhotometryResponseSeries`` whose 2 columns are the NAc and TS ROIs (column-stacked
      via a 2-element ``stream_names`` list), sharing one ``FiberPhotometryTable``. Keys use
      functional roles rather than raw hardware channel names: EXC1 -> control (tdTomato),
      EXC2 -> dopamine_signal (GRABDA3m); ROI01 -> NAc, ROI02 -> TS.
    - Processed{Control,DopamineSignal}: lab-processed fiber photometry, one
      ``ProcessedFiberPhotometryInterface`` per channel (interpolated_campy_and_doric.mat).
      Raw ROI fluorescence (not dF/F); written to processing/ophys, reusing the
      FiberPhotometryTable created by the raw Doric interfaces.
    - PCampiSync{CampyTrigger,RbfmcFrames}: pCampi LabVIEW TTL synchronization pulses (.h5), one
      ``PCampiSyncInterface`` per digital channel (see ``interfaces/pcampi_sync_interface.py``;
      ``PCampiSyncInterface.get_available_channels()`` discovers the channel names in a given
      file). ``campy_trigger`` also defines the NWB time base (its clock is what
      ``session_start_time`` is parsed from, and what every other stream is aligned to).
    - DANNCE: 3D pose estimation (save_data_AVG0.mat) combined with the 6-camera behavioral
      video (.mp4 per camera, external link) via ``DANNCEConverter``, which links each camera's
      source video and calibrated Device (from calibration/calibration.json) automatically.

    Temporal alignment: ``campy_trigger`` (pCampi/h5) and ``DigitalCh1`` (Doric/.doric, "DIO BNC |
    Ch.1") carry the same physical TTL pulse train on two independent 1 kHz clocks (see
    ``documentation/explore_sync_signals.py``). ``temporally_align_data_interfaces()``:

    - Reads ``DigitalCh1``'s raw trace directly off the already-instantiated ``DoricControl``
      interface (``DoricFiberPhotometryInterface._get_stream_data()``/``_get_stream_timestamps()``
      with ``stream_name=DORIC_SYNC_STREAM_NAME``) and ``campy_trigger``'s raw trace via
      ``PCampiSyncInterface.get_digital_data()``. Edge detection on both uses neuroconv's
      ``get_falling_frames_from_ttl``/``get_rising_frames_from_ttl``
      (``neuroconv.tools.signal_processing``). Each side's very
      first falling edge is the same physical event -- a start-of-recording marker pulse both
      systems emit once before their regular ~50 Hz train begins -- so subtracting the two directly
      gives a single scalar offset (seconds), applied via ``set_aligned_starting_time()`` to every
      Doric-photometry-derived interface (``DoricControl``, ``DoricDopamineSignal``,
      ``InterpolatedFPControlSignal``, ``InterpolatedFPDopamineSignal``).
    - Anchors ``DANNCE`` (pose + all 6 videos, which share one native "elapsed seconds since
      recording start" clock from each camera's ``frametimes.npy``) via
      ``set_aligned_starting_time()`` to the first non-spurious **rising** edge of the pCampi
      ``campy_trigger`` train (``drop_spurious_leading_edges()`` applied to
      ``get_rising_frames_from_ttl()`` output, to skip past the marker pulse and land on the first
      real camera-trigger pulse) -- the pCampi-clock time of that first real trigger. This is
      looped over every sub-interface of the ``DANNCEConverter``
      (``dannce.data_interface_objects.values()``), so pose and all 6 videos stay mutually
      synchronized after the shift.
    """

    # DANNCE must run first: NWBConverter.add_to_nwbfile() iterates data_interface_objects in this
    # dict's order, and DoricFiberPhotometryInterface.add_to_nwbfile() calls neuroconv's
    # add_fiber_photometry_devices(), which (as of neuroconv#<ISSUE_NUMBER>) blindly creates a plain
    # Device for *every* entry in the shared metadata["Devices"] registry -- including DANNCE's
    # Camera1..6 -- not just the fiber-photometry-owned ones. Device creation is idempotent on name
    # (an existing device is returned unchanged), so running DANNCE first lets it create the real
    # ndx_pose.CalibratedCamera Devices before add_fiber_photometry_devices() gets a chance to shadow
    # them with plain Devices. Remove this ordering requirement once the upstream bug is fixed.
    data_interface_classes = dict(
        DANNCE=DANNCEConverter,
        DoricControl=DoricFiberPhotometryInterface,
        DoricDopamineSignal=DoricFiberPhotometryInterface,
        InterpolatedFPControlSignal=ProcessedFiberPhotometryInterface,
        InterpolatedFPDopamineSignal=ProcessedFiberPhotometryInterface,
        PCampiSyncCampyTrigger=PCampiSyncInterface,
        PCampiSyncRbfmcFrames=PCampiSyncInterface,
    )

    def temporally_align_data_interfaces(
        self, metadata: dict | None = None, conversion_options: dict | None = None
    ):
        campy_trigger = self.data_interface_objects.get("PCampiSyncCampyTrigger")
        doric_control = self.data_interface_objects.get("DoricControl")
        if campy_trigger is None or doric_control is None:
            return  # cannot align without both halves of the sync pulse train

        doric_digital_ch1_data = doric_control._get_stream_data(
            stream_name=DORIC_SYNC_STREAM_NAME
        )
        doric_digital_ch1_time = doric_control._get_stream_timestamps(
            stream_name=DORIC_SYNC_STREAM_NAME
        )
        doric_ttl_falling_edges = get_falling_frames_from_ttl(doric_digital_ch1_data)
        first_doric_ttl_falling_edge_timestamp = doric_digital_ch1_time[
            doric_ttl_falling_edges[0]
        ]

        pcampi_data, pcampi_sampling_freq = campy_trigger.get_digital_data()
        pcampi_falling_edges = get_falling_frames_from_ttl(pcampi_data)
        first_pcampi_falling_edge_timestamp = (
            pcampi_falling_edges[0] / pcampi_sampling_freq
        )

        doric_to_pcampi_offset = float(
            first_pcampi_falling_edge_timestamp - first_doric_ttl_falling_edge_timestamp
        )

        for key in _DORIC_ALIGNED_INTERFACE_KEYS:
            interface = self.data_interface_objects.get(key)
            if interface is not None:
                interface.set_aligned_starting_time(doric_to_pcampi_offset)

        dannce = self.data_interface_objects.get("DANNCE")
        if dannce is not None:
            pcampi_rising_edge_times = (
                get_rising_frames_from_ttl(pcampi_data) / pcampi_sampling_freq
            )
            first_real_rising_edge = drop_spurious_leading_edges(
                pcampi_rising_edge_times
            )[0]
            for sub_interface in dannce.data_interface_objects.values():
                sub_interface.set_aligned_starting_time(first_real_rising_edge)
