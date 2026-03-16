import json
import re
import unicodedata
import uuid
from pathlib import Path

GNOSIS_NAMESPACE = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")

_SLUG_RE = re.compile(r"[^a-z0-9]+")
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_SLUG_OVERRIDES_PATH = _PROJECT_ROOT / "overrides" / "slug_overrides.json"

_slug_overrides: dict[str, str] | None = None


def _load_slug_overrides() -> dict[str, str]:
    global _slug_overrides
    if _slug_overrides is None:
        if _SLUG_OVERRIDES_PATH.exists():
            _slug_overrides = json.loads(_SLUG_OVERRIDES_PATH.read_text())
        else:
            _slug_overrides = {}
    return _slug_overrides


def slugify(name: str) -> str:
    """Convert a name to a lowercase, hyphenated slug with diacritics stripped."""
    text = unicodedata.normalize("NFKD", name)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = _SLUG_RE.sub("-", text)
    text = text.strip("-")
    return text


def make_uuid(slug: str) -> str:
    """Generate a deterministic UUID v5 from a slug."""
    return str(uuid.uuid5(GNOSIS_NAMESPACE, slug))


def disambiguate(
    name: str,
    records: list[dict],
    id_field: str = "personLookup",
) -> dict[str, str]:
    """Generate unique slugs for a list of records sharing the same name.

    Returns a mapping of upstream ID → unique slug.
    """
    overrides = _load_slug_overrides()
    base_slug = slugify(name)
    result: dict[str, str] = {}
    used_slugs: set[str] = set()

    if len(records) == 1:
        upstream_id = records[0].get(id_field, "")
        slug = overrides.get(upstream_id, base_slug)
        return {upstream_id: slug}

    # First pass: apply overrides
    remaining: list[dict] = []
    for rec in records:
        upstream_id = rec.get(id_field, "")
        if upstream_id in overrides:
            slug = overrides[upstream_id]
            result[upstream_id] = slug
            used_slugs.add(slug)
        else:
            remaining.append(rec)

    # Second pass: patronymic disambiguation
    still_remaining: list[dict] = []
    for rec in remaining:
        upstream_id = rec.get(id_field, "")
        father = rec.get("father")
        if father and isinstance(father, list) and len(father) > 0:
            father_name = father[0] if isinstance(father[0], str) else ""
            if father_name:
                father_slug = slugify(father_name)
                candidate = f"{base_slug}-son-of-{father_slug}"
                if candidate not in used_slugs:
                    result[upstream_id] = candidate
                    used_slugs.add(candidate)
                    continue
        still_remaining.append(rec)

    # Third pass: numeric fallback
    counter = 1
    for rec in still_remaining:
        upstream_id = rec.get(id_field, "")
        if base_slug not in used_slugs:
            result[upstream_id] = base_slug
            used_slugs.add(base_slug)
        else:
            while f"{base_slug}-{counter}" in used_slugs:
                counter += 1
            slug = f"{base_slug}-{counter}"
            result[upstream_id] = slug
            used_slugs.add(slug)
            counter += 1

    return result
