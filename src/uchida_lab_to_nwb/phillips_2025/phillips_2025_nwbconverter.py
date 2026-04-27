"""Primary NWBConverter class for the Uchida Lab phillips_2025 conversion."""

import numpy as np
from neuroconv import NWBConverter
from neuroconv.datainterfaces import ExternalVideoInterface, SDANNCEInterface
from scipy.interpolate import interp1d

from uchida_lab_to_nwb.phillips_2025.interfaces import (
    DoricFiberPhotometryInterface,
    DoricProcessedPhotometryInterface,
    PCampiSyncInterface,
)

# One ExternalVideoInterface entry per camera
_CAMERA_NAMES = [f"VideoCamera{i}" for i in range(1, 7)]


class Phillips2025NWBConverter(NWBConverter):
    """Primary conversion class for the Uchida Lab SFARI ARC dataset.

    Data streams:
    - DoricPhotometry: raw fiber photometry from Doric BBC300 (.doric)
    - DoricProcessed: lab-processed dF/F traces (interpolated_campy_and_doric_data.mat)
    - PCampiSync: pCampi LabVIEW TTL synchronization pulses (.h5)
    - DANNCE: 3D pose estimation (save_data_AVG0.mat)
    - VideoCamera1–6: 6-camera behavioral video (.mp4 per camera)

    Temporal alignment (pCampi clock as reference):
    - Video timestamps: from campy_trigger rising edges in pCampi H5
    - Doric timestamps: interpolated from Doric DigitalIO/Camera1 ↔ pCampi rbfmc_frames
    - Processed dF/F: same as video (interpolated to video frame rate)
    - DANNCE: indexed into video timestamps via sampleID
    - pCampi TTL: native (defines t=0)
    """

    data_interface_classes = dict(
        DoricPhotometry=DoricFiberPhotometryInterface,
        DoricProcessed=DoricProcessedPhotometryInterface,
        PCampiSync=PCampiSyncInterface,
        DANNCE=SDANNCEInterface,
        VideoCamera1=ExternalVideoInterface,
        VideoCamera2=ExternalVideoInterface,
        VideoCamera3=ExternalVideoInterface,
        VideoCamera4=ExternalVideoInterface,
        VideoCamera5=ExternalVideoInterface,
        VideoCamera6=ExternalVideoInterface,
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
        if "DoricPhotometry" in self.data_interface_objects:
            doric = self.data_interface_objects["DoricPhotometry"]
            doric_times_doric = doric.get_camera_pulse_times()

            n = min(len(doric_times_doric), len(doric_times_pcampi))
            if n >= 2:
                doric_to_pcampi = interp1d(
                    doric_times_doric[:n],
                    doric_times_pcampi[:n],
                    kind="linear",
                    fill_value="extrapolate",
                )
                doric.set_aligned_timestamps(
                    {
                        "CAM1EXC1": doric_to_pcampi(doric._timestamps["CAM1EXC1"]),
                        "CAM1EXC2": doric_to_pcampi(doric._timestamps["CAM1EXC2"]),
                    }
                )

        # ── Step 5: Align video cameras to campy_trigger ─────────────────────
        n_frames = len(campy_frame_times)
        for cam_key in _CAMERA_NAMES:
            if cam_key in self.data_interface_objects:
                video_iface = self.data_interface_objects[cam_key]
                # ExternalVideoInterface expects a list-of-arrays, one per video file
                video_iface.set_aligned_timestamps([campy_frame_times])

        # ── Step 5b: Align DANNCE to video timestamps ─────────────────────────
        # SDANNCEInterface sets its own timestamps from frametimes.npy during __init__;
        # here we replace them with the pCampi-aligned campy_trigger times for consistency.
        if "DANNCE" in self.data_interface_objects:
            dannce = self.data_interface_objects["DANNCE"]
            sample_ids = dannce._sample_id.astype(int)  # 0-based frame indices
            # Guard against frame indices beyond the trigger count
            valid = sample_ids < n_frames
            aligned = np.full(len(sample_ids), np.nan)
            aligned[valid] = campy_frame_times[sample_ids[valid]]
            dannce.set_aligned_timestamps(aligned)

        # ── Step 6: Align processed dF/F to video timestamps ─────────────────
        if "DoricProcessed" in self.data_interface_objects:
            proc = self.data_interface_objects["DoricProcessed"]
            # Processed photometry has ~90,071 samples; trim to video frame count
            proc.set_aligned_timestamps(campy_frame_times[: len(proc._timestamps)])
