"""Empirical dry run: insert an UNMODIFIED, already-published DANDI:001935 NWB file and
see exactly what succeeds/fails against the draft common_photometry schema
(LorenFrankLab/spyglass PR #1637, branch feature/fiber-photometry-ingestion).

This deliberately does NOT change the NWB file first -- the point is to observe real
behavior instead of guessing from source reading. Run inside the `spyglass-photometry`
WSL env (spyglass installed from the PR branch; the `spyglass` env stays untouched):

    cd /mnt/c/Users/algab/CatalystNeuro/uchida-lab-to-nwb/spyglass
    /home/algab/.conda/envs/spyglass-photometry/bin/python dry_run_insertion.py
    /home/algab/.conda/envs/spyglass-photometry/bin/python dry_run_insertion.py <file.nwb>

Scope: fiber photometry only. Tables for other modalities (pose, video, ...) are printed
at the end for information but are not chased.
"""

import sys
import traceback
from pathlib import Path

import datajoint as dj

CONF = Path(__file__).with_name("dj_local_conf.json")
DEFAULT_NWB_FILE_NAME = "sub-M4_ses-day-1-lone_image.nwb"

dj.config.load(str(CONF))  # BEFORE any spyglass import
dj.conn(use_tls=False)

import spyglass.common as sgc  # noqa: E402
import spyglass.data_import as sgi  # noqa: E402
from spyglass.common.common_usage import InsertError  # noqa: E402
from spyglass.settings import raw_dir  # noqa: E402
from spyglass.utils.nwb_helper_fn import get_nwb_copy_filename  # noqa: E402

from ingest_shims import install_hemisphere_shim  # noqa: E402

# Gap found by the first dry run (see ingest_shims.py): hemisphere='unknown' is rejected by
# the enum('left','right') column. Comment this out to reproduce the raw failure.
install_hemisphere_shim()

PHOTOMETRY_DEVICE_TABLES = (
    sgc.Indicator,
    sgc.ExcitationSource,
    sgc.Photodetector,
    sgc.DichroicMirror,
    sgc.OpticalFilter,
    sgc.OpticalFiber,
)


def section(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


def main() -> None:
    nwb_file_name = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_NWB_FILE_NAME
    nwbfile_path = Path(raw_dir) / nwb_file_name
    if not nwbfile_path.exists():
        raise FileNotFoundError(f"Expected NWB file at {nwbfile_path}")

    copy_name = get_nwb_copy_filename(nwb_file_name)
    copy_dict = {"nwb_file_name": copy_name}

    # Clean up any partial run from before. Nwbfile is keyed on the COPY filename
    # (stem + "_.nwb"), not the original -- using the original name here silently
    # matches nothing, insert_sessions() then warns "already in Nwbfile table" and
    # skips, leaving Session at 0 rows with no error (a documented Spyglass gotcha).
    entry = sgc.Nwbfile() & copy_dict
    if entry:
        section("Cleaning up existing Nwbfile entry from a previous run")
        entry.delete(safemode=False)

    section(f"STEP 1: sgi.insert_sessions() -- UNMODIFIED file, as-is: {nwb_file_name}")
    try:
        sgi.insert_sessions(str(nwbfile_path), rollback_on_fail=True, raise_err=True)
        print("insert_sessions() completed with no exception.")
    except Exception as exc:  # noqa: BLE001 -- we want to see and report everything
        print(f"insert_sessions() RAISED: {type(exc).__name__}: {exc}")
        traceback.print_exc()

    section("STEP 2: what actually populated (this file)")
    for table in (sgc.Nwbfile, sgc.Session, sgc.IntervalList):
        print(f"{table.__name__:<32} {len(table() & copy_dict)} row(s)")
    print(f"{'Subject (whole DB)':<32} {len(sgc.Subject())} row(s)")

    print("\n-- photometry device catalog (shared across sessions; whole-table counts) --")
    for table in PHOTOMETRY_DEVICE_TABLES:
        print(f"{table.__name__:<32} {len(table())} row(s)")
    print(f"{'BrainRegion':<32} {len(sgc.BrainRegion())} row(s)")

    print("\n-- photometry, session-specific (this file) --")
    cfg = sgc.FiberPhotometryConfig() & copy_dict
    rs = sgc.FiberPhotometryResponseSeries() & copy_dict
    fib = sgc.FiberPhotometryResponseSeries.Fiber() & copy_dict
    print(f"{'FiberPhotometryConfig':<32} {len(cfg)} row(s)")
    print(f"{'FiberPhotometryResponseSeries':<32} {len(rs)} row(s)")
    print(f"{'FiberPhotometryResponseSeries.Fiber':<32} {len(fib)} row(s)")

    section("STEP 3: InsertError log for this file (errors swallowed by non-raising paths)")
    errs = InsertError() & copy_dict
    print(f"InsertError rows: {len(errs)}")
    if errs:
        print(errs)

    if not (sgc.Session() & copy_dict):
        print("\nSession did not populate -- stopping before read-back.")
        return

    section("STEP 4: table contents")
    print(cfg.proj(
        "fiber_photometry_name", "indicator_name", "excitation_source_name",
        "photodetector_name", "optical_fiber_name", "region_id",
        "excitation_wavelength_in_nm", "emission_wavelength_in_nm",
        "hemisphere", "ap_location", "ml_location", "dv_location",
    ))
    print(rs)
    print(fib)

    section("STEP 5: read-back sanity check via Spyglass accessor")
    for key in rs.fetch("KEY"):
        try:
            df = (sgc.FiberPhotometryResponseSeries() & key).fetch1_dataframe()
            name = (sgc.FiberPhotometryResponseSeries() & key).fetch1("name")
            print(f"  {name!r}: shape={df.shape}, columns={list(df.columns)}")
            print(f"    t[0]={df.index[0]:.4f}  t[-1]={df.index[-1]:.4f}")
        except Exception as exc:  # noqa: BLE001
            print(f"  read-back FAILED for {key}: {type(exc).__name__}: {exc}")
            traceback.print_exc()

    section("DRY RUN DONE")


if __name__ == "__main__":
    main()
