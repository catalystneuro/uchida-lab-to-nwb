"""Inspect converted NWB files with NWB Inspector and summarize the results.

convert_all_sessions.py writes one NWB file per session to <output folder>/sub-<subject>/. For each of them,
inspect_output_folder saves an NWB Inspector report, inspector_reports/<file stem>.txt in the output folder, and
writes inspection_summary.csv to the output folder, with one row per NWB file: its subject and session, the number
of inspector messages per importance level and the number of HERD references (the ontology terms stated under
ExternalResources in general_metadata.yaml).

The DANDI configuration of NWB Inspector is used, the same checks dandi upload runs. A file with CRITICAL messages
cannot be uploaded.
"""

from pathlib import Path
from typing import Union

import pandas as pd

INSPECTOR_REPORT_FOLDER_NAME = "inspector_reports"
INSPECTION_SUMMARY_FILE_NAME = "inspection_summary.csv"
IMPORTANCE_LEVELS = ["ERROR", "PYNWB_VALIDATION", "CRITICAL", "BEST_PRACTICE_VIOLATION", "BEST_PRACTICE_SUGGESTION"]
INSPECTION_SUMMARY_COLUMNS = ["nwbfile_name", "subject_id", "session_id", *IMPORTANCE_LEVELS, "herd_references"]


def inspect_nwbfile_and_save_report(
    nwbfile_path: Union[str, Path], report_folder_path: Union[str, Path]
) -> dict[str, int]:
    """Run NWB Inspector with the DANDI configuration on one NWB file and save its report.

    Parameters
    ----------
    nwbfile_path : Union[str, Path]
        Path to the NWB file.
    report_folder_path : Union[str, Path]
        Folder of the report, <file stem>.txt. An earlier report of the same file is replaced.

    Returns
    -------
    dict[str, int]
        The number of inspector messages per importance level of IMPORTANCE_LEVELS.
    """
    from nwbinspector import format_messages, inspect_nwbfile, load_config, save_report

    nwbfile_path = Path(nwbfile_path)
    report_folder_path = Path(report_folder_path)
    messages = list(inspect_nwbfile(nwbfile_path=nwbfile_path, config=load_config("dandi")))
    report_folder_path.mkdir(parents=True, exist_ok=True)
    save_report(
        report_file_path=report_folder_path / f"{nwbfile_path.stem}.txt",
        formatted_messages=format_messages(messages, levels=["importance", "check_function_name"]),
        overwrite=True,
    )
    return {level: sum(message.importance.name == level for message in messages) for level in IMPORTANCE_LEVELS}


def read_subject_session_and_herd_references(nwbfile_path: Union[str, Path]) -> dict:
    """Read the subject ID, the session ID and the number of HERD references of an NWB file.

    Parameters
    ----------
    nwbfile_path : Union[str, Path]
        Path to the NWB file.

    Returns
    -------
    dict
        "subject_id", "session_id" and "herd_references" (0 if the file has no external resources).
    """
    from pynwb import NWBHDF5IO

    with NWBHDF5IO(nwbfile_path, "r") as io:
        nwbfile = io.read()
        external_resources = nwbfile.external_resources
        return dict(
            subject_id=nwbfile.subject.subject_id,
            session_id=nwbfile.session_id,
            herd_references=0 if external_resources is None else len(external_resources.to_dataframe()),
        )


def inspect_output_folder(output_dir_path: Union[str, Path]) -> pd.DataFrame:
    """Inspect every NWB file of a conversion output folder and write the inspection summary.

    The NWB files are those in the subject folders, <output folder>/sub-*/*.nwb; stub files (in nwb_stub/) are
    left out. The reports go to <output folder>/inspector_reports/ and the summary to
    <output folder>/inspection_summary.csv, both replacing earlier ones.

    Parameters
    ----------
    output_dir_path : Union[str, Path]
        The output folder of convert_all_sessions.dataset_to_nwb.

    Returns
    -------
    pd.DataFrame
        The summary, one row per NWB file, with the columns of INSPECTION_SUMMARY_COLUMNS.
    """
    output_dir_path = Path(output_dir_path)
    nwbfile_paths = sorted(output_dir_path.glob("sub-*/*.nwb"))
    if not nwbfile_paths:
        raise FileNotFoundError(f"No NWB files found in {output_dir_path}/sub-*/.")

    report_folder_path = output_dir_path / INSPECTOR_REPORT_FOLDER_NAME
    rows = []
    for nwbfile_path in nwbfile_paths:
        print(f"Inspecting {nwbfile_path.name}")
        rows.append(
            dict(
                nwbfile_name=nwbfile_path.name,
                **read_subject_session_and_herd_references(nwbfile_path),
                **inspect_nwbfile_and_save_report(nwbfile_path, report_folder_path),
            )
        )
    summary = pd.DataFrame(rows, columns=INSPECTION_SUMMARY_COLUMNS)
    summary.to_csv(output_dir_path / INSPECTION_SUMMARY_FILE_NAME, index=False)
    return summary


if __name__ == "__main__":
    output_dir_path = Path("H:/uchida-nwbfiles")

    summary = inspect_output_folder(output_dir_path)
    print(summary.to_string(index=False))
    print(f"Reports in {output_dir_path / INSPECTOR_REPORT_FOLDER_NAME}")
