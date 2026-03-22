"""Parser for neuu-org/bible-topics-dataset."""

import json
import re
from pathlib import Path

from gnosis.ids import make_uuid, slugify
from gnosis.osis import to_osis_range, to_osis_ref
from gnosis.types.topic import Topic, TopicAspect

# Match "Book Chapter:Verse" with optional range/comma suffixes.
# We extract individual verse refs from compound references like "Genesis 4:1-15,25".
_BASE_REF = re.compile(r"^(.+?)\s+(\d+):(.+)$")


def _parse_ref_string(raw: str) -> list[str]:
    """Parse a reference string into a list of OSIS refs.

    Handles:
    - "Genesis 1:1" -> ["Gen.1.1"]
    - "Genesis 4:1-15" -> ["Gen.4.1-15"]
    - "Genesis 4:1-15,25" -> ["Gen.4.1-15", "Gen.4.25"]
    - "Matthew 23:35" -> ["Matt.23.35"]
    """
    raw = raw.strip()
    m = _BASE_REF.match(raw)
    if not m:
        return []

    book, chapter_str, verse_part = m.group(1), m.group(2), m.group(3)
    try:
        chapter = int(chapter_str)
    except ValueError:
        return []

    results: list[str] = []
    for segment in verse_part.split(","):
        segment = segment.strip()
        if not segment:
            continue
        if "-" in segment:
            parts = segment.split("-", 1)
            try:
                v_start = int(parts[0].strip())
                v_end = int(parts[1].strip())
            except ValueError:
                continue
            ref = to_osis_range(book, chapter, v_start, v_end)
            if ref:
                results.append(ref)
        else:
            try:
                verse = int(segment)
            except ValueError:
                continue
            ref = to_osis_ref(book, chapter, verse)
            if ref:
                results.append(ref)

    return results


def parse_topics(sources_dir: Path) -> dict[str, Topic]:
    """Parse all topic JSON files from the 01_parsed layer.

    Returns dict keyed by slug.
    """
    topics_dir = sources_dir / "topics"
    result: dict[str, Topic] = {}

    for letter_dir in sorted(topics_dir.iterdir()):
        if not letter_dir.is_dir():
            continue
        for path in sorted(letter_dir.glob("*.json")):
            raw = json.loads(path.read_text(encoding="utf-8"))
            slug = raw.get("slug") or slugify(raw.get("topic", ""))
            if not slug:
                continue

            aspects: list[TopicAspect] = []
            for asp in raw.get("aspects", []):
                osis_refs: list[str] = []
                for ref_str in asp.get("references", []):
                    osis_refs.extend(_parse_ref_string(ref_str))
                aspects.append(TopicAspect(
                    label=asp.get("label"),
                    verses=osis_refs,
                    source=asp.get("source"),
                ))

            see_also = [slugify(s) for s in raw.get("see_also", []) if s]

            result[slug] = Topic(
                id=slug,
                uuid=make_uuid(f"topic-{slug}"),
                name=raw.get("topic", slug),
                sources=raw.get("sources", []),
                aspects=aspects,
                see_also=see_also,
            )

    return dict(sorted(result.items()))
