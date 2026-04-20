"""Gnosis build pipeline and CLI entry point."""

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console
from rich.progress import Progress

from gnosis.merge.places import merge_places
from gnosis.merge.verse_index import build_verse_index
from gnosis.parsers.dictionaries import link_dictionary_entities, parse_dictionaries
from gnosis.parsers.dodson import parse_dodson
from gnosis.parsers.hebrew_lexicon import parse_hebrew_lexicon
from gnosis.parsers.kjv import parse_kjv
from gnosis.parsers.macula_greek import parse_macula_greek
from gnosis.parsers.morphhb import parse_morphhb
from gnosis.parsers.openbible import parse_openbible
from gnosis.parsers.scrollmapper import parse_scrollmapper
from gnosis.parsers.strongs import parse_strongs
from gnosis.parsers.theographic import display_year, parse_theographic, parse_verse_years
from gnosis.parsers.topics import parse_topics
from gnosis.sqlite_writer import write_sqlite
from gnosis.types import Event, PeopleGroup, Person, Place
from gnosis.types.cross_reference import CrossReferenceEntry
from gnosis.types.dictionary import DictionaryEntry
from gnosis.types.greek import GreekLexiconEntry, GreekVerse
from gnosis.types.hebrew import HebrewVerse, LexiconEntry
from gnosis.types.strongs import StrongsEntry
from gnosis.types.topic import Topic
from gnosis.validate.checks import print_results, validate

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SOURCES_DIR = PROJECT_ROOT / "sources"
OUTPUT_DIR = PROJECT_ROOT / "output"

console = Console()


@dataclass
class BuildContext:
    people: dict[str, Person]
    places: dict[str, Place]
    events: dict[str, Event]
    groups: dict[str, PeopleGroup]
    match_log: dict[str, str]
    cross_refs: dict[str, CrossReferenceEntry]
    strongs: dict[str, StrongsEntry]
    dictionary: dict[str, DictionaryEntry]
    topics: dict[str, Topic]
    hebrew_verses: dict[str, HebrewVerse]
    lexicon: dict[str, LexiconEntry]
    greek_verses: dict[str, GreekVerse]
    greek_lexicon: dict[str, GreekLexiconEntry]
    kjv_verses: dict[str, str]
    chapter_timeline: dict[str, dict]


def _repair_people(people: dict[str, Person]) -> None:
    """Fix known relationship asymmetries and chronological errors in-place."""
    for pid, person in people.items():
        # Fix parent -> child symmetry: if child lists a parent, ensure parent lists child
        for parent_field in ("father", "mother"):
            parent_id = getattr(person, parent_field)
            if parent_id and parent_id in people:
                parent = people[parent_id]
                if pid not in parent.children:
                    parent.children.append(pid)

        # Fix child -> parent symmetry: if parent lists child, ensure child has parent set
        for child_id in person.children:
            if child_id in people:
                child = people[child_id]
                if child.father != pid and child.mother != pid:
                    # Assign based on parent's gender, default to father
                    if person.gender and person.gender.lower() in ("f", "female"):
                        child.mother = pid
                    else:
                        child.father = pid

        # Fix sibling symmetry
        for sib_id in person.siblings:
            if sib_id in people:
                sibling = people[sib_id]
                if pid not in sibling.siblings:
                    sibling.siblings.append(pid)

        # Fix partner symmetry
        for partner_id in person.partners:
            if partner_id in people:
                partner = people[partner_id]
                if pid not in partner.partners:
                    partner.partners.append(pid)

        # Null out clearly wrong dates (birth >= death)
        if person.birth_year is not None and person.death_year is not None:
            if person.birth_year >= person.death_year:
                person.birth_year = None
                person.death_year = None
                person.birth_year_display = None
                person.death_year_display = None

    # Second pass: fix parent born after child by nulling parent's birth year
    for person in people.values():
        for parent_field in ("father", "mother"):
            parent_id = getattr(person, parent_field)
            if parent_id and parent_id in people:
                parent = people[parent_id]
                if (
                    person.birth_year is not None
                    and parent.birth_year is not None
                    and parent.birth_year >= person.birth_year
                ):
                    parent.birth_year = None
                    parent.birth_year_display = None


def _apply_supplements(people: dict[str, Person]) -> None:
    """Apply curated birth/death years. Only fills gaps; never overrides Theographic values."""
    path = SOURCES_DIR / "supplements" / "people-dates.json"
    if not path.exists():
        return
    with open(path) as f:
        supplements = json.load(f)
    for slug, data in supplements.items():
        if slug not in people:
            continue
        person = people[slug]
        birth = data.get("birth_year")
        applied = False
        if person.birth_year is None and birth is not None:
            person.birth_year = birth
            person.birth_year_display = display_year(birth)
            applied = True
        death = data.get("death_year")
        if person.death_year is None and death is not None:
            person.death_year = death
            person.death_year_display = display_year(death)
            applied = True
        if applied:
            confidence = data.get("confidence")
            if confidence:
                person.dates_confidence = confidence
            source = data.get("source")
            if source:
                person.dates_source = source


def _apply_event_supplements(events: dict[str, Event]) -> None:
    """Apply curated event dates; overrides Theographic (corrects wrong dates, spreads pile-ups)."""
    path = SOURCES_DIR / "supplements" / "events-dates.json"
    if not path.exists():
        return
    with open(path) as f:
        supplements = json.load(f)
    for slug, data in supplements.items():
        if slug not in events:
            continue
        event = events[slug]
        applied = False
        start = data.get("start_year")
        if start is not None:
            event.start_year = start
            event.start_year_display = display_year(start)
            applied = True
        end = data.get("end_year")
        if end is not None:
            event.end_year = end
            event.end_year_display = display_year(end)
            applied = True
        if applied:
            confidence = data.get("confidence")
            if confidence:
                event.dates_confidence = confidence
            source = data.get("source")
            if source:
                event.dates_source = source


def _recompute_year_ranges(
    people: dict[str, Person], events: dict[str, Event],
) -> None:
    """Recompute earliest/latest year mentioned from event dates."""
    verse_range: dict[str, tuple[int, int]] = {}
    for event in events.values():
        if event.start_year is None:
            continue
        for v in event.verses:
            if v in verse_range:
                lo, hi = verse_range[v]
                verse_range[v] = (min(lo, event.start_year), max(hi, event.start_year))
            else:
                verse_range[v] = (event.start_year, event.start_year)

    for person in people.values():
        min_year = None
        max_year = None
        for v in person.verses:
            if v in verse_range:
                lo, hi = verse_range[v]
                min_year = lo if min_year is None else min(min_year, lo)
                max_year = hi if max_year is None else max(max_year, hi)
        if min_year is None:
            continue
        if person.earliest_year_mentioned is None or min_year < person.earliest_year_mentioned:
            person.earliest_year_mentioned = min_year
            person.earliest_year_mentioned_display = display_year(min_year)
        if person.latest_year_mentioned is None or max_year > person.latest_year_mentioned:
            person.latest_year_mentioned = max_year
            person.latest_year_mentioned_display = display_year(max_year)


def _compute_end_years(events: dict[str, Event]) -> None:
    """Compute end_year from start_year + duration for events with year-scale durations."""
    import re
    for event in events.values():
        if event.start_year is None or event.end_year is not None or not event.duration:
            continue
        m = re.match(r"^(\d+(?:\.\d+)?)Y", event.duration)
        if not m:
            continue
        years = int(float(m.group(1)))
        if years > 0:
            event.end_year = event.start_year + years
            event.end_year_display = display_year(event.end_year)


def _build_chapter_timeline(
    verse_years: dict[str, int], events: dict[str, Event],
) -> dict[str, dict]:
    """Build chapter-level timeline, preferring event start_year over verse yearNum.

    Theographic's verses.json yearNum is inconsistent with events.json in places
    (e.g. Passion Week: events at 30 AD, verses at 33 AD). When a verse is attached
    to a dated event, trust the event's start_year as the authoritative date.
    """
    from collections import Counter
    verse_to_event_year: dict[str, int] = {}
    for event in events.values():
        if event.start_year is None:
            continue
        for v in event.verses:
            verse_to_event_year.setdefault(v, event.start_year)

    chapters: dict[str, list[int]] = {}
    for ref, year in verse_years.items():
        parts = ref.split(".")
        if len(parts) < 2:
            continue
        chapter_ref = f"{parts[0]}.{parts[1]}"
        chapters.setdefault(chapter_ref, []).append(verse_to_event_year.get(ref, year))

    result: dict[str, dict] = {}
    for ch_ref, years in sorted(chapters.items()):
        mode_year = Counter(years).most_common(1)[0][0]
        result[ch_ref] = {"year": mode_year, "year_display": display_year(mode_year)}
    return result


def _parse_all() -> BuildContext:
    """Parse and merge all sources."""
    people, places, events, groups = parse_theographic(SOURCES_DIR / "theographic")
    _repair_people(people)
    _apply_supplements(people)
    _apply_event_supplements(events)
    _recompute_year_ranges(people, events)
    _compute_end_years(events)
    openbible_places = parse_openbible(SOURCES_DIR / "openbible")
    places, match_log = merge_places(places, openbible_places)
    cross_refs = parse_scrollmapper(SOURCES_DIR)
    strongs = parse_strongs(SOURCES_DIR)
    dictionary = parse_dictionaries(SOURCES_DIR)
    link_dictionary_entities(dictionary, people, places)
    topics = parse_topics(SOURCES_DIR)
    hebrew_verses = parse_morphhb(SOURCES_DIR)
    lexicon = parse_hebrew_lexicon(SOURCES_DIR)
    greek_verses = parse_macula_greek(SOURCES_DIR)
    greek_lexicon = parse_dodson(SOURCES_DIR)
    kjv_verses = parse_kjv(SOURCES_DIR)
    verse_years = parse_verse_years(SOURCES_DIR)
    chapter_timeline = _build_chapter_timeline(verse_years, events)
    return BuildContext(
        people=people, places=places, events=events, groups=groups,
        match_log=match_log, cross_refs=cross_refs, strongs=strongs,
        dictionary=dictionary, topics=topics, hebrew_verses=hebrew_verses,
        lexicon=lexicon, greek_verses=greek_verses,
        greek_lexicon=greek_lexicon, kjv_verses=kjv_verses,
        chapter_timeline=chapter_timeline,
    )


def _compact(data: dict) -> dict:
    """Remove None values and empty collections from a dict."""
    return {k: v for k, v in data.items() if v is not None and v != [] and v != ""}


def _write_output(data: dict, filename: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / filename
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    console.print(f"  Wrote {path.name} ({len(data)} entries)")


_OUTPUTS: list[tuple[str, str, bool]] = [
    ("people", "people.json", True),
    ("places", "places.json", True),
    ("events", "events.json", True),
    ("groups", "people-groups.json", True),
    ("cross_refs", "cross-references.json", True),
    ("strongs", "strongs.json", True),
    ("dictionary", "dictionary.json", True),
    ("topics", "topics.json", True),
    ("hebrew_verses", "hebrew-words.json", True),
    ("lexicon", "lexicon.json", True),
    ("greek_verses", "greek-words.json", True),
    ("greek_lexicon", "greek-lexicon.json", True),
]


def cmd_build(strict: bool = False, no_vectors: bool = False) -> bool:
    """Run the full build pipeline."""
    console.print("[bold]Gnosis Build Pipeline[/bold]\n")

    with Progress(console=console) as progress:
        task = progress.add_task("Parsing sources...", total=3)

        ctx = _parse_all()
        progress.update(task, advance=1, description="Building verse index...")

        verse_index = build_verse_index(ctx.people, ctx.places, ctx.events, ctx.topics)
        progress.update(task, advance=1, description="Validating...")

        results = validate(ctx, strict=strict)
        progress.update(task, advance=1, description="Done ✓")

    console.print()
    ok = print_results(results)
    console.print()

    if not ok:
        console.print("[red]Validation failed. Output not written.[/red]")
        return False

    for attr, filename, compact in _OUTPUTS:
        data = getattr(ctx, attr)
        serialized = {
            k: (_compact(v.model_dump()) if compact else v.model_dump())
            for k, v in data.items()
        }
        _write_output(serialized, filename)

    _write_output(
        {k: v.model_dump() for k, v in verse_index.items()},
        "verse-index.json",
    )
    _write_output(ctx.chapter_timeline, "chapter-timeline.json")

    db_path = write_sqlite(ctx, OUTPUT_DIR)
    console.print(f"  Wrote {db_path.name}")
    lite_db_path = write_sqlite(ctx, OUTPUT_DIR, lite=True)
    console.print(f"  Wrote {lite_db_path.name}")

    if not no_vectors:
        try:
            from gnosis.vector import build_vector_index

            vector_path = build_vector_index(ctx, OUTPUT_DIR, db_path)
            console.print(f"  Wrote {vector_path.name}")
        except ImportError:
            console.print(
                "  [yellow]Skipping vectors (install with: uv sync --extra vectors)[/yellow]"
            )

    console.print("\n[bold green]Build complete.[/bold green]")
    return True


def cmd_validate(strict: bool = False) -> bool:
    """Run validation only (no output written)."""
    console.print("[bold]Gnosis Validation[/bold]\n")

    ctx = _parse_all()
    results = validate(ctx, strict=strict)
    return print_results(results)


def main() -> None:
    parser = argparse.ArgumentParser(prog="gnosis", description="Gnosis biblical knowledge graph")
    subparsers = parser.add_subparsers(dest="command")

    build_parser = subparsers.add_parser("build", help="Run full build pipeline")
    build_parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    build_parser.add_argument("--no-vectors", action="store_true", help="Skip vector index build")

    validate_parser = subparsers.add_parser("validate", help="Run validation only")
    validate_parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")

    args = parser.parse_args()

    if args.command == "build":
        ok = cmd_build(strict=args.strict, no_vectors=args.no_vectors)
    elif args.command == "validate":
        ok = cmd_validate(strict=args.strict)
    else:
        parser.print_help()
        sys.exit(1)

    sys.exit(0 if ok else 1)
