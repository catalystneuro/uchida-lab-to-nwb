"""Full Spyglass ingestion of converted DANDI:001935 NWB files with `insert_sessions()`.

Runs every common table (not only fiber photometry, unlike insert_fiber_photometry.py),
then prints row counts per table and the InsertError log for each file. Errors are
collected with raise_err=False so one run shows every table that fails.

Needs a Spyglass build with fiber photometry and multi-camera pose support, e.g. the
`uchida-integration` branch of https://github.com/catalystneuro/spyglass installed in the
WSL env. Run from this directory, passing NWB file names in the Spyglass raw dir:

    conda activate spyglass-uchida-lab-env
    python insert_full_session.py sub-M4_ses-day-1-lone.nwb sub-M4_ses-day-1-social.nwb
"""

import sys
from pathlib import Path

import datajoint as dj

CONF = Path(__file__).with_name("dj_local_conf.json")

dj.config.load(str(CONF))  # BEFORE any spyglass import
dj.conn(use_tls=False)

import spyglass.common as sgc  # noqa: E402
import spyglass.data_import as sgi  # noqa: E402
from spyglass.common.common_events import ImportedEvents  # noqa: E402
from spyglass.common.common_usage import InsertError  # noqa: E402
from spyglass.position.v1.imported_multicam_pose import (  # noqa: E402
    CameraCalibration,
    ImportedMultiCameraPose,
)
from spyglass.position.v1.imported_pose import ImportedPose  # noqa: E402
from spyglass.settings import raw_dir  # noqa: E402
from spyglass.utils.nwb_helper_fn import get_nwb_copy_filename  # noqa: E402

PER_FILE_TABLES = (
    sgc.Session,
    sgc.Session.Experimenter,
    sgc.IntervalList,
    sgc.TaskEpoch,
    sgc.VideoFile,
    CameraCalibration,
    ImportedMultiCameraPose,
    ImportedMultiCameraPose.BodyPart,
    ImportedMultiCameraPose.Camera,
    ImportedPose,
    ImportedEvents,
    sgc.FiberPhotometryConfig,
    sgc.FiberPhotometryResponseSeries,
    sgc.FiberPhotometryResponseSeries.Fiber,
    sgc.PositionSource,
    sgc.RawPosition,
    sgc.DIOEvents,
    sgc.SensorData,
    sgc.ExternalResources,
    sgc.ExternalResources.Reference,
)
SHARED_TABLES = (
    sgc.OntologyTerm,
    sgc.Subject,
    sgc.LabMember,
    sgc.Institution,
    sgc.Lab,
    sgc.Task,
    sgc.CameraDevice,
    sgc.BrainRegion,
    sgc.Indicator,
    sgc.ExcitationSource,
    sgc.Photodetector,
    sgc.OpticalFiber,
)


def section(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


def table_name(table) -> str:
    return getattr(table, "full_table_name", table.__name__).split(".")[-1].strip("`")


def ingest(nwb_file_name: str) -> None:
    nwbfile_path = Path(raw_dir) / nwb_file_name
    if not nwbfile_path.exists():
        raise FileNotFoundError(f"Expected NWB file at {nwbfile_path}")
    copy_dict = {"nwb_file_name": get_nwb_copy_filename(nwb_file_name)}
    error_keys = [copy_dict, {"nwb_file_name": nwb_file_name}]

    # Nwbfile is keyed on the copy name (stem + "_.nwb"); with an existing entry
    # insert_sessions() skips the file silently, so remove it (cascades) first.
    existing = sgc.Nwbfile() & copy_dict
    if existing:
        section(f"Removing existing entry for {copy_dict['nwb_file_name']}")
        existing.delete(safemode=False)
    (InsertError() & error_keys).delete_quick()

    section(f"insert_sessions(): {nwb_file_name}")
    sgi.insert_sessions(str(nwbfile_path), rollback_on_fail=False, raise_err=False)

    section(f"Row counts for {nwb_file_name}")
    for table in PER_FILE_TABLES:
        print(f"{table_name(table):<45} {len(table() & copy_dict)}")
    print("-- shared tables (whole DB) --")
    for table in SHARED_TABLES:
        print(f"{table_name(table):<45} {len(table())}")

    section(f"InsertError log for {nwb_file_name}")
    errors = InsertError() & error_keys
    print(f"InsertError rows: {len(errors)}")
    for row in errors.fetch(as_dict=True):
        print(f"- {row.get('table')}: {row.get('error_type')}: {row.get('error_message')}")


def main() -> None:
    for nwb_file_name in sys.argv[1:]:
        ingest(nwb_file_name)


if __name__ == "__main__":
    main()
