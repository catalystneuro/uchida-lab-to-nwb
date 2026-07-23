"""Primary NWBConverter class for the Uchida Lab phillips_2025 conversion."""

import numpy as np
from neuroconv import NWBConverter
from neuroconv.converters import DANNCEConverter
from neuroconv.datainterfaces import DoricFiberPhotometryInterface
from scipy.interpolate import interp1d

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
      Raw ROI fluorescence (not dF/F) resampled to the video frame rate; written to
      processing/ophys, reusing the FiberPhotometryTable created by the raw Doric interfaces.
    - PCampiSync: pCampi LabVIEW TTL synchronization pulses (.h5)
    - DANNCE: 3D pose estimation (save_data_AVG0.mat) combined with the 6-camera behavioral
      video (.mp4 per camera, external link) via ``DANNCEConverter``, which links each camera's
      source video and calibrated Device (from calibration/calibration.json) automatically.

    Temporal alignment (pCampi clock as reference):
    - Video timestamps: from campy_trigger rising edges in pCampi H5
    - Doric timestamps: interpolated from Doric DigitalIO/Camera1 ↔ pCampi rbfmc_frames
    - Processed dF/F: same as video (interpolated to video frame rate)
    - DANNCE: indexed into video timestamps via sampleID
    - pCampi TTL: native (defines t=0)
    """

    data_interface_classes = dict(
        DoricControl=DoricFiberPhotometryInterface,
        DoricDopamineSignal=DoricFiberPhotometryInterface,
        ProcessedControl=ProcessedFiberPhotometryInterface,
        ProcessedDopamineSignal=ProcessedFiberPhotometryInterface,
        PCampiSync=PCampiSyncInterface,
        DANNCE=DANNCEConverter,
    )

    def temporally_align_data_interfaces(self, metadata=None, conversion_options=None):
        """Align all data streams to the pCampi reference clock.

        Strategy
        --------
        1. Extract campy_trigger rising edges from the pCampi H5 → video frame times.
        2. Extract rbfmc_frames rising edges from the pCampi H5 → Doric pulse times in pCampi clock.
        3. Extract Doric Camera1 DigitalIO rising edges → same pulses in Doric clock.
        4. Build a Doric→pCampi interpolation and apply to photometry timestamps.
        5. Set video and DANNCE timestamps from campy_trigger rising edges.
        6. Set processed-photometry timestamps to match video frames (already interpolated).
        """
        if "PCampiSync" not in self.data_interface_objects:
            return

        pcampi = self.data_interface_objects["PCampiSync"]

        # ── Step 1 & 2: Extract pulse times from pCampi ──────────────────────
        campy_frame_times = pcampi.get_campy_trigger_rising_edges()
        doric_times_pcampi = pcampi.get_doric_frame_rising_edges()

        # ── Step 3 & 4: Align Doric clock to pCampi clock ────────────────────
        # Each channel is its own DoricFiberPhotometryInterface instance, but both read from
        # the same .doric file and so discover the same full set of streams (including the
        # Camera1 DigitalIO sync pulse, which neither owns as one of its own stream_names) --
        # either one can be used to look up that shared sync stream.
        doric_interfaces = [
            interface
            for interface in self.data_interface_objects.values()
            if isinstance(interface, DoricFiberPhotometryInterface)
        ]
        if doric_interfaces:
            reference_doric = doric_interfaces[0]
            sync_stream = "BBC300_Signals_Series0001_DigitalIO_Camera1"
            cam1_data = reference_doric._get_stream_data(stream_name=sync_stream)
            cam1_time = reference_doric._get_stream_timestamps(stream_name=sync_stream)
            edges = np.where(np.diff((cam1_data > 0.5).astype(np.int8)) > 0)[0]
            doric_times_doric = cam1_time[edges]

            n = min(len(doric_times_doric), len(doric_times_pcampi))
            if n >= 2:
                doric_to_pcampi = interp1d(
                    doric_times_doric[:n],
                    doric_times_pcampi[:n],
                    kind="linear",
                    fill_value="extrapolate",
                )
                for doric in doric_interfaces:
                    doric.set_aligned_timestamps(doric_to_pcampi(doric.get_original_timestamps()))

        # ── Step 5 & 5b: Align video cameras and DANNCE to campy_trigger ─────
        # DANNCEConverter wraps one DANNCEInterface (key "DANNCE") and one
        # ExternalVideoInterface per camera (keys "VideoCamera1".."VideoCamera6") in its own
        # data_interface_objects. Both load their own timestamps at construction time
        # (frametimes.npy directly); here we replace them with the pCampi-aligned
        # campy_trigger times for consistency across all streams.
        n_frames = len(campy_frame_times)
        dannce_converter = self.data_interface_objects.get("DANNCE")
        if dannce_converter is not None:
            for interface_name, sub_interface in dannce_converter.data_interface_objects.items():
                if interface_name.startswith("Video"):
                    # ExternalVideoInterface expects a list-of-arrays, one per video file
                    sub_interface.set_aligned_timestamps([campy_frame_times])
                else:
                    # DANNCEInterface: reindex campy_trigger times via each prediction's sampleID
                    sample_ids = sub_interface._sample_id.astype(int)  # 0-based frame indices
                    # Guard against frame indices beyond the trigger count
                    valid = sample_ids < n_frames
                    aligned = np.full(len(sample_ids), np.nan)
                    aligned[valid] = campy_frame_times[sample_ids[valid]]
                    sub_interface.set_aligned_timestamps(aligned)

        # ── Step 6: Align processed fiber photometry to video timestamps ────
        for processed_key in ("ProcessedControl", "ProcessedDopamineSignal"):
            proc = self.data_interface_objects.get(processed_key)
            if proc is not None:
                # Processed photometry has ~90,074 samples; trim to video frame count
                proc.set_aligned_timestamps(campy_frame_times[: len(proc._video_timestamps)])
