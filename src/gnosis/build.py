"""Gnosis build pipeline and CLI entry point."""

import argparse
import json
import sys
from pathlib import Path

from rich.console import Console
from rich.progress import Progress

from gnosis.merge.places import merge_places
from gnosis.merge.verse_index import build_verse_index
from gnosis.parsers.dictionaries import link_dictionary_entities, parse_dictionaries
from gnosis.parsers.hebrew_lexicon import parse_hebrew_lexicon
from gnosis.parsers.morphhb import parse_morphhb
from gnosis.parsers.openbible import parse_openbible
from gnosis.parsers.scrollmapper import parse_scrollmapper
from gnosis.parsers.strongs import parse_strongs
from gnosis.parsers.theographic import parse_theographic
from gnosis.parsers.topics import parse_topics
from gnosis.sqlite_writer import write_sqlite
from gnosis.validate.checks import print_results, validate

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SOURCES_DIR = PROJECT_ROOT / "sources"
OUTPUT_DIR = PROJECT_ROOT / "output"

console = Console()


def _parse_all() -> tuple:
    """Parse and merge all sources."""
    people, places, events, groups = parse_theographic(SOURCES_DIR / "theographic")
    openbible_places = parse_openbible(SOURCES_DIR / "openbible")
    places, match_log = merge_places(places, openbible_places)
    cross_refs = parse_scrollmapper(SOURCES_DIR)
    strongs = parse_strongs(SOURCES_DIR)
    dictionary = parse_dictionaries(SOURCES_DIR)
    link_dictionary_entities(dictionary, people, places)
    topics = parse_topics(SOURCES_DIR)
    hebrew_verses = parse_morphhb(SOURCES_DIR)
    lexicon = parse_hebrew_lexicon(SOURCES_DIR)
    return (people, places, events, groups, match_log,
            cross_refs, strongs, dictionary, topics, hebrew_verses, lexicon)


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


def cmd_build(strict: bool = False) -> bool:
    """Run the full build pipeline."""
    console.print("[bold]Gnosis Build Pipeline[/bold]\n")

    with Progress(console=console) as progress:
        task = progress.add_task("Parsing sources...", total=3)

        (people, places, events, groups, match_log,
         cross_refs, strongs, dictionary, topics,
         hebrew_verses, lexicon) = _parse_all()
        progress.update(task, advance=1, description="Building verse index...")

        verse_index = build_verse_index(people, places, events, topics)
        progress.update(task, advance=1, description="Validating...")

        results = validate(
            people, places, events, groups, match_log,
            cross_refs=cross_refs, strongs=strongs,
            dictionary=dictionary, topics=topics,
            hebrew_verses=hebrew_verses, lexicon=lexicon,
            strict=strict,
        )
        progress.update(task, advance=1, description="Done ✓")

    console.print()
    ok = print_results(results)
    console.print()

    if not ok:
        console.print("[red]Validation failed. Output not written.[/red]")
        return False

    # Serialize to JSON dicts keyed by slug ID
    _write_output(
        {k: _compact(v.model_dump()) for k, v in sorted(people.items())},
        "people.json",
    )
    _write_output(
        {k: _compact(v.model_dump()) for k, v in sorted(places.items())},
        "places.json",
    )
    _write_output(
        {k: _compact(v.model_dump()) for k, v in sorted(events.items())},
        "events.json",
    )
    _write_output(
        {k: _compact(v.model_dump()) for k, v in sorted(groups.items())},
        "people-groups.json",
    )
    _write_output(
        {k: v.model_dump() for k, v in sorted(verse_index.items())},
        "verse-index.json",
    )
    _write_output(
        {k: _compact(v.model_dump()) for k, v in sorted(cross_refs.items())},
        "cross-references.json",
    )
    _write_output(
        {k: _compact(v.model_dump()) for k, v in sorted(strongs.items())},
        "strongs.json",
    )
    _write_output(
        {k: _compact(v.model_dump()) for k, v in sorted(dictionary.items())},
        "dictionary.json",
    )
    _write_output(
        {k: _compact(v.model_dump()) for k, v in sorted(topics.items())},
        "topics.json",
    )
    _write_output(
        {k: _compact(v.model_dump()) for k, v in sorted(hebrew_verses.items())},
        "hebrew-words.json",
    )
    _write_output(
        {k: _compact(v.model_dump()) for k, v in sorted(lexicon.items())},
        "lexicon.json",
    )

    db_path = write_sqlite(
        people, places, events, groups, cross_refs, strongs, dictionary,
        topics, hebrew_verses, lexicon, OUTPUT_DIR,
    )
    console.print(f"  Wrote {db_path.name}")

    console.print("\n[bold green]Build complete.[/bold green]")
    return True


def cmd_validate(strict: bool = False) -> bool:
    """Run validation only (no output written)."""
    console.print("[bold]Gnosis Validation[/bold]\n")

    (people, places, events, groups, match_log,
     cross_refs, strongs, dictionary, topics,
     hebrew_verses, lexicon) = _parse_all()
    results = validate(
        people, places, events, groups, match_log,
        cross_refs=cross_refs, strongs=strongs,
        dictionary=dictionary, topics=topics,
        hebrew_verses=hebrew_verses, lexicon=lexicon,
        strict=strict,
    )
    return print_results(results)


def main() -> None:
    parser = argparse.ArgumentParser(prog="gnosis", description="Gnosis biblical knowledge graph")
    subparsers = parser.add_subparsers(dest="command")

    build_parser = subparsers.add_parser("build", help="Run full build pipeline")
    build_parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")

    validate_parser = subparsers.add_parser("validate", help="Run validation only")
    validate_parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")

    args = parser.parse_args()

    if args.command == "build":
        ok = cmd_build(strict=args.strict)
    elif args.command == "validate":
        ok = cmd_validate(strict=args.strict)
    else:
        parser.print_help()
        sys.exit(1)

    sys.exit(0 if ok else 1)
