"""Helpers for aligning Doric BBC300 and DANNCE/video timestamps to the pCampi reference clock.

The pCampi ``campy_trigger`` channel (h5) and the Doric ``DigitalCh1`` channel (.doric, "DIO BNC
| Ch.1") carry the same physical TTL pulse train, wired from pCampi into the Doric BNC digital
input, but are each sampled by their own independent 1 kHz clock. See
``documentation/explore_sync_signals.py`` for the exploratory analysis this is based on.

Each side's very first square wave is not part of the real ~50 Hz camera-trigger train: it is a
single, longer pulse -- the start-of-recording marker each system emits once before the regular
train begins (``campy_trigger``: rising ~3.2 s in, falling ~3 s later; ``DigitalCh1``: the signal
starts HIGH at t=0 and falls once, ~3 s in, before its own regular train starts ~5-8 s later). That
first falling edge is the same physical event on both sides, so subtracting the two directly gives
the pCampi<->Doric clock offset without needing to match the full pulse trains: doing so here gives
~3.215 s, matching (to within the ~20 ms clock drift over a session) the offset separately measured
by averaging over all ~90,000 matched pulses of the regular train -- see git history of this file
for that alternative approach.
"""

import numpy as np

# The Doric digital line ("DIO BNC | Ch.1") carrying the pCampi campy_trigger pulse train into the
# Doric BBC300, in DoricFiberPhotometryInterface's stream-name convention (the path relative to
# ``DataAcquisition``, with ``/`` replaced by ``_``).
DORIC_SYNC_STREAM_NAME = "BBC300_Signals_Series0001_DigitalIO_DigitalCh1"


def drop_spurious_leading_edges(edge_times: np.ndarray) -> np.ndarray:
    """Drop leading edges whose spacing to the next edge is far from the train's nominal ISI.

    Used to find the first edge of the *regular* ~50 Hz train (e.g. for DANNCE alignment, anchored
    to ``campy_trigger``'s first real rising edge) -- distinct from the start-of-recording marker
    pulse itself, which ``compute_doric_to_pcampi_offset`` below reads directly.
    """
    edge_times = np.asarray(edge_times)
    if len(edge_times) < 2:
        return edge_times
    nominal_isi = np.median(np.diff(edge_times))
    clean = edge_times
    while len(clean) > 1 and abs(clean[1] - clean[0] - nominal_isi) > nominal_isi:
        clean = clean[1:]
    return clean


def first_falling_edge_time(values: np.ndarray, time: np.ndarray, threshold: float = 0.5) -> float:
    """Return the timestamp of the first falling edge in a digital (0/1) trace.

    Parameters
    ----------
    values : numpy.ndarray
        The digital trace.
    time : numpy.ndarray
        Timestamps (seconds), same length as ``values``.
    threshold : float, default: 0.5
        On/off threshold.

    Returns
    -------
    float
        Timestamp of the first sample after the first high-to-low transition.
    """
    binary = (np.asarray(values) > threshold).astype(np.int8)
    edges = np.where(np.diff(binary) < 0)[0]
    if len(edges) == 0:
        raise ValueError("No falling edge found in the given trace.")
    return float(time[edges[0] + 1])


def compute_doric_to_pcampi_offset(
    pcampi_falling_edge_times: np.ndarray,
    doric_digital_ch1_data: np.ndarray,
    doric_digital_ch1_time: np.ndarray,
) -> float:
    """Return the scalar offset (seconds) that converts a Doric-clock timestamp to pCampi-clock time.

    ``pcampi_time ~= doric_time + offset``. Computed from each side's very first falling edge only
    (the shared start-of-recording marker pulse -- see module docstring), not by matching or
    averaging over the regular pulse train.

    Parameters
    ----------
    pcampi_falling_edge_times : numpy.ndarray
        Falling-edge timestamps (seconds) of the pCampi ``campy_trigger`` channel, in the pCampi
        clock. See ``PCampiSyncInterface.get_falling_edges()``.
    doric_digital_ch1_data : numpy.ndarray
        Raw ``DigitalCh1`` trace, in the Doric clock. See
        ``DoricFiberPhotometryInterface._get_stream_data(stream_name=DORIC_SYNC_STREAM_NAME)``.
    doric_digital_ch1_time : numpy.ndarray
        Timestamps (seconds) for ``doric_digital_ch1_data``. See
        ``DoricFiberPhotometryInterface._get_stream_timestamps(stream_name=DORIC_SYNC_STREAM_NAME)``.

    Returns
    -------
    float
        The offset to pass to ``BaseTemporalAlignmentInterface.set_aligned_starting_time()`` for
        any interface whose native timestamps are on the Doric clock.
    """
    doric_first_falling_edge = first_falling_edge_time(
        doric_digital_ch1_data, doric_digital_ch1_time
    )
    return float(pcampi_falling_edge_times[0] - doric_first_falling_edge)
