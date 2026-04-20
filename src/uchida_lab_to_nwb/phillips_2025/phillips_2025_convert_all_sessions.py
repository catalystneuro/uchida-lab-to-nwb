"""Batch conversion of all Uchida Lab (Phillips 2025) sessions to NWB."""
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from pprint import pformat
from typing import Union
import traceback

from tqdm import tqdm

from neuroconv.utils import load_dict_from_file

from .phillips_2025_convert_session import session_to_nwb


def get_session_to_nwb_kwargs_per_session(
    *,
    data_dir_path: Union[str, Path],
    subject_metadata_path: Union[str, Path, None] = None,
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
    subject_metadata_path : str or Path, optional
        Path to a YAML file with per-subject metadata keyed by subject_id
        (e.g. ``_metadata/subject_metadata.yaml``).

    Returns
    -------
    list of dict
        One dict per session containing kwargs for `session_to_nwb`.
    """
    data_dir_path = Path(data_dir_path)

    # Load per-subject metadata if provided
    subject_meta_map: dict = {}
    if subject_metadata_path is not None:
        subject_meta_map = load_dict_from_file(Path(subject_metadata_path))

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
            kwargs_list.append(
                dict(
                    session_dir_path=subject_dir,
                    subject_metadata=subject_meta_map.get(subject_id, {}),
                )
            )

    return kwargs_list


def safe_session_to_nwb(
    *,
    session_to_nwb_kwargs: dict,
    exception_file_path: Union[Path, str],
) -> None:
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
    subject_metadata_path: Union[str, Path, None] = None,
    max_workers: int = 1,
    stub_test: bool = False,
    overwrite: bool = False,
    verbose: bool = True,
) -> None:
    """Convert the entire Phillips 2025 dataset to NWB.

    Parameters
    ----------
    data_dir_path : str or Path
        Root data directory (e.g. ``Lone_data/``).
    output_dir_path : str or Path
        Directory where NWB files will be written.
    subject_metadata_path : str or Path, optional
        Path to ``_metadata/subject_metadata.yaml`` with per-subject metadata.
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
            session_id = kwargs["session_dir_path"].name
            exception_file_path = exception_dir / f"ERROR_{session_id}.txt"
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
        output_dir_path="C:/Users/amtra/CatalystNeuro/nwb_output/uchida",
        subject_metadata_path=(
            "C:/Users/amtra/CatalystNeuro/uchida-lab-to-nwb"
            "/src/uchida_lab_to_nwb/phillips_2025/_metadata/subject_metadata.yaml"
        ),
        max_workers=1,
        stub_test=False,
        overwrite=False,
        verbose=True,
    )
