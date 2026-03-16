"""Parser for OpenBible Geocoding Data (JSONL format)."""

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class OpenBiblePlace:
    friendly_id: str
    place_types: list[str] = field(default_factory=list)
    latitude: float | None = None
    longitude: float | None = None
    confidence: float | None = None
    precision_meters: float | None = None
    coordinate_source: str = "openbible"
    modern_name: str | None = None
    modern_country: str | None = None


def _parse_lonlat(lonlat: str | None) -> tuple[float | None, float | None]:
    """Parse a 'lon,lat' string into (latitude, longitude)."""
    if not lonlat:
        return None, None
    try:
        parts = lonlat.split(",")
        if len(parts) == 2:
            lon = float(parts[0].strip())
            lat = float(parts[1].strip())
            return lat, lon
    except (ValueError, IndexError):
        pass
    return None, None


def parse_openbible(sources_dir: Path) -> dict[str, OpenBiblePlace]:
    """Parse OpenBible ancient + modern JSONL files.

    Returns a dict keyed by friendly_id (e.g. 'Jerusalem', 'Mount_Sinai').
    """
    modern_path = sources_dir / "modern.jsonl"
    ancient_path = sources_dir / "ancient.jsonl"

    # First pass: build modern place lookup for coordinates
    modern_places: dict[str, dict] = {}
    if modern_path.exists():
        with open(modern_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                mid = rec.get("id", "")
                modern_places[mid] = rec

    # Second pass: parse ancient places, resolve coords from modern associations
    results: dict[str, OpenBiblePlace] = {}
    if ancient_path.exists():
        with open(ancient_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                friendly_id = rec.get("friendly_id", "")
                if not friendly_id:
                    continue

                place = OpenBiblePlace(friendly_id=friendly_id)

                # Extract types
                place_type = rec.get("type")
                if place_type:
                    place.place_types = [place_type]

                # Try to get coordinates from identifications → resolutions
                best_lat, best_lon, best_confidence = _extract_best_coords(rec)

                # Try modern associations if no direct coords
                if best_lat is None:
                    best_lat, best_lon, modern_name = _resolve_modern_coords(
                        rec, modern_places
                    )
                    if modern_name:
                        place.modern_name = modern_name
                else:
                    # Still try to get modern name
                    _, _, modern_name = _resolve_modern_coords(rec, modern_places)
                    if modern_name:
                        place.modern_name = modern_name

                place.latitude = best_lat
                place.longitude = best_lon
                place.confidence = best_confidence

                results[friendly_id] = place

    return results


def _extract_best_coords(rec: dict) -> tuple[float | None, float | None, float | None]:
    """Extract the best coordinates from identifications → resolutions."""
    identifications = rec.get("identifications", [])
    best_confidence = -1.0
    best_lat = None
    best_lon = None

    for ident in identifications:
        confidence = ident.get("confidence", 0)
        if not isinstance(confidence, (int, float)):
            try:
                confidence = float(confidence)
            except (ValueError, TypeError):
                confidence = 0

        resolutions = ident.get("resolutions", [])
        for res in resolutions:
            lonlat = res.get("lonlat")
            lat, lon = _parse_lonlat(lonlat)
            if lat is not None and confidence > best_confidence:
                best_confidence = confidence
                best_lat = lat
                best_lon = lon

    if best_lat is not None:
        return best_lat, best_lon, best_confidence if best_confidence > 0 else None
    return None, None, None


def _resolve_modern_coords(
    rec: dict, modern_places: dict[str, dict]
) -> tuple[float | None, float | None, str | None]:
    """Resolve coordinates from modern place associations."""
    # Check the extra field for associations
    extra_str = rec.get("extra", "")
    if extra_str and isinstance(extra_str, str):
        try:
            extra = json.loads(extra_str)
            associations = extra.get("modern_associations", {})
        except (json.JSONDecodeError, AttributeError):
            associations = {}
    else:
        associations = {}

    best_score = -1.0
    best_lat = None
    best_lon = None
    best_name = None

    for modern_id, assoc in associations.items():
        score = assoc.get("score", 0)
        if not isinstance(score, (int, float)):
            try:
                score = float(score)
            except (ValueError, TypeError):
                score = 0

        if score > best_score and modern_id in modern_places:
            modern = modern_places[modern_id]
            lat, lon = _parse_lonlat(modern.get("lonlat"))
            if lat is not None:
                best_score = score
                best_lat = lat
                best_lon = lon
                names = modern.get("names", [])
                if names:
                    best_name = names[0].get("name")

    return best_lat, best_lon, best_name
