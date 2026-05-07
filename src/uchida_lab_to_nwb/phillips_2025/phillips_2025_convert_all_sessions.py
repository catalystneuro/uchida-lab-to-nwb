"""Batch conversion of all Uchida Lab (Phillips 2025) sessions to NWB."""
import datetime
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from pprint import pformat
from typing import Union
from zoneinfo import ZoneInfo

from tqdm import tqdm

from neuroconv.utils import load_dict_from_file

from .phillips_2025_convert_session import session_to_nwb

_TIMEZONE = ZoneInfo("America/New_York")


def load_subject_metadata_from_xlsx(xlsx_path: Union[str, Path]) -> dict:
    """Load per-subject NWB metadata from the lab-provided Excel spreadsheet.

    The spreadsheet is in transposed format: rows are fields, columns are subjects.
    Expected fields (row labels in column A):
        Subject ID, Species, Strain / genotype, Sex, Date of birth,
        Weight at time of experiment, Experimental group, Surgery date

    Parameters
    ----------
    xlsx_path : str or Path
        Path to ``Subject metadata.xlsx``.

    Returns
    -------
    dict
        Keyed by subject_id (e.g. ``"M4"``). Each value is a dict of NWB Subject
        fields ready to pass to ``session_to_nwb(subject_metadata=...)``.
    """
    import openpyxl

    wb = openpyxl.load_workbook(xlsx_path)
    ws = wb.active

    rows = [row for row in ws.iter_rows(values_only=True) if any(v is not None for v in row)]
    field_names = [str(row[0]) for row in rows]
    n_subjects = len(rows[0]) - 1

    result = {}
    for col_idx in range(n_subjects):
        raw = {field_names[i]: rows[i][col_idx + 1] for i in range(len(rows))}

        subject_id = str(raw["Subject ID"])

        # date_of_birth: openpyxl returns datetime.datetime for date cells
        dob = raw.get("Date of birth")
        if isinstance(dob, (datetime.datetime, datetime.date)):
            dob = datetime.datetime(dob.year, dob.month, dob.day, tzinfo=_TIMEZONE)
        else:
            dob = None

        # Surgery date (not a standard NWB field — included in description)
        surgery_raw = raw.get("Surgery date")
        surgery_str = None
        if isinstance(surgery_raw, (datetime.datetime, datetime.date)):
            surgery_str = surgery_raw.strftime("%Y-%m-%d")
        elif surgery_raw:
            surgery_str = str(surgery_raw)

        # Strain / genotype: "Long Evans WT" → strain="Long Evans", genotype="WT"
        strain_raw = str(raw.get("Strain / genotype", "")).strip()
        parts = strain_raw.rsplit(" ", 1)
        strain = parts[0] if len(parts) > 1 else strain_raw
        genotype = parts[1] if len(parts) > 1 else "WT"

        exp_group = str(raw.get("Experimental group", "unknown")).strip()
        sex = str(raw.get("Sex", "U")).strip()
        species = str(raw.get("Species", "Rattus norvegicus")).strip()

        weight_raw = raw.get("Weight at time of experiment")
        weight_str = (
            None if (weight_raw is None or str(weight_raw).lower() == "not available") else str(weight_raw)
        )

        desc_parts = [f"Experimental group: {exp_group}.", f"Strain: {strain_raw}."]
        if surgery_str:
            desc_parts.append(f"Surgery date: {surgery_str}.")
        desc_parts.append(
            f"Weight at experiment time: {weight_str}." if weight_str else "Weight at experiment time: not recorded."
        )
        desc_parts.append("SFARI Autism Rat Models Consortium (ARC).")

        entry = dict(
            subject_id=subject_id,
            species=species,
            strain=strain,
            genotype=genotype,
            sex=sex,
            description=" ".join(desc_parts),
        )
        if dob is not None:
            entry["date_of_birth"] = dob
        if weight_str is not None:
            entry["weight"] = weight_str

        result[subject_id] = entry

    return result


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
        Path to a subject metadata file. Accepts:
        - ``.xlsx`` / ``.xls``: lab-provided Excel spreadsheet (preferred)
        - ``.yaml`` / ``.yml``: legacy YAML keyed by subject_id

    Returns
    -------
    list of dict
        One dict per session containing kwargs for `session_to_nwb`.
    """
    data_dir_path = Path(data_dir_path)

    # Load per-subject metadata if provided
    subject_meta_map: dict = {}
    if subject_metadata_path is not None:
        path = Path(subject_metadata_path)
        if path.suffix.lower() in (".xlsx", ".xls"):
            subject_meta_map = load_subject_metadata_from_xlsx(path)
        else:
            subject_meta_map = load_dict_from_file(path)

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
        subject_metadata_path="H:/Uchida-CN-data-share/Subject metadata.xlsx",
        max_workers=1,
        stub_test=False,
        overwrite=False,
        verbose=True,
    )
