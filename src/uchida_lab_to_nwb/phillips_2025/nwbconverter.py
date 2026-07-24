"""Primary NWBConverter class for the Uchida Lab phillips_2025 conversion."""

from neuroconv import NWBConverter
from neuroconv.converters import DANNCEConverter
from neuroconv.datainterfaces import DoricFiberPhotometryInterface

from uchida_lab_to_nwb.phillips_2025.interfaces import (
    PCampiSyncInterface,
    ProcessedFiberPhotometryInterface,
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
      file).
    - DANNCE: 3D pose estimation (save_data_AVG0.mat) combined with the 6-camera behavioral
      video (.mp4 per camera, external link) via ``DANNCEConverter``, which links each camera's
      source video and calibrated Device (from calibration/calibration.json) automatically.

    Temporal alignment: **not yet implemented.** Each interface currently writes timestamps on
    its own native/nominal clock (Doric raw photometry: Doric's own clock; processed photometry
    and DANNCE/video: nominal regular timestamps from a configured sampling rate). Cross-stream
    alignment to a common reference clock is a known open problem -- see conversion_notes.md.
    """

    data_interface_classes = dict(
        DoricControl=DoricFiberPhotometryInterface,
        DoricDopamineSignal=DoricFiberPhotometryInterface,
        ProcessedControl=ProcessedFiberPhotometryInterface,
        ProcessedDopamineSignal=ProcessedFiberPhotometryInterface,
        PCampiSyncCampyTrigger=PCampiSyncInterface,
        PCampiSyncRbfmcFrames=PCampiSyncInterface,
        DANNCE=DANNCEConverter,
    )

    def temporally_align_data_interfaces(
        self, metadata: dict | None = None, conversion_options: dict | None = None
    ):
        pass
