"""Runtime shims for the gaps found by dry_run_insertion.py.

Neither the published NWB files nor the installed Spyglass source is modified; the shim
wraps one Spyglass method at runtime, inside our own ingestion scripts only.

Gap 1 -- hemisphere == 'unknown'
    The DANDI:001935 files (created 2026-07-28) carry ``FiberInsertion.hemisphere =
    "unknown"`` (a placeholder, because implant hemisphere is randomized per animal) and an
    unsigned ML magnitude. Spyglass PR #1637 declares
    ``FiberPhotometryConfig.hemisphere = enum('left', 'right')`` (nullable), so MySQL
    rejects the value: ``DataError 1265: Data truncated for column 'hemisphere'``.
    ``ndx-ophys-devices`` itself allows 'unknown', so the file is valid; the schema is just
    stricter. This shim maps any value outside {'left', 'right'} to NULL.

    It is a no-op for files that carry a real 'left'/'right' (uchida-lab-to-nwb commit
    913b41d, 2026-09-15, fills the real per-subject hemisphere on re-conversion).
"""

from spyglass.utils import logger

_VALID_HEMISPHERES = (None, "left", "right")


def install_hemisphere_shim() -> None:
    """Null out non-{'left','right'} hemisphere values in FiberPhotometryConfig entries."""
    from spyglass.common.common_photometry import FiberPhotometryConfig

    original = FiberPhotometryConfig.generate_entries_from_nwb_object
    if getattr(original, "_uchida_hemisphere_shim", False):
        return  # already installed

    def generate_entries_from_nwb_object(self, nwb_obj, base_key=None):
        result = original(self, nwb_obj, base_key)
        replaced = set()
        for entries in result.values():
            for entry in entries:
                value = entry.get("hemisphere")
                if value not in _VALID_HEMISPHERES:
                    replaced.add(value)
                    entry["hemisphere"] = None
        if replaced:
            logger.warning(
                f"FiberPhotometryConfig: hemisphere value(s) {sorted(replaced)} are not "
                "'left'/'right'; stored as NULL (ingest_shims.install_hemisphere_shim)."
            )
        return result

    generate_entries_from_nwb_object._uchida_hemisphere_shim = True
    FiberPhotometryConfig.generate_entries_from_nwb_object = (
        generate_entries_from_nwb_object
    )
