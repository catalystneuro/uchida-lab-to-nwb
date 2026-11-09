"""Batch conversion of all Uchida Lab (Phillips 2025) sessions to NWB.

dataset_to_nwb converts every session of one condition folder (Lone_data or Social_data) with
convert_session.session_to_nwb, writing <output folder>/sub-<subject>/sub-<subject>_ses-<session>.nwb. A session that
fails does not stop the others: its traceback is written to <output folder>/exceptions/. Run this file to convert
both conditions; the paths are set in the ``if __name__ == "__main__":`` block at the bottom.

After converting, run inspection.py on the output folder, then upload_to_DANDI.py.
"""

import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from pprint import pformat
from typing import Union

from tqdm import tqdm

from uchida_lab_to_nwb.phillips_2025.convert_session import session_to_nwb
from uchida_lab_to_nwb.phillips_2025.utils.subject_metadata import get_subject_metadata


def get_session_to_nwb_kwargs_per_session(
    *,
    data_dir_path: Union[str, Path],
    subject_metadata_path: Union[str, Path],
) -> list[dict]:
    """Discover all sessions in the data directory and return kwargs for each.

    Expected directory structure::

        data_dir_path/
            day_{N}/
                M{id}/
                    *.h5, *.doric, DANNCE/, videos/, ...

    Parameters
    ----------
    data_dir_path : str or Path
        Root directory containing day_*/M*/ session folders.
    subject_metadata_path : str or Path
        Path to the lab-provided ``Subject metadata.xlsx`` spreadsheet. A session whose
        subject is missing from the sheet is skipped with a warning.

    Returns
    -------
    list of dict
        One dict per session containing kwargs for `session_to_nwb`.
    """
    data_dir_path = Path(data_dir_path)
    subject_metadata_path = Path(subject_metadata_path)

    kwargs_list = []
    for day_dir in sorted(data_dir_path.glob("day_*")):
        if not day_dir.is_dir():
            continue
        for subject_dir in sorted(day_dir.glob("M*")):
            if not subject_dir.is_dir():
                continue
            # Sanity check: must have at least a pCampi H5 and a Doric file
            if not list(subject_dir.glob("*.h5")) or not list(subject_dir.glob("*.doric")):
                continue
            subject_id = subject_dir.name

            try:
                subject_metadata = get_subject_metadata(subject_id, subject_metadata_path)
            except KeyError as exc:
                print(f"  [WARNING] {exc}; skipping {subject_dir}")
                continue

            kwargs_list.append(
                dict(
                    session_dir_path=subject_dir,
                    subject_metadata=subject_metadata,
                )
            )

    return kwargs_list


def safe_session_to_nwb(
    *,
    session_to_nwb_kwargs: dict,
    exception_file_path: Union[Path, str],
) -> None:
    """Run session_to_nwb and write the traceback of any exception to exception_file_path.

    Parameters
    ----------
    session_to_nwb_kwargs : dict
        Keyword arguments of session_to_nwb.
    exception_file_path : Path or str
        File the kwargs and the traceback are written to if the conversion raises.
    """
    exception_file_path = Path(exception_file_path)
    try:
        session_to_nwb(**session_to_nwb_kwargs)
    except Exception:
        with open(exception_file_path, mode="w") as f:
            f.write(f"session_to_nwb_kwargs:\n{pformat(session_to_nwb_kwargs)}\n\n")
            f.write(traceback.format_exc())


def dataset_to_nwb(
    *,
    data_dir_path: Union[str, Path],
    output_dir_path: Union[str, Path],
    subject_metadata_path: Union[str, Path],
    max_workers: int = 1,
    stub_test: bool = False,
    overwrite: bool = False,
    verbose: bool = True,
) -> None:
    """Convert every session of one condition folder of the Phillips 2025 dataset to NWB.

    Parameters
    ----------
    data_dir_path : str or Path
        Condition folder, ``Lone_data/`` or ``Social_data/``, holding ``day_*/M*/`` sessions.
    output_dir_path : str or Path
        Directory where NWB files will be written, one ``sub-<subject>/`` folder per subject.
        Failed sessions write their traceback to ``exceptions/`` in it.
    subject_metadata_path : str or Path
        Path to the lab-provided ``Subject metadata.xlsx`` spreadsheet.
    max_workers : int
        Number of parallel workers.
    stub_test : bool
        Write small stub files for testing.
    overwrite : bool
        Overwrite existing NWB files.
    verbose : bool
        Print progress.
    """
    data_dir_path = Path(data_dir_path)
    output_dir_path = Path(output_dir_path)
    exception_dir = output_dir_path / "exceptions"
    exception_dir.mkdir(parents=True, exist_ok=True)

    kwargs_list = get_session_to_nwb_kwargs_per_session(
        data_dir_path=data_dir_path,
        subject_metadata_path=subject_metadata_path,
    )

    futures = []
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        for kwargs in kwargs_list:
            kwargs["output_dir_path"] = output_dir_path
            kwargs["stub_test"] = stub_test
            kwargs["overwrite"] = overwrite
            kwargs["verbose"] = verbose
            # Name by condition, day and subject: the subject folder name alone (e.g. "M4") repeats across
            # days and conditions, which share one exceptions folder.
            session_dir_path = kwargs["session_dir_path"]
            condition = data_dir_path.name.removesuffix("_data").lower()
            exception_file_path = (
                exception_dir / f"ERROR_{condition}_{session_dir_path.parent.name}_{session_dir_path.name}.txt"
            )
            futures.append(
                executor.submit(
                    safe_session_to_nwb,
                    session_to_nwb_kwargs=kwargs,
                    exception_file_path=exception_file_path,
                )
            )

        for _ in tqdm(as_completed(futures), total=len(futures), desc="Converting sessions"):
            pass


if __name__ == "__main__":
    dataset_to_nwb(
        data_dir_path="H:/Uchida-CN-data-share/Hannah_data/M4-M7/Lone_data",
        output_dir_path="H:/uchida-nwbfiles",
        subject_metadata_path="H:/Uchida-CN-data-share/Subject metadata.xlsx",
        max_workers=1,
        stub_test=False,
        overwrite=True,
        verbose=True,
    )

    dataset_to_nwb(
        data_dir_path="H:/Uchida-CN-data-share/Hannah_data/M4-M7/Social_data",
        output_dir_path="H:/uchida-nwbfiles",
        subject_metadata_path="H:/Uchida-CN-data-share/Subject metadata.xlsx",
        max_workers=1,
        stub_test=False,
        overwrite=True,
        verbose=True,
    )
