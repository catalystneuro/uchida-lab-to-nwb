# DANDI staging

The converted files are shared in [DANDI:001935](https://dandiarchive.org/dandiset/001935), which is embargoed until
the paper is published. Uploads go to the draft of the dandiset; a published version is a fixed snapshot of the draft.
Upload by hand, after reviewing the NWB files and the inspection summary.

The steps are in `upload_to_DANDI.py`. Its `__main__` block sets:

- `nwb_folder_path`: the output folder of the conversion;
- `dandiset_folder_path`: a folder for the organized copy;
- `dandiset_id`: `001935`;
- `dandi_instance`: `dandi` for the archive, `dandi-sandbox` for the [sandbox](https://sandbox.dandiarchive.org), a
  separate test server where a copy of the dandiset can be tried first (with the ID of the sandbox dandiset);
- `upload`: `False` until the organized folder and the report are checked.

Reading the embargoed dandiset and uploading need a DANDI API key, from your account page on the archive or the
sandbox, in the environment: `DANDI_API_KEY` for the archive, `DANDI_SANDBOX_API_KEY` for the sandbox.

## 1. Review the converted files

Before staging, check in the output folder:

- `inspection_summary.csv`: no `CRITICAL` or `ERROR` messages, and `herd_references` above 0 for every file.
- `inspector_reports/`: the NWB Inspector report of each file.
- `exceptions/`: empty, so that every session was converted.
- A few files opened with PyNWB or the example notebook (see [NWB file structure](nwb_file_structure.md)).

## 2. Organize and compare with the draft

Run `upload_to_DANDI.py` with `upload = False`:

```bash
python src/uchida_lab_to_nwb/phillips_2025/upload_to_DANDI.py
```

`organize_nwbfiles` downloads the dandiset metadata (`dandiset.yaml`) into `<dandiset folder>/001935` and runs
`dandi organize` in copy mode: the NWB files are copied there with the names DANDI expects
(`sub-M4/sub-M4_ses-day-1-lone_image.nwb`; dandi adds `_image` for files with linked videos), and the 6 videos of
each file are copied to a folder of the same name, with the links in the file updated. The files of the output folder
are not changed. Stub files must not be in the output folder that is organized.

`organize_nwbfiles` runs only when the dandiset folder holds no NWB files. To organize again, remove the folder first.

`report_draft_assets` then prints the status of each draft asset:

- `replaced`: the upload replaces it with a file at the same path.
- `superseded`: a new file of the same subject and session has another path. The upload adds the new file; the old
  asset stays on the draft until it is removed. Videos are always superseded when a file is uploaded again, because
  dandi names them by the ID of their video series.
- `not reconverted`: no new file for its subject and session.
- `new`: an organized file that is not on the draft yet.

## 3. Upload

Set `upload = True` and run the file again. `upload_organized_files` validates the organized files (NWB schema, DANDI
requirements, NWB Inspector critical checks) and the dandiset metadata, as `dandi upload` would, and uploads the
folder to the draft. Nothing is uploaded if validation finds an error; the error lists every problem.

Superseded assets are not removed. Remove them on the dandiset page or with `dandi delete` once the new files are
checked.

## From Python

```python
from uchida_lab_to_nwb.phillips_2025.upload_to_DANDI import (
    organize_nwbfiles,
    report_draft_assets,
    upload_organized_files,
)

dandiset_path = organize_nwbfiles(
    nwb_folder_path="<output folder>",
    dandiset_folder_path="<dandiset folder>",
    dandiset_id="001935",
    dandi_instance="dandi",
)
print(report_draft_assets(dandiset_path=dandiset_path, dandiset_id="001935", dandi_instance="dandi"))
upload_organized_files(dandiset_path=dandiset_path, dandi_instance="dandi")
```
