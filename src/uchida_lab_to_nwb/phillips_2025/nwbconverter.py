"""Primary NWBConverter class for the Uchida Lab phillips_2025 conversion."""

import warnings

import numpy as np
from neuroconv import NWBConverter
from neuroconv.converters import DANNCEConverter
from neuroconv.datainterfaces import DoricFiberPhotometryInterface
from neuroconv.tools.signal_processing import (
    get_falling_frames_from_ttl,
    get_rising_frames_from_ttl,
)

from uchida_lab_to_nwb.phillips_2025.interfaces import (
    DffFiberPhotometryInterface,
    PCampiSyncInterface,
    ProcessedFiberPhotometryInterface,
)

# Interfaces whose native timestamps are on the Doric BBC300 clock (raw fiber photometry) or a
# nominal clock derived from it (processed/interpolated/dF/F photometry) -- see
# temporally_align_data_interfaces(). DffDopamineSignal is ad hoc / off by default (see
# interfaces/dff_fiber_photometry_interface.py and convert_session.py's commented-out
# DffDopamineSignal block); listing it here just means that *when* it is instantiated, it gets
# the same clock treatment as InterpolatedFPDopamineSignal, which it's derived from.
_DORIC_ALIGNED_INTERFACE_KEYS = (
    "DoricControl",
    "DoricDopamineSignal",
    "InterpolatedFPControlSignal",
    "InterpolatedFPDopamineSignal",
    "DffDopamineSignal",
)

# Interfaces whose source .mat file is the lab's own MATLAB pipeline's output, resampled onto
# Campy trigger-pulse timestamps -- see _compute_doric_trigger_pulse_timestamps() below.
_PROCESSED_PHOTOMETRY_INTERFACE_KEYS = (
    "InterpolatedFPControlSignal",
    "InterpolatedFPDopamineSignal",
    "DffDopamineSignal",
)

DORIC_SYNC_STREAM_NAME = "BBC300_Signals_Series0001_DigitalIO_DigitalCh1"


def _compute_doric_trigger_pulse_timestamps(
    doric_digital_ch1_data: np.ndarray, doric_digital_ch1_time: np.ndarray
) -> np.ndarray:
    """Rising-edge timestamps of the Doric-side Campy-trigger signal, on Doric's own (unaligned) clock.

    Mirrors the Uchida lab's own MATLAB alignment pipeline ``interpolate_campy_and_doric2_clean.m``:
    it resamples each photometry trace onto these same trigger-pulse timestamps
    -- see conversion_notes.md, Temporal Alignment.

    ``DigitalCh1`` is already high at the very first Doric sample in every session inspected (its first
    *falling* edge, read elsewhere for the pCampi<->Doric offset, is the marker pulse ending). The
    MATLAB script counts that already-high first sample as an implicit extra rising edge
    (``if dio1_triggers(1) == 1 -> campy_re = [1, <real rising edges>]``) and, empirically, keeps it
    rather than dropping it as a spurious startup pulse: prepending it here (with no other filtering)
    exactly reproduces ``interpolated_data``'s sample count in 9 of the 12 sessions in the share
    (verified 2026-09-15); the remaining 3 land on the saved-video-frame grid instead (a separate,
    already-documented lab-side inconsistency -- see conversion_notes.md, Open Questions).
    """
    rising_edges = get_rising_frames_from_ttl(doric_digital_ch1_data)
    if doric_digital_ch1_data[0] == 1:
        rising_edges = np.concatenate(([0], rising_edges))
    return doric_digital_ch1_time[rising_edges]


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
    - DffDopamineSignal: lab-computed dF/F (processed_dff.mat), one ``DffFiberPhotometryInterface``.
      AD HOC / OFF BY DEFAULT -- see that interface's module docstring. Registered here, but
      ``convert_session.py`` never adds it to ``source_data`` -- the code that would (and the
      matching ``fiber_photometry_dff_dopamine_signal`` block in ``fiber_photometry.yaml``) is
      commented out; both need uncommenting to use it.
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
      gives a single scalar offset (seconds), applied via ``set_aligned_starting_time()`` to the raw
      Doric interfaces (``DoricControl``, ``DoricDopamineSignal``, which keep their real per-sample
      Doric-clock timestamps).
    - For the processed/interpolated interfaces (``InterpolatedFPControlSignal``,
      ``InterpolatedFPDopamineSignal``, and ``DffDopamineSignal`` when enabled):
      ``_compute_doric_trigger_pulse_timestamps()`` derives the Doric-side Campy-trigger rising-edge
      timestamps (mirroring the lab's own MATLAB pipeline, ``interpolate_campy_and_doric2_clean.m``,
      shared 2026-09-15), and -- when their count matches the interpolated data's sample count --
      those per-sample timestamps (offset onto the pCampi clock) are written directly via
      ``interface.alignment[metadata_key].set_times()``. In the sessions where the counts don't
      match (the interpolated data landed on the saved-video-frame grid instead -- see
      conversion_notes.md, Temporal Alignment), this falls back to the previous nominal-camera-rate
      ``set_aligned_starting_time()`` shift, with a warning.
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
        # Ad hoc / off by default -- see interfaces/dff_fiber_photometry_interface.py.
        DffDopamineSignal=DffFiberPhotometryInterface,
        PCampiSyncCampyTrigger=PCampiSyncInterface,
        PCampiSyncRbfmcFrames=PCampiSyncInterface,
    )

    def temporally_align_data_interfaces(self, metadata: dict | None = None, conversion_options: dict | None = None):
        campy_trigger = self.data_interface_objects.get("PCampiSyncCampyTrigger")
        doric_control = self.data_interface_objects.get("DoricControl")
        if campy_trigger is None or doric_control is None:
            return  # cannot align without both halves of the sync pulse train

        doric_digital_ch1_data = doric_control._get_stream_data(stream_name=DORIC_SYNC_STREAM_NAME)
        doric_digital_ch1_time = doric_control._get_stream_timestamps(stream_name=DORIC_SYNC_STREAM_NAME)
        doric_ttl_falling_edges = get_falling_frames_from_ttl(doric_digital_ch1_data)
        first_doric_ttl_falling_edge_timestamp = doric_digital_ch1_time[doric_ttl_falling_edges[0]]

        pcampi_data, pcampi_sampling_freq = campy_trigger.get_digital_data()
        pcampi_falling_edges = get_falling_frames_from_ttl(pcampi_data)
        first_pcampi_falling_edge_timestamp = pcampi_falling_edges[0] / pcampi_sampling_freq

        doric_to_pcampi_offset = float(first_pcampi_falling_edge_timestamp - first_doric_ttl_falling_edge_timestamp)

        doric_trigger_pulse_times = _compute_doric_trigger_pulse_timestamps(
            doric_digital_ch1_data, doric_digital_ch1_time
        )

        for key in _DORIC_ALIGNED_INTERFACE_KEYS:
            interface = self.data_interface_objects.get(key)
            if interface is None:
                continue
            if key in _PROCESSED_PHOTOMETRY_INTERFACE_KEYS:
                n_samples = len(interface.get_original_timestamps())
                if n_samples == len(doric_trigger_pulse_times):
                    interface.alignment[interface.metadata_key].set_times(
                        doric_trigger_pulse_times + doric_to_pcampi_offset
                    )
                    continue
                warnings.warn(
                    f"{key}: interpolated_campy_and_doric.mat has {n_samples} samples but "
                    f"{len(doric_trigger_pulse_times)} Doric Campy-trigger pulses were found for "
                    "this session -- falling back to nominal camera-rate timestamps for this "
                    "interface (see conversion_notes.md, Temporal Alignment)."
                )
            interface.set_aligned_starting_time(doric_to_pcampi_offset)

        dannce = self.data_interface_objects.get("DANNCE")
        if dannce is not None:
            pcampi_rising_edge_times = get_rising_frames_from_ttl(pcampi_data) / pcampi_sampling_freq
            first_real_rising_edge = drop_spurious_leading_edges(pcampi_rising_edge_times)[0]
            for sub_interface in dannce.data_interface_objects.values():
                sub_interface.set_aligned_starting_time(first_real_rising_edge)
