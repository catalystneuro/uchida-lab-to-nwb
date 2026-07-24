"""Data inspection and NWB validation utilities for the Uchida Lab conversion."""
import warnings
warnings.filterwarnings("ignore")

from pynwb import NWBHDF5IO
import nwbinspector

NWB_STUB = "C:/Users/amtra/CatalystNeuro/nwb_output/uchida/nwb_stub/sub-M4_ses-240624_135840_M4.nwb"

# ── NWB Inspector ─────────────────────────────────────────────────────────────
print("=== nwbinspector ===")
results = list(nwbinspector.inspect_all(NWB_STUB))
for r in results:
    print(r)
print(f"Total issues: {len(results)}\n")

# ── NWB file structure ────────────────────────────────────────────────────────
print("=== NWB file structure ===")
with NWBHDF5IO(NWB_STUB, "r", load_namespaces=True) as io:
    nwb = io.read()

    print(f"session_id          : {nwb.session_id}")
    print(f"session_start_time  : {nwb.session_start_time}")
    print(f"subject             : {nwb.subject}")

    print("\n-- acquisition --")
    for k, v in nwb.acquisition.items():
        print(f"  {k}: {type(v).__name__}  data={getattr(v, 'data', None) and getattr(v.data, 'shape', None)}")

    print("\n-- processing --")
    for mod_name, mod in nwb.processing.items():
        for k, v in mod.data_interfaces.items():
            print(f"  {mod_name}/{k}: {type(v).__name__}  data={getattr(v, 'data', None) and getattr(v.data, 'shape', None)}")

    print("\n-- lab_meta_data --")
    for k, v in nwb.lab_meta_data.items():
        print(f"  {k}: {type(v).__name__}")
        if hasattr(v, "fiber_photometry_table"):
            t = v.fiber_photometry_table
            print(f"    FiberPhotometryTable: {len(t)} rows")

    print("\n-- behavior (processing) --")
    if "behavior" in nwb.processing:
        for k, v in nwb.processing["behavior"].data_interfaces.items():
            print(f"  {k}: {type(v).__name__}")
