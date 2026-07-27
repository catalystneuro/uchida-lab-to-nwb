"""Primary NWBConverter class for the Uchida Lab phillips_2025 conversion."""

from neuroconv import NWBConverter
from neuroconv.converters import DANNCEConverter
from neuroconv.datainterfaces import DoricFiberPhotometryInterface

from uchida_lab_to_nwb.phillips_2025.interfaces import (
    PCampiSyncInterface,
    ProcessedFiberPhotometryInterface,
)
from uchida_lab_to_nwb.phillips_2025.utils.sync_alignment import (
    DORIC_SYNC_STREAM_NAME,
    compute_doric_to_pcampi_offset,
    drop_spurious_leading_edges,
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
    ``documentation/explore_sync_signals.py`` and ``utils/sync_alignment.py``).
    ``temporally_align_data_interfaces()``:
    """

    data_interface_classes = dict(
        DoricControl=DoricFiberPhotometryInterface,
        DoricDopamineSignal=DoricFiberPhotometryInterface,
        InterpolatedFPControlSignal=ProcessedFiberPhotometryInterface,
        InterpolatedFPDopamineSignal=ProcessedFiberPhotometryInterface,
        PCampiSyncCampyTrigger=PCampiSyncInterface,
        PCampiSyncRbfmcFrames=PCampiSyncInterface,
        DANNCE=DANNCEConverter,
    )

    def temporally_align_data_interfaces(
        self, metadata: dict | None = None, conversion_options: dict | None = None
    ):
        campy_trigger = self.data_interface_objects.get("PCampiSyncCampyTrigger")
        doric_control = self.data_interface_objects.get("DoricControl")
        if campy_trigger is None or doric_control is None:
            return  # cannot align without both halves of the sync pulse train

        # Read DigitalCh1's raw trace directly off the already-instantiated DoricControl
        # interface -- no extra interface is instantiated, and nothing extra is written to the
        # NWB file.
        doric_digital_ch1_data = doric_control._get_stream_data(
            stream_name=DORIC_SYNC_STREAM_NAME
        )
        doric_digital_ch1_time = doric_control._get_stream_timestamps(
            stream_name=DORIC_SYNC_STREAM_NAME
        )
        pcampi_falling_edge_times = campy_trigger.get_falling_edges()
        doric_to_pcampi_offset = compute_doric_to_pcampi_offset(
            pcampi_falling_edge_times, doric_digital_ch1_data, doric_digital_ch1_time
        )

        for key in _DORIC_ALIGNED_INTERFACE_KEYS:
            interface = self.data_interface_objects.get(key)
            if interface is not None:
                interface.set_aligned_starting_time(doric_to_pcampi_offset)

        dannce = self.data_interface_objects.get("DANNCE")
        if dannce is not None:
            pcampi_rising_edge_times = campy_trigger.get_rising_edges()
            first_real_rising_edge = drop_spurious_leading_edges(
                pcampi_rising_edge_times
            )[0]
            for sub_interface in dannce.data_interface_objects.values():
                sub_interface.set_aligned_starting_time(first_real_rising_edge)
