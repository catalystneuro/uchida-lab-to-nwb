"""One-off probe: does FiberPhotometryConfig/ResponseSeries still populate when an
unrelated, out-of-scope table (ImportedPose) fails during the same insertion batch?

ImportedPose crashes on this file's newer ndx-pose CalibratedCamera-based DANNCE layout
(IndexError: list index out of range -- a per-camera PoseEstimation container has zero
pose_estimation_series). Pose ingestion is explicitly out of scope for this pass; this
probe checks whether that failure is isolated (logged to InsertError, does not block
photometry) when run the way insert_sessions() is normally used (raise_err=False).
"""

from pathlib import Path

import datajoint as dj

CONF = Path(__file__).with_name("dj_local_conf.json")
dj.config.load(str(CONF))
dj.conn(use_tls=False)

import spyglass.common as sgc  # noqa: E402
import spyglass.data_import as sgi  # noqa: E402
from spyglass.common.common_usage import InsertError  # noqa: E402
from spyglass.utils.nwb_helper_fn import get_nwb_copy_filename  # noqa: E402

from ingest_shims import install_hemisphere_shim  # noqa: E402

install_hemisphere_shim()

nwb_file_name = "sub-M4_ses-day-1-lone.nwb"
copy_name = get_nwb_copy_filename(nwb_file_name)
copy_dict = {"nwb_file_name": copy_name}

entry = sgc.Nwbfile() & copy_dict
if entry:
    entry.delete(safemode=False)

sgi.insert_sessions(nwb_file_name, rollback_on_fail=False, raise_err=False)

print("Session:", len(sgc.Session() & copy_dict))
print("InsertError rows for this file:")
for row in (InsertError() & copy_dict).fetch(as_dict=True):
    print(" -", row["table"], "|", str(row["error_message"])[:200])

cfg = sgc.FiberPhotometryConfig() & copy_dict
rs = sgc.FiberPhotometryResponseSeries() & copy_dict
fib = sgc.FiberPhotometryResponseSeries.Fiber() & copy_dict
print("FiberPhotometryConfig:", len(cfg))
print("FiberPhotometryResponseSeries:", len(rs))
print("FiberPhotometryResponseSeries.Fiber:", len(fib))
if cfg:
    print(cfg)
if rs:
    print(rs)
