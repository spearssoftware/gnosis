"""Parser for scrollmapper/bible_databases cross-reference data."""

import csv
from collections import defaultdict
from pathlib import Path

from gnosis.types.cross_reference import CrossReferenceEntry, CrossReferenceTarget


def _parse_to_verse(raw: str) -> tuple[str, str | None]:
    """Parse a to-verse field which may be a range like 'Prov.8.22-Prov.8.30'.

    Returns (verse_start, verse_end) where verse_end is None for single refs.
    """
    if "-" not in raw:
        return raw, None

    # Ranges are "Book.Ch.V-Book.Ch.V" — split on the dash that separates two OSIS refs.
    # We need to find the dash that's between two refs, not inside a book name.
    # OSIS refs contain dots, so we split on the last occurrence pattern.
    parts = raw.split("-")
    if len(parts) == 2:
        return parts[0], parts[1]

    # Edge case: multiple dashes (shouldn't happen but be safe).
    # Rejoin: first part is everything up to the first complete OSIS ref boundary.
    # Heuristic: find the dash that has a dot before and after it.
    for i in range(1, len(parts)):
        left = "-".join(parts[:i])
        right = "-".join(parts[i:])
        if "." in left and "." in right:
            return left, right

    return raw, None


def parse_scrollmapper(sources_dir: Path) -> dict[str, CrossReferenceEntry]:
    """Parse cross-references from the scrollmapper TSV file.

    Returns dict keyed by from-verse OSIS ref.
    """
    path = sources_dir / "scrollmapper" / "cross_references.txt"

    grouped: dict[str, list[CrossReferenceTarget]] = defaultdict(list)

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        for row in reader:
            if not row or row[0].startswith("From") or row[0].startswith("#"):
                continue
            if len(row) < 3:
                continue

            from_verse = row[0].strip()
            to_raw = row[1].strip()
            try:
                votes = int(row[2].strip())
            except ValueError:
                votes = 0

            verse_start, verse_end = _parse_to_verse(to_raw)
            grouped[from_verse].append(
                CrossReferenceTarget(
                    verse_start=verse_start,
                    verse_end=verse_end,
                    votes=votes,
                )
            )

    # Sort targets by votes descending within each entry
    return {
        from_verse: CrossReferenceEntry(
            targets=sorted(targets, key=lambda t: t.votes, reverse=True)
        )
        for from_verse, targets in sorted(grouped.items())
    }
