"""Load per-subject metadata from the lab's Excel spreadsheet."""

from __future__ import annotations

import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

_TIMEZONE = ZoneInfo("America/New_York")


def get_subject_metadata(subject_id: str, xlsx_path: Path) -> dict:
    """Return NWB Subject metadata dict for one subject.

    Reads ``Subject metadata.xlsx`` (lab-provided). The sheet is transposed:
    rows are fields, columns are subjects. Expected fields (row labels in
    column A): Subject ID, Species, Strain / genotype, Sex, Date of birth,
    Weight at time of experiment, Experimental group, Surgery date.

    Parameters
    ----------
    subject_id : str
        Subject identifier, e.g. ``"M4"``.
    xlsx_path : Path
        Path to ``Subject metadata.xlsx``.

    Returns
    -------
    dict
        NWB Subject fields: subject_id, species, strain, genotype, sex,
        description, and (when available) date_of_birth, weight.

    Raises
    ------
    KeyError
        If ``subject_id`` is not found in the sheet.
    """
    import openpyxl

    wb = openpyxl.load_workbook(xlsx_path)
    ws = wb.active

    rows = [row for row in ws.iter_rows(values_only=True) if any(v is not None for v in row)]
    field_names = [str(row[0]) for row in rows]
    n_subjects = len(rows[0]) - 1

    for col_idx in range(n_subjects):
        raw = {field_names[i]: rows[i][col_idx + 1] for i in range(len(rows))}
        if str(raw.get("Subject ID")) == subject_id:
            return _parse_subject_row(raw)

    raise KeyError(f"Subject '{subject_id}' not found in {xlsx_path}")


def _parse_subject_row(raw: dict) -> dict:
    """Convert one column of the transposed spreadsheet into NWB Subject fields."""
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

    # Strain / genotype: "Long Evans WT" -> strain="Long Evans", genotype="WT"
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

    result = dict(
        subject_id=subject_id,
        species=species,
        strain=strain,
        genotype=genotype,
        sex=sex,
        description=" ".join(desc_parts),
    )
    if dob is not None:
        result["date_of_birth"] = dob
    if weight_str is not None:
        result["weight"] = weight_str

    return result


if __name__ == "__main__":
    xlsx_path = Path("H:/Uchida-CN-data-share/Subject metadata.xlsx")
    metadata = get_subject_metadata(subject_id="M4", xlsx_path=xlsx_path)
    print(metadata)
