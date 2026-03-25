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
from gnosis.parsers.hebrew_lexicon import parse_hebrew_lexicon
from gnosis.parsers.kjv import parse_kjv
from gnosis.parsers.morphhb import parse_morphhb
from gnosis.parsers.openbible import parse_openbible
from gnosis.parsers.scrollmapper import parse_scrollmapper
from gnosis.parsers.strongs import parse_strongs
from gnosis.parsers.theographic import parse_theographic
from gnosis.parsers.topics import parse_topics
from gnosis.sqlite_writer import write_sqlite
from gnosis.types import Event, PeopleGroup, Person, Place
from gnosis.types.cross_reference import CrossReferenceEntry
from gnosis.types.dictionary import DictionaryEntry
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
    kjv_verses: dict[str, str]


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


def _parse_all() -> BuildContext:
    """Parse and merge all sources."""
    people, places, events, groups = parse_theographic(SOURCES_DIR / "theographic")
    _repair_people(people)
    openbible_places = parse_openbible(SOURCES_DIR / "openbible")
    places, match_log = merge_places(places, openbible_places)
    cross_refs = parse_scrollmapper(SOURCES_DIR)
    strongs = parse_strongs(SOURCES_DIR)
    dictionary = parse_dictionaries(SOURCES_DIR)
    link_dictionary_entities(dictionary, people, places)
    topics = parse_topics(SOURCES_DIR)
    hebrew_verses = parse_morphhb(SOURCES_DIR)
    lexicon = parse_hebrew_lexicon(SOURCES_DIR)
    kjv_verses = parse_kjv(SOURCES_DIR)
    return BuildContext(
        people=people, places=places, events=events, groups=groups,
        match_log=match_log, cross_refs=cross_refs, strongs=strongs,
        dictionary=dictionary, topics=topics, hebrew_verses=hebrew_verses,
        lexicon=lexicon, kjv_verses=kjv_verses,
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

    db_path = write_sqlite(ctx, OUTPUT_DIR)
    console.print(f"  Wrote {db_path.name}")

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
