"""One-off: clear DB state left by the earlier sgi.insert_sessions() full-pipeline probe
run against sub-M4_ses-day-1-lone.nwb, so insert_fiber_photometry.py's report reflects
only what that scoped script itself does (not leftovers from the broader probe, including
its ImportedPose InsertError log row, which the scoped script never touches)."""

from pathlib import Path

import datajoint as dj

CONF = Path(__file__).with_name("dj_local_conf.json")
dj.config.load(str(CONF))
dj.conn(use_tls=False)

from spyglass.common.common_nwbfile import Nwbfile  # noqa: E402
from spyglass.common.common_usage import InsertError  # noqa: E402
from spyglass.utils.nwb_helper_fn import get_nwb_copy_filename  # noqa: E402

copy_name = get_nwb_copy_filename("sub-M4_ses-day-1-lone.nwb")
copy_dict = {"nwb_file_name": copy_name}

entry = Nwbfile() & copy_dict
if entry:
    print(f"Deleting Nwbfile entry (cascades): {copy_dict}")
    entry.delete(safemode=False)

errs = InsertError() & copy_dict
if errs:
    print(f"Deleting {len(errs)} InsertError row(s) for {copy_dict}")
    errs.delete(safemode=False)

print("Cleared.")
