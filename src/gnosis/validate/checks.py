"""Validation checks for the Gnosis knowledge graph."""

import re
from dataclasses import dataclass, field
from typing import Literal

from rich.console import Console
from rich.table import Table

from gnosis.types import Event, PeopleGroup, Person, Place
from gnosis.types.cross_reference import CrossReferenceEntry

OSIS_PATTERN = re.compile(
    r"^[A-Z1-9][A-Za-z]+\.\d{1,3}\.\d{1,3}(-\d{1,3})?$"
)


@dataclass
class ValidationResult:
    name: str
    status: Literal["pass", "warn", "fail"]
    message: str
    details: list[str] = field(default_factory=list)


def validate(
    people: dict[str, Person],
    places: dict[str, Place],
    events: dict[str, Event],
    groups: dict[str, PeopleGroup],
    match_log: dict[str, str] | None = None,
    cross_refs: dict[str, CrossReferenceEntry] | None = None,
    strict: bool = False,
) -> list[ValidationResult]:
    """Run all validation checks. Returns list of results."""
    results: list[ValidationResult] = []

    # 1. Dangling cross-refs
    results.append(_check_dangling_refs(people, places, events, groups))

    # 2. OSIS format validation
    results.append(_check_osis_format(people, places, events))

    # 3. WIP entry detection
    results.append(_check_wip_entries(people, places, events, strict))

    # 4. Place merge coverage
    if match_log:
        results.append(_check_place_coverage(match_log))

    # 5. Cross-reference validation
    if cross_refs is not None:
        results.append(_check_cross_refs(cross_refs))

    # 6. Basic entity counts
    xref_count = sum(len(e.targets) for e in cross_refs.values()) if cross_refs else 0
    results.append(ValidationResult(
        name="Entity counts",
        status="pass",
        message=(
            f"{len(people)} people, {len(places)} places, "
            f"{len(events)} events, {len(groups)} groups, "
            f"{xref_count} cross-refs"
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

    for pid, person in people.items():
        for v in person.verses:
            total += 1
            if not OSIS_PATTERN.match(v):
                invalid.append(f"person/{pid}: {v}")
    for plid, place in places.items():
        for v in place.verses:
            total += 1
            if not OSIS_PATTERN.match(v):
                invalid.append(f"place/{plid}: {v}")
    for eid, event in events.items():
        for v in event.verses:
            total += 1
            if not OSIS_PATTERN.match(v):
                invalid.append(f"event/{eid}: {v}")

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
    for pid, p in people.items():
        if p.status and p.status.lower() in ("wip", "draft", "incomplete"):
            wip.append(f"person/{pid}: {p.status}")
    for plid, p in places.items():
        if p.status and p.status.lower() in ("wip", "draft", "incomplete"):
            wip.append(f"place/{plid}: {p.status}")
    for eid, e in events.items():
        if e.status and e.status.lower() in ("wip", "draft", "incomplete"):
            wip.append(f"event/{eid}: {e.status}")

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
