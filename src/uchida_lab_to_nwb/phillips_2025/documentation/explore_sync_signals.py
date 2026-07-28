"""Exploration script: inspect and compare the pCampi (.h5) and Doric (.doric) sync signals.

PCampiSyncInterface.get_doric_frame_rising_edges() reads the h5 "rbfmc_frames" channel and
finds 0 edges because the signal is flat. Separately, the .doric file's "DigitalCh1"
channel ("DIO BNC | Ch.1", an external BNC digital input) has a pulse count that nearly
matches the h5 "campy_trigger" channel, suggesting DigitalCh1 is actually the same physical
TTL pulse train as campy_trigger, wired from pCampi into the Doric BNC input.

This script loads both files, prints stats for every relevant digital channel, and plots
campy_trigger (h5) and DigitalCh1 (doric) together -- both on their own raw clocks, and
aligned by their first falling edge -- to visually confirm whether they are the same pulse
train. Falling edges (rather than rising edges) are used here as the reference event.

Run with the uchida_lab_to_nwb_env conda environment.
"""
import h5py
import numpy as np
import matplotlib.pyplot as plt

DORIC_PATH = r"H:\Uchida-CN-data-share\Hannah_data\M4-M7\Lone_data\day_1\M4\BBC300_Acq_0093.doric"
H5_PATH = r"H:\Uchida-CN-data-share\Hannah_data\M4-M7\Lone_data\day_1\M4\240624_135840_M4.h5"
H5_SAMPLING_RATE = 1000.0  # Hz, per PCampiSyncInterface


def falling_edges(arr, threshold=0.5):
    binary = (arr > threshold).astype(np.int8)
    return np.where(np.diff(binary) < 0)[0]


def analyze_signal(name, time, values):
    print(f"--- {name} ---")
    print(f"  n_samples   : {len(values)}")
    print(f"  value range : [{values.min()}, {values.max()}]")
    print(f"  unique vals : {np.unique(values)[:10]}")
    edges = falling_edges(values)
    print(f"  falling edges: {len(edges)}")
    if len(edges):
        edge_times = time[edges + 1]
        isis = np.diff(edge_times)
        print(f"  first edge time: {edge_times[0]:.4f} s, last: {edge_times[-1]:.4f} s")
        print(f"  median inter-pulse interval: {np.median(isis):.6f} s "
              f"(~{1 / np.median(isis):.2f} Hz)")
    else:
        print("  ** FLAT SIGNAL: no falling edges found **")
    print()
    return edges


def load_doric_digital(path):
    with h5py.File(path, "r") as f:
        sig_group = "DataAcquisition/BBC300/Signals/Series0001/DigitalIO"
        time = f[f"{sig_group}/Time"][:]
        channels = {ch: f[f"{sig_group}/{ch}"][:] for ch in f[sig_group].keys() if ch != "Time"}
    return time, channels


def load_h5_digital(path, sampling_rate):
    with h5py.File(path, "r") as f:
        digital = f["digital_input/data"]
        data = digital[:]
        chan_names = [c.strip() for c in digital.attrs.get("channel_names", "").split(",")]
    time = np.arange(data.shape[0]) / sampling_rate
    channels = {name: data[:, i] for i, name in enumerate(chan_names)}
    return time, channels


def main():
    print("=== Doric file: DigitalIO channels ===")
    doric_time, doric_channels = load_doric_digital(DORIC_PATH)
    doric_edges = {name: analyze_signal(f"doric/{name}", doric_time, values)
                   for name, values in doric_channels.items()}

    print("=== pCampi h5 file: digital_input channels ===")
    h5_time, h5_channels = load_h5_digital(H5_PATH, H5_SAMPLING_RATE)
    h5_edges = {name: analyze_signal(f"h5/{name}", h5_time, values)
                for name, values in h5_channels.items()}

    campy_edge_times = h5_time[h5_edges["campy_trigger"] + 1]
    digitalch1_edge_times = doric_time[doric_edges["DigitalCh1"] + 1]

    print("=== campy_trigger (h5) vs DigitalCh1 (doric) ===")
    print(f"  n edges: {len(campy_edge_times)} vs {len(digitalch1_edge_times)}")

    # Each signal has one leading falling edge that is NOT part of the regular ~50Hz train,
    # for a different reason on each side:
    #  - campy_trigger has an isolated spurious pulse right at recording start (rising at
    #    ~3.2s, falling at ~6.2s), unrelated to the real train that starts ~5s later.
    #  - DigitalCh1 (doric) starts HIGH at t=0 (recording began mid-pulse), so its first
    #    falling edge is just the end of that leftover initial state, not a real pulse.
    # Drop leading edges whose ISI to the next edge is way off the nominal spacing before
    # doing a pulse-for-pulse comparison.
    def drop_spurious_leading_edges(edge_times, label):
        nominal_isi = np.median(np.diff(edge_times))
        clean = edge_times.copy()
        while len(clean) > 1 and abs(clean[1] - clean[0] - nominal_isi) > nominal_isi:
            print(f"  dropping spurious leading {label} falling edge at t={clean[0]:.4f}s "
                  f"(next edge {clean[1] - clean[0]:.4f}s later, nominal ISI {nominal_isi:.4f}s)")
            clean = clean[1:]
        return clean

    campy_clean = drop_spurious_leading_edges(campy_edge_times, "campy_trigger")
    digitalch1_clean = drop_spurious_leading_edges(digitalch1_edge_times, "DigitalCh1")

    n = min(len(campy_clean), len(digitalch1_clean))
    offset = campy_clean[:n] - digitalch1_clean[:n]
    print(f"  matched pulses: {n}")
    print(f"  clock offset (campy_trigger time - DigitalCh1 time) per matched pulse: "
          f"mean={offset.mean():.4f}s, std={offset.std():.5f}s, "
          f"first={offset[0]:.4f}s, last={offset[-1]:.4f}s")
    print(f"  -> offset drifts by {offset[-1] - offset[0]:+.4f}s over the session "
          f"({(offset[-1] - offset[0]) / (digitalch1_clean[n - 1] - digitalch1_clean[0]) * 1e6:.1f} ppm), "
          "consistent with independent clock crystals on the same physical TTL pulse train.")
    print()

    # ── Plots ────────────────────────────────────────────────────────────────
    fig, axes = plt.subplots(4, 1, figsize=(14, 11))

    # Raw traces on their own native clocks
    ax = axes[0]
    ax.plot(h5_time, h5_channels["campy_trigger"], drawstyle="steps-post",
             label="campy_trigger (h5)", color="tab:blue")
    ax.plot(doric_time, doric_channels["DigitalCh1"], drawstyle="steps-post",
             label="DigitalCh1 (doric)", color="tab:orange", alpha=0.7)
    ax.set_title("Full recording, each signal on its own native clock (t=0 at file start)")
    ax.set_xlabel("time (s)")
    ax.legend()

    # Zoom on first few pulses, native clocks (using the first *clean* falling edge of each
    # signal, i.e. excluding each side's own leading artifact)
    ax = axes[1]
    t0_campy = campy_clean[0]
    t0_doric = digitalch1_clean[0]
    zoom_h5 = (h5_time >= t0_campy - 0.05) & (h5_time <= t0_campy + 1.0)
    zoom_doric = (doric_time >= t0_doric - 0.05) & (doric_time <= t0_doric + 1.0)
    ax.plot(h5_time[zoom_h5], h5_channels["campy_trigger"][zoom_h5], drawstyle="steps-post",
             label="campy_trigger (h5)", color="tab:blue", marker=".")
    ax.plot(doric_time[zoom_doric], doric_channels["DigitalCh1"][zoom_doric], drawstyle="steps-post",
             label="DigitalCh1 (doric)", color="tab:orange", marker=".", alpha=0.7)
    ax.set_title("Zoom: first ~1s of pulses starting at each signal's first falling edge (native clocks)")
    ax.set_xlabel("time (s)")
    ax.legend()

    # Aligned by first falling edge -- overlay to compare pulse-train shape/spacing
    ax = axes[2]
    aligned_h5_time = h5_time - t0_campy
    aligned_doric_time = doric_time - t0_doric
    mask_h5 = (aligned_h5_time >= -0.05) & (aligned_h5_time <= 5.0)
    mask_doric = (aligned_doric_time >= -0.05) & (aligned_doric_time <= 5.0)
    ax.plot(aligned_h5_time[mask_h5], h5_channels["campy_trigger"][mask_h5], drawstyle="steps-post",
             label="campy_trigger (h5, aligned)", color="tab:blue")
    ax.plot(aligned_doric_time[mask_doric], doric_channels["DigitalCh1"][mask_doric], drawstyle="steps-post",
             label="DigitalCh1 (doric, aligned)", color="tab:orange", alpha=0.7)
    ax.set_title("Aligned by first falling edge: first 5s -- do pulses line up?")
    ax.set_xlabel("time since first falling edge (s)")
    ax.legend()

    # Clock offset per matched pulse (campy_trigger time - DigitalCh1 time). A same pulse
    # train recorded on two independent clocks should show a slowly drifting offset, not a
    # noisy/scattered one.
    ax = axes[3]
    ax.plot(digitalch1_clean[:n], offset, color="tab:green")
    ax.set_title(
        f"Clock offset per matched pulse (campy_trigger - DigitalCh1): "
        f"{offset.mean():.4f}s +/- {offset.std():.5f}s, drift {offset[-1] - offset[0]:+.4f}s over session"
    )
    ax.set_xlabel("DigitalCh1 (doric) time (s)")
    ax.set_ylabel("offset (s)")

    fig.suptitle("campy_trigger (pCampi h5) vs DigitalCh1 (Doric BNC input) comparison")
    fig.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
