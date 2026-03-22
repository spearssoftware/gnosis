"""Validation checks for the Gnosis knowledge graph."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from rich.console import Console
from rich.table import Table

from gnosis.osis import is_valid_osis_ref
from gnosis.types import Event, PeopleGroup, Person, Place
from gnosis.types.cross_reference import CrossReferenceEntry
from gnosis.types.dictionary import DictionaryEntry
from gnosis.types.hebrew import HebrewVerse, LexiconEntry
from gnosis.types.strongs import StrongsEntry
from gnosis.types.topic import Topic

if TYPE_CHECKING:
    from gnosis.build import BuildContext

OSIS_PATTERN = re.compile(
    r"^[A-Z1-9][A-Za-z]+\.\d{1,3}\.\d{1,3}(-\d{1,3})?$"
)

_WIP_STATUSES = ("wip", "draft", "incomplete")


@dataclass
class ValidationResult:
    name: str
    status: Literal["pass", "warn", "fail"]
    message: str
    details: list[str] = field(default_factory=list)


def validate(
    ctx: BuildContext,
    strict: bool = False,
) -> list[ValidationResult]:
    """Run all validation checks. Returns list of results."""
    results: list[ValidationResult] = []

    results.append(_check_dangling_refs(ctx.people, ctx.places, ctx.events, ctx.groups))
    results.append(_check_osis_format(ctx.people, ctx.places, ctx.events))
    results.append(_check_wip_entries(ctx.people, ctx.places, ctx.events, strict))

    if ctx.match_log:
        results.append(_check_place_coverage(ctx.match_log))

    results.append(_check_cross_refs(ctx.cross_refs))
    results.append(_check_strongs(ctx.strongs))
    results.append(_check_dictionary(ctx.dictionary))
    results.append(_check_topics(ctx.topics))
    results.append(_check_hebrew(ctx.hebrew_verses, ctx.lexicon))
    results.append(_check_verse_existence(
        ctx.people, ctx.places, ctx.events,
        ctx.cross_refs, ctx.dictionary, ctx.topics, ctx.hebrew_verses,
    ))
    results.append(_check_relationship_symmetry(ctx.people))
    results.append(_check_chronology(ctx.people, ctx.events))

    xref_count = sum(len(e.targets) for e in ctx.cross_refs.values())
    hebrew_count = sum(len(v.words) for v in ctx.hebrew_verses.values())
    results.append(ValidationResult(
        name="Entity counts",
        status="pass",
        message=(
            f"{len(ctx.people)} people, {len(ctx.places)} places, "
            f"{len(ctx.events)} events, {len(ctx.groups)} groups, "
            f"{xref_count} cross-refs, {len(ctx.strongs)} strongs, "
            f"{len(ctx.dictionary)} dictionary, {len(ctx.topics)} topics, "
            f"{hebrew_count} hebrew words, {len(ctx.lexicon)} lexicon"
        ),
    ))

    return results


def print_results(results: list[ValidationResult]) -> bool:
    """Print validation results as a Rich table. Returns True if all passed."""
    console = Console()
    table = Table(title="Gnosis Validation")
    table.add_column("Check", style="bold")
    table.add_column("Status")
    table.add_column("Message")

    icon = {"pass": "[green]PASS[/]", "warn": "[yellow]WARN[/]", "fail": "[red]FAIL[/]"}
    has_failures = False

    for r in results:
        table.add_row(r.name, icon.get(r.status, r.status), r.message)
        if r.details:
            for detail in r.details[:10]:
                table.add_row("", "", f"  {detail}")
            if len(r.details) > 10:
                table.add_row("", "", f"  ... and {len(r.details) - 10} more")
        if r.status == "fail":
            has_failures = True

    console.print(table)
    return not has_failures


def _check_dangling_refs(
    people: dict[str, Person],
    places: dict[str, Place],
    events: dict[str, Event],
    groups: dict[str, PeopleGroup],
) -> ValidationResult:
    people_ids = set(people.keys())
    place_ids = set(places.keys())
    event_ids = set(events.keys())
    group_ids = set(groups.keys())
    dangling: list[str] = []

    for pid, person in people.items():
        for ref_field, ref_val in [
            ("father", person.father),
            ("mother", person.mother),
        ]:
            if ref_val and ref_val not in people_ids:
                dangling.append(f"person/{pid}.{ref_field} → {ref_val}")
        for ref_field, ref_val in [
            ("birth_place", person.birth_place),
            ("death_place", person.death_place),
        ]:
            if ref_val and ref_val not in place_ids:
                dangling.append(f"person/{pid}.{ref_field} → {ref_val}")
        for ref in person.siblings + person.children + person.partners:
            if ref not in people_ids:
                dangling.append(f"person/{pid}.relations → {ref}")
        for ref in person.people_groups:
            if ref not in group_ids:
                dangling.append(f"person/{pid}.people_groups → {ref}")

    for eid, event in events.items():
        for ref in event.participants:
            if ref not in people_ids:
                dangling.append(f"event/{eid}.participants → {ref}")
        for ref in event.locations:
            if ref not in place_ids:
                dangling.append(f"event/{eid}.locations → {ref}")
        if event.parent_event and event.parent_event not in event_ids:
            dangling.append(f"event/{eid}.parent_event → {event.parent_event}")

    for gid, group in groups.items():
        for ref in group.members:
            if ref not in people_ids:
                dangling.append(f"group/{gid}.members → {ref}")

    if dangling:
        return ValidationResult(
            name="Dangling refs",
            status="warn",
            message=f"{len(dangling)} dangling cross-references",
            details=dangling,
        )
    return ValidationResult(name="Dangling refs", status="pass", message="All refs resolve")


def _check_osis_format(
    people: dict[str, Person],
    places: dict[str, Place],
    events: dict[str, Event],
) -> ValidationResult:
    invalid: list[str] = []
    total = 0

    for label, collection in [("person", people), ("place", places), ("event", events)]:
        for eid, entity in collection.items():
            for v in entity.verses:
                total += 1
                if not OSIS_PATTERN.match(v):
                    invalid.append(f"{label}/{eid}: {v}")

    if invalid:
        return ValidationResult(
            name="OSIS format",
            status="warn",
            message=f"{len(invalid)}/{total} verse refs have non-standard format",
            details=invalid,
        )
    return ValidationResult(
        name="OSIS format",
        status="pass",
        message=f"All {total} verse refs valid",
    )


def _check_wip_entries(
    people: dict[str, Person],
    places: dict[str, Place],
    events: dict[str, Event],
    strict: bool,
) -> ValidationResult:
    wip: list[str] = []
    for label, collection in [("person", people), ("place", places), ("event", events)]:
        for eid, entity in collection.items():
            if entity.status and entity.status.lower() in _WIP_STATUSES:
                wip.append(f"{label}/{eid}: {entity.status}")

    if wip:
        return ValidationResult(
            name="WIP entries",
            status="fail" if strict else "warn",
            message=f"{len(wip)} entries with WIP status",
            details=wip,
        )
    return ValidationResult(name="WIP entries", status="pass", message="No WIP entries")


def _check_place_coverage(match_log: dict[str, str]) -> ValidationResult:
    counts: dict[str, int] = {"exact": 0, "override": 0, "fuzzy": 0, "unmatched": 0}
    for match_type in match_log.values():
        counts[match_type] = counts.get(match_type, 0) + 1

    total = len(match_log)
    matched = counts["exact"] + counts["override"] + counts["fuzzy"]
    pct = (matched / total * 100) if total > 0 else 0

    return ValidationResult(
        name="Place merge coverage",
        status="pass" if pct >= 50 else "warn",
        message=(
            f"{matched}/{total} ({pct:.0f}%) matched — "
            f"exact: {counts['exact']}, override: {counts['override']}, "
            f"fuzzy: {counts['fuzzy']}, unmatched: {counts['unmatched']}"
        ),
    )


def _check_cross_refs(
    cross_refs: dict[str, CrossReferenceEntry],
) -> ValidationResult:
    invalid: list[str] = []
    self_refs: list[str] = []
    total = 0

    for from_verse, entry in cross_refs.items():
        if not OSIS_PATTERN.match(from_verse):
            invalid.append(f"from: {from_verse}")
        for t in entry.targets:
            total += 1
            if not OSIS_PATTERN.match(t.verse_start):
                invalid.append(f"to: {t.verse_start}")
            if t.verse_end and not OSIS_PATTERN.match(t.verse_end):
                invalid.append(f"to_end: {t.verse_end}")
            if t.verse_start == from_verse and t.verse_end is None:
                self_refs.append(from_verse)

    details = [f"invalid OSIS: {r}" for r in invalid[:5]]
    details += [f"self-ref: {r}" for r in self_refs[:5]]

    if invalid:
        return ValidationResult(
            name="Cross-references",
            status="warn",
            message=(
                f"{len(invalid)} invalid OSIS refs, "
                f"{len(self_refs)} self-refs in {total} cross-refs"
            ),
            details=details,
        )
    return ValidationResult(
        name="Cross-references",
        status="pass",
        message=f"{total} cross-refs across {len(cross_refs)} verses",
    )


_STRONGS_PATTERN = re.compile(r"^[HG]\d+$")


def _check_strongs(strongs: dict[str, StrongsEntry]) -> ValidationResult:
    invalid: list[str] = []
    hebrew = 0
    greek = 0

    for number, entry in strongs.items():
        if not _STRONGS_PATTERN.match(number):
            invalid.append(number)
        if entry.language == "hebrew":
            hebrew += 1
        elif entry.language == "greek":
            greek += 1

    if invalid:
        return ValidationResult(
            name="Strong's concordance",
            status="warn",
            message=f"{len(invalid)} invalid Strong's numbers",
            details=invalid[:10],
        )
    return ValidationResult(
        name="Strong's concordance",
        status="pass",
        message=f"{len(strongs)} entries (H:{hebrew}, G:{greek})",
    )


def _check_dictionary(
    dictionary: dict[str, DictionaryEntry],
) -> ValidationResult:
    invalid_refs: list[str] = []
    empty_defs: list[str] = []
    source_counts: dict[str, int] = {}

    for slug, entry in dictionary.items():
        if not entry.definitions:
            empty_defs.append(slug)
        for defn in entry.definitions:
            source_counts[defn.source] = source_counts.get(defn.source, 0) + 1
        for ref in entry.scripture_refs:
            if not OSIS_PATTERN.match(ref):
                invalid_refs.append(f"{slug}: {ref}")

    details: list[str] = []
    if invalid_refs:
        details.extend(invalid_refs[:5])
    if empty_defs:
        details.append(f"{len(empty_defs)} entries with no definitions")

    sources_str = ", ".join(
        f"{k}:{v}" for k, v in sorted(source_counts.items())
    )

    if invalid_refs:
        return ValidationResult(
            name="Dictionary",
            status="warn",
            message=f"{len(invalid_refs)} invalid refs in {len(dictionary)} entries",
            details=details,
        )
    return ValidationResult(
        name="Dictionary",
        status="pass",
        message=f"{len(dictionary)} entries ({sources_str})",
    )


def _check_topics(topics: dict[str, Topic]) -> ValidationResult:
    dangling_see_also: list[str] = []
    source_counts: dict[str, int] = {}
    total_aspects = 0

    topic_slugs = set(topics.keys())
    for slug, topic in topics.items():
        for src in topic.sources:
            source_counts[src] = source_counts.get(src, 0) + 1
        total_aspects += len(topic.aspects)
        for sa in topic.see_also:
            if sa not in topic_slugs:
                dangling_see_also.append(f"{slug} -> {sa}")

    sources_str = ", ".join(
        f"{k}:{v}" for k, v in sorted(source_counts.items())
    )

    if dangling_see_also:
        return ValidationResult(
            name="Topics",
            status="warn",
            message=(
                f"{len(dangling_see_also)} dangling see_also "
                f"in {len(topics)} topics"
            ),
            details=dangling_see_also[:5],
        )
    return ValidationResult(
        name="Topics",
        status="pass",
        message=(
            f"{len(topics)} topics, {total_aspects} aspects ({sources_str})"
        ),
    )


def _check_hebrew(
    hebrew_verses: dict[str, HebrewVerse],
    lexicon: dict[str, LexiconEntry],
) -> ValidationResult:
    total_words = sum(len(v.words) for v in hebrew_verses.values())
    words_with_strongs = sum(
        1 for v in hebrew_verses.values()
        for w in v.words if w.strongs_number
    )
    pct = (words_with_strongs / total_words * 100) if total_words else 0

    return ValidationResult(
        name="Hebrew Bible",
        status="pass",
        message=(
            f"{len(hebrew_verses)} verses, {total_words} words "
            f"({pct:.0f}% with Strong's), {len(lexicon)} lexicon entries"
        ),
    )


def _validate_ref(ref: str) -> bool:
    """Validate a single OSIS ref or range against the canonical verse table."""
    return OSIS_PATTERN.match(ref) is not None and is_valid_osis_ref(ref)


def _check_verse_existence(
    people: dict[str, Person],
    places: dict[str, Place],
    events: dict[str, Event],
    cross_refs: dict[str, CrossReferenceEntry],
    dictionary: dict[str, DictionaryEntry],
    topics: dict[str, Topic],
    hebrew_verses: dict[str, HebrewVerse],
) -> ValidationResult:
    """Check that all verse references point to real Bible verses."""
    invalid: list[str] = []
    total = 0

    for label, collection in [("person", people), ("place", places), ("event", events)]:
        for eid, entity in collection.items():
            for v in entity.verses:
                total += 1
                if not _validate_ref(v):
                    invalid.append(f"{label}/{eid}: {v}")

    for from_verse, entry in cross_refs.items():
        total += 1
        if not _validate_ref(from_verse):
            invalid.append(f"xref/from: {from_verse}")
        for t in entry.targets:
            total += 1
            if not _validate_ref(t.verse_start):
                invalid.append(f"xref/to: {t.verse_start}")
            if t.verse_end:
                total += 1
                if not _validate_ref(t.verse_end):
                    invalid.append(f"xref/to_end: {t.verse_end}")

    for slug, entry in dictionary.items():
        for ref in entry.scripture_refs:
            total += 1
            if not _validate_ref(ref):
                invalid.append(f"dict/{slug}: {ref}")

    for slug, topic in topics.items():
        for aspect in topic.aspects:
            for v in aspect.verses:
                total += 1
                if not _validate_ref(v):
                    invalid.append(f"topic/{slug}: {v}")

    for ref in hebrew_verses:
        total += 1
        if not _validate_ref(ref):
            invalid.append(f"hebrew: {ref}")

    if invalid:
        return ValidationResult(
            name="Verse existence",
            status="warn",
            message=f"{len(invalid)}/{total} refs point to nonexistent verses",
            details=invalid[:10],
        )
    return ValidationResult(
        name="Verse existence",
        status="pass",
        message=f"All {total} verse refs point to real verses",
    )


def _check_relationship_symmetry(
    people: dict[str, Person],
) -> ValidationResult:
    """Check that family relationships are symmetric."""
    asymmetries: list[str] = []
    people_ids = set(people.keys())

    for pid, person in people.items():
        if person.father and person.father in people_ids:
            father = people[person.father]
            if pid not in father.children:
                asymmetries.append(
                    f"{pid}.father={person.father} but {person.father}.children missing {pid}"
                )

        if person.mother and person.mother in people_ids:
            mother = people[person.mother]
            if pid not in mother.children:
                asymmetries.append(
                    f"{pid}.mother={person.mother} but {person.mother}.children missing {pid}"
                )

        for child_id in person.children:
            if child_id in people_ids:
                child = people[child_id]
                if child.father != pid and child.mother != pid:
                    asymmetries.append(
                        f"{pid}.children has {child_id} but {child_id} has neither parent={pid}"
                    )

        for sib_id in person.siblings:
            if sib_id in people_ids:
                sibling = people[sib_id]
                if pid not in sibling.siblings:
                    asymmetries.append(
                        f"{pid}.siblings has {sib_id} but {sib_id}.siblings missing {pid}"
                    )

        for partner_id in person.partners:
            if partner_id in people_ids:
                partner = people[partner_id]
                if pid not in partner.partners:
                    asymmetries.append(
                        f"{pid}.partners has {partner_id} but {partner_id}.partners missing {pid}"
                    )

    if asymmetries:
        return ValidationResult(
            name="Relationship symmetry",
            status="warn",
            message=f"{len(asymmetries)} asymmetric relationships",
            details=asymmetries[:10],
        )
    return ValidationResult(
        name="Relationship symmetry",
        status="pass",
        message="All relationships are symmetric",
    )


def _check_chronology(
    people: dict[str, Person],
    events: dict[str, Event],
) -> ValidationResult:
    """Check chronological consistency of dates."""
    issues: list[str] = []

    for pid, person in people.items():
        if person.birth_year is not None and person.death_year is not None:
            if person.birth_year >= person.death_year:
                issues.append(
                    f"person/{pid}: birth ({person.birth_year}) >= death ({person.death_year})"
                )

        for parent_field in ("father", "mother"):
            parent_id = getattr(person, parent_field)
            if parent_id and parent_id in people:
                parent = people[parent_id]
                if person.birth_year is not None and parent.birth_year is not None:
                    if parent.birth_year >= person.birth_year:
                        issues.append(
                            f"person/{pid}: {parent_field} {parent_id} born ({parent.birth_year})"
                            f" >= child born ({person.birth_year})"
                        )

    for eid, event in events.items():
        if event.start_year is not None:
            if event.start_year < -4004 or event.start_year > 100:
                issues.append(
                    f"event/{eid}: start_year {event.start_year} outside [-4004, 100]"
                )

    if issues:
        return ValidationResult(
            name="Chronology",
            status="warn",
            message=f"{len(issues)} chronological issues",
            details=issues[:10],
        )
    return ValidationResult(
        name="Chronology",
        status="pass",
        message="All dates are chronologically consistent",
    )
