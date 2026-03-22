"""Parser for neuu-org/bible-dictionary-dataset."""

import json
import re
from pathlib import Path

from gnosis.ids import make_uuid, slugify
from gnosis.osis import to_osis_ref
from gnosis.types.dictionary import DictionaryDefinition, DictionaryEntry
from gnosis.types.person import Person
from gnosis.types.place import Place

_SOURCES = ("smith", "hastings", "schaff", "hitchcock")

_REF_PATTERN = re.compile(r"^(.+?)\s+(\d+):(\d+)$")


def _convert_ref(reference: str) -> str | None:
    """Convert 'Genesis 1:1' to OSIS ref 'Gen.1.1'."""
    m = _REF_PATTERN.match(reference.strip())
    if not m:
        return None
    book, chapter, verse = m.group(1), int(m.group(2)), int(m.group(3))
    return to_osis_ref(book, chapter, verse)


def _load_source(source_dir: Path) -> dict[str, dict]:
    """Load all per-letter JSON files from a dictionary source directory."""
    entries: dict[str, dict] = {}
    for path in sorted(source_dir.glob("*.json")):
        if path.name.startswith("_"):
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        entries.update(data)
    return entries


def parse_dictionaries(sources_dir: Path) -> dict[str, DictionaryEntry]:
    """Parse all dictionary sources and merge entries sharing the same slug.

    Returns dict keyed by slug.
    """
    dict_dir = sources_dir / "dictionaries"
    merged: dict[str, DictionaryEntry] = {}
    seen_refs: dict[str, set[str]] = {}

    for source_name in _SOURCES:
        source_path = dict_dir / source_name
        if not source_path.exists():
            continue

        raw_entries = _load_source(source_path)

        for raw in raw_entries.values():
            slug = raw.get("slug") or slugify(raw.get("name", ""))
            if not slug:
                continue

            osis_refs: list[str] = []
            for ref_obj in raw.get("scripture_refs", []):
                ref_str = ref_obj.get("reference", "")
                osis = _convert_ref(ref_str)
                if osis:
                    osis_refs.append(osis)

            definitions = [
                DictionaryDefinition(source=d["source"], text=d["text"])
                for d in raw.get("definitions", [])
                if d.get("text")
            ]

            if slug in merged:
                existing = merged[slug]
                existing.definitions.extend(definitions)
                ref_set = seen_refs[slug]
                for ref in osis_refs:
                    if ref not in ref_set:
                        ref_set.add(ref)
                        existing.scripture_refs.append(ref)
            else:
                merged[slug] = DictionaryEntry(
                    id=slug,
                    uuid=make_uuid(f"dict-{slug}"),
                    name=raw.get("name", slug),
                    definitions=definitions,
                    scripture_refs=osis_refs,
                )
                seen_refs[slug] = set(osis_refs)

    return dict(sorted(merged.items()))


def link_dictionary_entities(
    dictionary: dict[str, DictionaryEntry],
    people: dict[str, Person],
    places: dict[str, Place],
) -> None:
    """Populate related_people and related_places on dictionary entries."""
    people_slugs = set(people.keys())
    place_slugs = set(places.keys())

    for entry in dictionary.values():
        if entry.id in people_slugs:
            entry.related_people.append(entry.id)
        if entry.id in place_slugs:
            entry.related_places.append(entry.id)
