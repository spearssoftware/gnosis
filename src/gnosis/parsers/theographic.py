"""Parser for Theographic Bible Metadata (Airtable export format)."""

import json
import re
from collections import defaultdict
from pathlib import Path

from gnosis.ids import disambiguate, make_uuid, slugify
from gnosis.types import Event, PeopleGroup, Person, Place


def _parse_year(year_str: str | None) -> tuple[int | None, str | None, str | None]:
    """Parse a year string like '1575 BC' into (astronomical_year, display, era).

    Returns (astronomical_int, display_string, era).
    Astronomical years: 1 BC = 0, 2 BC = -1, etc.
    """
    if not year_str or not year_str.strip():
        return None, None, None

    year_str = year_str.strip()
    match = re.match(r"^(-?\d+)\s*(BC|AD|BCE|CE)?$", year_str, re.IGNORECASE)
    if not match:
        return None, year_str, None

    num = int(match.group(1))
    era = (match.group(2) or "").upper()

    if era in ("BC", "BCE"):
        astronomical = -(num - 1)  # 1 BC = 0, 2 BC = -1
        display = f"{num} BC"
        return astronomical, display, "BC"
    elif era in ("AD", "CE"):
        display = f"{num} AD"
        return num, display, "AD"
    else:
        # No era marker — assume positive = AD
        return num, str(num), None


def _load_json(path: Path) -> list[dict]:
    with open(path) as f:
        return json.load(f)


def _build_verse_lookup(sources_dir: Path) -> dict[str, str]:
    """Build a map of Airtable verse record ID → OSIS reference string."""
    verses_path = sources_dir / "verses.json"
    if not verses_path.exists():
        return {}

    records = _load_json(verses_path)
    lookup: dict[str, str] = {}
    for rec in records:
        rec_id = rec["id"]
        fields = rec.get("fields", {})
        # Try common field names for the OSIS reference
        osis = fields.get("osisRef") or fields.get("verseID") or fields.get("verseLookup", "")
        if osis:
            lookup[rec_id] = osis
    return lookup


def _build_easton_lookup(sources_dir: Path) -> dict[str, str]:
    """Build a map of Airtable Easton record ID → definition text."""
    easton_path = sources_dir / "easton.json"
    if not easton_path.exists():
        return {}

    records = _load_json(easton_path)
    lookup: dict[str, str] = {}
    for rec in records:
        rec_id = rec["id"]
        fields = rec.get("fields", {})
        text = fields.get("dictText", "")
        if text:
            lookup[rec_id] = text
    return lookup


def parse_theographic(sources_dir: Path) -> tuple[
    dict[str, Person],
    dict[str, Place],
    dict[str, Event],
    dict[str, PeopleGroup],
]:
    """Parse all Theographic source files. Returns dicts keyed by slug ID."""
    verse_lookup = _build_verse_lookup(sources_dir)
    easton_lookup = _build_easton_lookup(sources_dir)

    # --- Pass 1: Build Airtable ID → slug mappings ---
    people_raw = _load_json(sources_dir / "people.json")
    places_raw = _load_json(sources_dir / "places.json")
    events_raw = _load_json(sources_dir / "events.json")
    groups_raw = _load_json(sources_dir / "peopleGroups.json")

    # People: group by name for disambiguation
    people_by_name: dict[str, list[dict]] = defaultdict(list)
    for rec in people_raw:
        fields = rec.get("fields", {})
        name = fields.get("name", fields.get("personLookup", ""))
        if name:
            # Store full record plus Airtable ID for disambiguation
            entry = {**fields, "_airtable_id": rec["id"]}
            people_by_name[name].append(entry)

    # Build person Airtable ID → slug
    person_id_to_slug: dict[str, str] = {}
    for name, records in people_by_name.items():
        id_map = disambiguate(name, records, id_field="_airtable_id")
        person_id_to_slug.update(id_map)

    # Places: slugify placeLookup or kjvName
    place_id_to_slug: dict[str, str] = {}
    place_slugs_seen: dict[str, int] = {}
    for rec in places_raw:
        fields = rec.get("fields", {})
        name = fields.get("kjvName", fields.get("esvName", fields.get("placeLookup", "")))
        slug = slugify(name) if name else f"place-{rec['id']}"
        if slug in place_slugs_seen:
            place_slugs_seen[slug] += 1
            slug = f"{slug}-{place_slugs_seen[slug]}"
        else:
            place_slugs_seen[slug] = 1
        place_id_to_slug[rec["id"]] = slug

    # Events: slugify title
    event_id_to_slug: dict[str, str] = {}
    event_slugs_seen: dict[str, int] = {}
    for rec in events_raw:
        fields = rec.get("fields", {})
        title = fields.get("title", f"event-{rec['id']}")
        slug = slugify(title)
        if slug in event_slugs_seen:
            event_slugs_seen[slug] += 1
            slug = f"{slug}-{event_slugs_seen[slug]}"
        else:
            event_slugs_seen[slug] = 1
        event_id_to_slug[rec["id"]] = slug

    # People groups: slugify groupName
    group_id_to_slug: dict[str, str] = {}
    for rec in groups_raw:
        fields = rec.get("fields", {})
        name = fields.get("groupName", f"group-{rec['id']}")
        slug = slugify(name)
        group_id_to_slug[rec["id"]] = slug

    def resolve_refs(ids: list | None, lookup: dict[str, str]) -> list[str]:
        if not ids:
            return []
        return [lookup[rid] for rid in ids if rid in lookup]

    def resolve_single(ids: list | None, lookup: dict[str, str]) -> str | None:
        if not ids:
            return None
        for rid in ids:
            if rid in lookup:
                return lookup[rid]
        return None

    # --- Pass 2: Build entities with resolved cross-refs ---

    people: dict[str, Person] = {}
    for rec in people_raw:
        airtable_id = rec["id"]
        if airtable_id not in person_id_to_slug:
            continue
        slug = person_id_to_slug[airtable_id]
        fields = rec.get("fields", {})

        birth_year, birth_display, birth_era = _parse_year(fields.get("birthYear"))
        death_year, death_display, death_era = _parse_year(fields.get("deathYear"))

        # Extract name meaning from Easton's
        name_meaning = None
        easton_ids = fields.get("eastons", [])
        if easton_ids:
            texts = [easton_lookup[eid] for eid in easton_ids if eid in easton_lookup]
            if texts:
                name_meaning = texts[0]

        verses = resolve_refs(fields.get("verses"), verse_lookup)

        person = Person(
            id=slug,
            uuid=make_uuid(slug),
            name=fields.get("name", fields.get("personLookup", "")),
            gender=fields.get("gender"),
            birth_year=birth_year,
            death_year=death_year,
            birth_year_display=birth_display,
            birth_era=birth_era,
            death_year_display=death_display,
            death_era=death_era,
            birth_place=resolve_single(fields.get("birthPlace"), place_id_to_slug),
            death_place=resolve_single(fields.get("deathPlace"), place_id_to_slug),
            father=resolve_single(fields.get("father"), person_id_to_slug),
            mother=resolve_single(fields.get("mother"), person_id_to_slug),
            siblings=resolve_refs(fields.get("siblings"), person_id_to_slug),
            children=resolve_refs(fields.get("children"), person_id_to_slug),
            partners=resolve_refs(fields.get("partners"), person_id_to_slug),
            verses=verses,
            verse_count=fields.get("verseCount", len(verses)),
            name_meaning=name_meaning,
            role=None,
            narrative_arc=None,
            first_mention=verses[0] if verses else None,
            people_groups=resolve_refs(fields.get("memberOf"), group_id_to_slug),
            theographic_id=airtable_id,
            status=fields.get("status"),
        )
        people[slug] = person

    places: dict[str, Place] = {}
    for rec in places_raw:
        airtable_id = rec["id"]
        if airtable_id not in place_id_to_slug:
            continue
        slug = place_id_to_slug[airtable_id]
        fields = rec.get("fields", {})

        lat = _try_float(fields.get("latitude"))
        lon = _try_float(fields.get("longitude"))

        verses = resolve_refs(fields.get("verses"), verse_lookup)

        place = Place(
            id=slug,
            uuid=make_uuid(slug),
            name=fields.get("placeLookup", fields.get("kjvName", "")),
            kjv_name=fields.get("kjvName"),
            esv_name=fields.get("esvName"),
            latitude=lat,
            longitude=lon,
            coordinate_source="theographic" if lat is not None else None,
            feature_type=fields.get("featureType"),
            feature_sub_type=fields.get("featureSubType"),
            verses=verses,
            people_born=[],
            people_died=[],
            events=[],
            theographic_id=airtable_id,
            status=fields.get("status"),
        )
        places[slug] = place

    # Back-fill people_born/people_died on places
    for person in people.values():
        if person.birth_place and person.birth_place in places:
            places[person.birth_place].people_born.append(person.id)
        if person.death_place and person.death_place in places:
            places[person.death_place].people_died.append(person.id)

    events: dict[str, Event] = {}
    for rec in events_raw:
        airtable_id = rec["id"]
        if airtable_id not in event_id_to_slug:
            continue
        slug = event_id_to_slug[airtable_id]
        fields = rec.get("fields", {})

        start_year, start_display, start_era = _parse_year(fields.get("startDate"))

        verses = resolve_refs(fields.get("verses"), verse_lookup)

        event = Event(
            id=slug,
            uuid=make_uuid(slug),
            title=fields.get("title", ""),
            start_year=start_year,
            start_year_display=start_display,
            start_era=start_era,
            duration=fields.get("duration"),
            sort_key=fields.get("sortKey"),
            participants=resolve_refs(fields.get("participants"), person_id_to_slug),
            locations=[],
            verses=verses,
            parent_event=None,
            predecessor=None,
            theographic_id=airtable_id,
            status=fields.get("status"),
        )
        events[slug] = event

    # Back-fill events on places (via event participants → locations mapping not in data,
    # we'd need verse-location mapping which is complex — skip for now)

    groups: dict[str, PeopleGroup] = {}
    for rec in groups_raw:
        airtable_id = rec["id"]
        if airtable_id not in group_id_to_slug:
            continue
        slug = group_id_to_slug[airtable_id]
        fields = rec.get("fields", {})

        group = PeopleGroup(
            id=slug,
            uuid=make_uuid(slug),
            name=fields.get("groupName", ""),
            members=resolve_refs(fields.get("members"), person_id_to_slug),
            verses=[],
            theographic_id=airtable_id,
        )
        groups[slug] = group

    return people, places, events, groups


def _try_float(val: str | float | None) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None
