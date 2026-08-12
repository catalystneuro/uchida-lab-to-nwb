"""Module-level constants for the sDANNCE rat23 skeleton and fiber photometry brain regions."""

# fiber_photometry.yaml FiberPhotometryTable "location" string -> ontology term. NeuroConv's
# built-in offline brain-region lookup doesn't recognize either of these for rat (no dedicated
# Allen atlas -- falls back to a small UBERON vocabulary that doesn't include these specific
# structures), so map them explicitly via metadata["BrainRegions"].
#
# - "Nucleus Accumbens" (NAc, ROI01): UBERON:0001882, verified against the EBI Ontology Lookup
#   Service (https://www.ebi.ac.uk/ols4), an exact, unambiguous match.
# - "Tail of Striatum" (TS, ROI02): a functionally-defined dopamine-circuit subregion (see
#   Menegas et al.) with no dedicated term in UBERON or in NeuroConv's curated Allen Mouse Brain
#   Atlas subset as of 2026-08-12 (checked both). Approximated with the coarser generic
#   "striatum" (UBERON:0002435) -- confirmed acceptable pending a more specific term becoming
#   available.
BRAIN_REGION_ONTOLOGY_MAPPING: dict[str, dict] = {
    "Nucleus Accumbens": {
        "id": "UBERON:0001882",
        "uri": "http://purl.obolibrary.org/obo/UBERON_0001882",
    },
    "Tail of Striatum": {
        "id": "UBERON:0002435",
        "uri": "http://purl.obolibrary.org/obo/UBERON_0002435",
    },
}

# rat23 landmark name -> base anatomical structure name to resolve via
# neuroconv.tools.ontology.get_anatomy_term(). NeuroConv's curated general-anatomy table
# recognizes the base structure ("Shoulder", "Hand", ...) but not this skeleton's own
# "<Structure><Left|Right>" naming convention, and UBERON doesn't distinguish laterality as
# separate terms, so both sides of a bilateral landmark reuse the same UBERON reference. Names not
# listed here either already resolve directly ("Snout") or via NeuroConv's built-in alias list
# ("TailBase" -> "Tail"). "SpineFront"/"SpineMiddle"/"SpineLow" all map to the single generic
# "Spine" (vertebral column) term -- NeuroConv's vocabulary does not distinguish anteroposterior
# spine subdivisions.
_ANATOMY_BASE_STRUCTURE: dict[str, str] = {
    "EarLeft": "Ear",
    "EarRight": "Ear",
    "SpineFront": "Spine",
    "SpineMiddle": "Spine",
    "SpineLow": "Spine",
    "ShoulderLeft": "Shoulder",
    "ShoulderRight": "Shoulder",
    "ElbowLeft": "Elbow",
    "ElbowRight": "Elbow",
    "WristLeft": "Wrist",
    "WristRight": "Wrist",
    "HandLeft": "Hand",
    "HandRight": "Hand",
    "HipLeft": "Hip",
    "HipRight": "Hip",
    "KneeLeft": "Knee",
    "KneeRight": "Knee",
    "AnkleLeft": "Ankle",
    "AnkleRight": "Ankle",
    "FootLeft": "Foot",
    "FootRight": "Foot",
}


def get_anatomy_ontology_mapping() -> dict:
    """Build the ``metadata["Anatomy"]`` HERD override mapping for the rat23 skeleton.

    See :data:`_ANATOMY_BASE_STRUCTURE` for why an explicit override is needed: NeuroConv's
    curated anatomy table doesn't recognize this skeleton's ``"<Structure><Left|Right>"`` node
    naming, only the base structure name.

    Returns
    -------
    dict
        ``{landmark name: {"id": "UBERON:...", "uri": "http://purl.obolibrary.org/obo/UBERON_..."}}``
        for each rat23 landmark whose base structure NeuroConv's curated table recognizes.
    """
    from neuroconv.tools.ontology import get_anatomy_term

    mapping = {}
    for landmark_name, base_name in _ANATOMY_BASE_STRUCTURE.items():
        term = get_anatomy_term(base_name)
        if term is None:
            continue
        mapping[landmark_name] = {"id": term.curie, "uri": term.entity_uri}
    return mapping


SDANNCE_LANDMARK_NAMES: list[str] = [
    "Snout",
    "EarLeft",
    "EarRight",
    "SpineFront",
    "SpineMiddle",
    "SpineLow",
    "TailBase",
    "ShoulderLeft",
    "ElbowLeft",
    "WristLeft",
    "HandLeft",
    "ShoulderRight",
    "ElbowRight",
    "WristRight",
    "HandRight",
    "HipLeft",
    "KneeLeft",
    "AnkleLeft",
    "FootLeft",
    "HipRight",
    "KneeRight",
    "AnkleRight",
    "FootRight",
]

# Skeleton edges from rat23.mat joints_idx, converted from 1-based to 0-based.
SDANNCE_SKELETON_EDGES: list[tuple[int, int]] = [
    (0, 1),
    (0, 2),
    (0, 3),
    (1, 2),
    (3, 4),
    (3, 7),
    (3, 11),
    (4, 5),
    (5, 6),
    (5, 15),
    (5, 19),
    (7, 8),
    (8, 9),
    (9, 10),
    (11, 12),
    (12, 13),
    (13, 14),
    (15, 16),
    (16, 17),
    (17, 18),
    (19, 20),
    (20, 21),
    (21, 22),
]
