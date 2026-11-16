"""Interface writing the session's epoch and task, in the layout Spyglass reads, annotated with HED."""

import re

import h5py
import numpy as np
from hdmf.common import DynamicTable, VectorData, VectorIndex
from ndx_hed import HedLabMetaData, HedTags
from pydantic import FilePath
from pynwb.file import NWBFile

from neuroconv.basedatainterface import BaseDataInterface

# pCampi records at exactly 1 kHz on the NIDAQ (see PCampiSyncInterface).
_PCAMPI_SAMPLING_RATE = 1000.0

# PCampiSyncInterface writes the first 10 seconds in stub mode; the epoch matches it.
_STUB_DURATION_IN_S = 10.0

# Each NWB file holds one recording session, so it has one epoch.
_EPOCH_NUMBER = 1


class TaskEpochInterface(BaseDataInterface):
    """Write one epoch and one task row describing the session's behavioral condition.

    The layout follows what Spyglass ingests into ``IntervalList``, ``Task`` and ``TaskEpoch``:

    - ``nwbfile.epochs``: one row spanning the pCampi recording (the NWB time base), tagged
      ``"01_<task_name>"``. Spyglass names the interval after the first tag and matches it to the
      task's epoch number.
    - ``processing["tasks"]["task_table"]``: one row with ``task_name``, ``task_description``,
      ``task_environment``, ``camera_id`` and ``task_epochs``. ``camera_id`` lists the integer IDs of
      the cameras that recorded the task, taken from the trailing digits of each camera Device name
      (``"Camera1"`` -> 1), which is how Spyglass maps the IDs back to its ``CameraDevice`` entries.
      Without cameras it holds an empty string, which Spyglass reads as no cameras.

    The task row also carries a ``HED`` column (ndx-hed ``HedTags``) holding a ``Def/`` reference
    to a lab definition. The definitions and the HED schema version are written once to
    ``HedLabMetaData``. Task text and HED come from ``metadata["Tasks"][task_metadata_key]`` and
    ``metadata["HED"]`` (see ``general_metadata.yaml``).
    """

    keywords = ["task", "epoch", "HED"]

    def __init__(
        self,
        pcampi_file_path: FilePath,
        task_metadata_key: str,
        camera_names: list[str] | None = None,
        verbose: bool = False,
    ):
        """Initialize the interface.

        Parameters
        ----------
        pcampi_file_path : FilePath
            Path to the pCampi ``.h5`` file. Its length sets the epoch's stop time.
        task_metadata_key : str
            Key of this session's task under ``metadata["Tasks"]`` (``"lone"`` or ``"social"``).
        camera_names : list of str, optional
            Names of the camera Devices that recorded the task (``"Camera1"`` ... ``"Camera6"``). Each
            must end in its integer camera ID.
        verbose : bool, default: False
            Whether to print status messages.
        """
        self.verbose = verbose
        super().__init__(
            pcampi_file_path=pcampi_file_path, task_metadata_key=task_metadata_key, camera_names=camera_names
        )

    def get_metadata_schema(self) -> dict:
        metadata_schema = super().get_metadata_schema()
        metadata_schema["properties"]["Tasks"] = {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "required": ["task_name", "task_description", "task_environment", "hed"],
                "properties": {
                    "task_name": {"type": "string"},
                    "task_description": {"type": "string"},
                    "task_environment": {"type": "string"},
                    "hed": {"type": "string"},
                },
            },
        }
        metadata_schema["properties"]["HED"] = {
            "type": "object",
            "required": ["hed_schema_version", "definitions"],
            "properties": {
                "hed_schema_version": {"type": "string"},
                "definitions": {"type": "string"},
            },
        }
        return metadata_schema

    def add_to_nwbfile(self, nwbfile: NWBFile, metadata: dict, stub_test: bool = False) -> None:
        task_metadata = metadata["Tasks"][self.source_data["task_metadata_key"]]
        hed_metadata = metadata["HED"]

        if stub_test:
            stop_time = _STUB_DURATION_IN_S
        else:
            with h5py.File(self.source_data["pcampi_file_path"], "r") as file:
                stop_time = file["digital_input/data"].shape[0] / _PCAMPI_SAMPLING_RATE

        nwbfile.add_lab_meta_data(
            HedLabMetaData(
                hed_schema_version=hed_metadata["hed_schema_version"],
                definitions=hed_metadata["definitions"],
            )
        )

        task_name = task_metadata["task_name"]
        nwbfile.add_epoch(start_time=0.0, stop_time=stop_time, tags=[f"{_EPOCH_NUMBER:02d}_{task_name}"])

        task_epochs = VectorData(
            name="task_epochs",
            description="Epoch numbers in which the task ran.",
            data=np.array([_EPOCH_NUMBER], dtype=np.int64),
        )

        camera_names = self.source_data["camera_names"] or []
        if camera_names:
            camera_ids = [int(re.search(r"(\d+)$", name).group(1)) for name in camera_names]
            camera_id = VectorData(
                name="camera_id",
                description="IDs of the cameras that recorded the task: the trailing digits of each camera Device name.",
                data=np.array(camera_ids, dtype=np.int64),
            )
            camera_columns = [camera_id, VectorIndex(name="camera_id_index", data=[len(camera_ids)], target=camera_id)]
        else:
            # Spyglass reads camera IDs as list(row.camera_id), so "" means no cameras. An empty ragged
            # integer column would say the same, but NWB Inspector 0.7.1 and the ndx-hed 0.3.0 validator
            # both crash on a zero-length column.
            camera_columns = [
                VectorData(name="camera_id", description="IDs of the cameras that recorded the task: none.", data=[""])
            ]
        task_table = DynamicTable(
            name="task_table",
            description="Behavioral task of this session, in the layout Spyglass reads into Task and TaskEpoch.",
            columns=[
                VectorData(name="task_name", description="Name of the task.", data=[task_name]),
                VectorData(
                    name="task_description",
                    description="Description of the task.",
                    data=[task_metadata["task_description"]],
                ),
                VectorData(
                    name="task_environment",
                    description="Environment the animal was in.",
                    data=[task_metadata["task_environment"]],
                ),
                *camera_columns,
                task_epochs,
                VectorIndex(name="task_epochs_index", data=[1], target=task_epochs),
                HedTags(name="HED", description="HED annotation of the task.", data=[task_metadata["hed"]]),
            ],
        )

        tasks_module = nwbfile.create_processing_module(name="tasks", description="Behavioral task of this session.")
        tasks_module.add(task_table)
