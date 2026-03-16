"""Merge Theographic places with OpenBible geocoding data."""

import json
from pathlib import Path

from rapidfuzz import fuzz

from gnosis.parsers.openbible import OpenBiblePlace
from gnosis.types import Place

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_PLACE_MATCHES_PATH = _PROJECT_ROOT / "overrides" / "place_matches.json"


def _load_manual_overrides() -> dict[str, str]:
    if _PLACE_MATCHES_PATH.exists():
        return json.loads(_PLACE_MATCHES_PATH.read_text())
    return {}


def merge_places(
    theographic_places: dict[str, Place],
    openbible_places: dict[str, OpenBiblePlace],
) -> tuple[dict[str, Place], dict[str, str]]:
    """Merge OpenBible geo data into Theographic places.

    Returns:
        - Updated places dict
        - Match log: theographic_slug → match_type ("exact", "override", "fuzzy", "unmatched")
    """
    manual_overrides = _load_manual_overrides()
    match_log: dict[str, str] = {}

    # Build case-insensitive lookup for OpenBible
    ob_lower: dict[str, str] = {}
    for fid in openbible_places:
        ob_lower[fid.lower().replace("_", " ")] = fid

    matched_ob_ids: set[str] = set()

    for slug, place in theographic_places.items():
        # 1. Manual override
        if slug in manual_overrides:
            ob_fid = manual_overrides[slug]
            if ob_fid in openbible_places:
                _apply_openbible(place, openbible_places[ob_fid])
                match_log[slug] = "override"
                matched_ob_ids.add(ob_fid)
                continue

        # 2. Exact match on kjvName or esvName
        matched = False
        for name in [place.kjv_name, place.esv_name, place.name]:
            if not name:
                continue
            key = name.lower().replace("_", " ")
            if key in ob_lower:
                ob_fid = ob_lower[key]
                _apply_openbible(place, openbible_places[ob_fid])
                match_log[slug] = "exact"
                matched_ob_ids.add(ob_fid)
                matched = True
                break
        if matched:
            continue

        # 3. Fuzzy match
        best_score = 0.0
        best_fid = None
        for name in [place.kjv_name, place.esv_name, place.name]:
            if not name:
                continue
            for ob_fid in openbible_places:
                if ob_fid in matched_ob_ids:
                    continue
                score = fuzz.token_sort_ratio(
                    name.lower(), ob_fid.lower().replace("_", " ")
                )
                if score > best_score:
                    best_score = score
                    best_fid = ob_fid

        if best_score >= 85 and best_fid:
            _apply_openbible(place, openbible_places[best_fid])
            match_log[slug] = "fuzzy"
            matched_ob_ids.add(best_fid)
        else:
            match_log[slug] = "unmatched"

    return theographic_places, match_log


def _apply_openbible(place: Place, ob: OpenBiblePlace) -> None:
    """Apply OpenBible data to a Theographic place."""
    if ob.latitude is not None:
        place.latitude = ob.latitude
        place.longitude = ob.longitude
        place.coordinate_source = "openbible"
    if ob.confidence is not None:
        place.geo_confidence = ob.confidence
    if ob.precision_meters is not None:
        place.precision_meters = ob.precision_meters
    if ob.modern_name:
        place.modern_name = ob.modern_name
    place.openbible_id = ob.friendly_id
    if ob.place_types:
        existing = set(place.place_types)
        for pt in ob.place_types:
            if pt not in existing:
                place.place_types.append(pt)
