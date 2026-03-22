import textwrap
from pathlib import Path

from gnosis.parsers.scrollmapper import _parse_to_verse, parse_scrollmapper
from gnosis.types.cross_reference import CrossReferenceEntry, CrossReferenceTarget


def test_parse_to_verse_single():
    assert _parse_to_verse("Gen.1.1") == ("Gen.1.1", None)


def test_parse_to_verse_range():
    assert _parse_to_verse("Prov.8.22-Prov.8.30") == ("Prov.8.22", "Prov.8.30")


def test_parse_to_verse_no_dots():
    """A plain string without dots should return as-is with no range."""
    assert _parse_to_verse("something") == ("something", None)


def test_cross_reference_target_model():
    t = CrossReferenceTarget(verse_start="Gen.1.1", votes=42)
    assert t.verse_end is None
    assert t.votes == 42


def test_cross_reference_entry_model():
    entry = CrossReferenceEntry(
        targets=[
            CrossReferenceTarget(verse_start="Ps.33.9", votes=72),
            CrossReferenceTarget(verse_start="Prov.8.22", verse_end="Prov.8.30", votes=59),
        ]
    )
    assert len(entry.targets) == 2


def test_parse_scrollmapper(tmp_path: Path):
    src = tmp_path / "scrollmapper"
    src.mkdir()
    tsv = src / "cross_references.txt"
    tsv.write_text(textwrap.dedent("""\
        From Verse\tTo Verse\tVotes\t#header
        Gen.1.1\tPs.33.9\t72
        Gen.1.1\tProv.8.22-Prov.8.30\t59
        Gen.1.1\tActs.14.15\t62
        Gen.1.2\tIsa.45.18\t40
    """))

    result = parse_scrollmapper(tmp_path)

    assert "Gen.1.1" in result
    assert "Gen.1.2" in result
    assert len(result["Gen.1.1"].targets) == 3
    # Should be sorted by votes descending
    assert result["Gen.1.1"].targets[0].votes == 72
    assert result["Gen.1.1"].targets[1].votes == 62
    # Range should be parsed
    range_target = next(t for t in result["Gen.1.1"].targets if t.verse_end is not None)
    assert range_target.verse_start == "Prov.8.22"
    assert range_target.verse_end == "Prov.8.30"


def test_parse_scrollmapper_negative_votes(tmp_path: Path):
    """Negative votes should be preserved."""
    src = tmp_path / "scrollmapper"
    src.mkdir()
    tsv = src / "cross_references.txt"
    tsv.write_text(textwrap.dedent("""\
        From Verse\tTo Verse\tVotes\t#header
        Gen.1.1\tExod.31.18\t-31
    """))

    result = parse_scrollmapper(tmp_path)
    assert result["Gen.1.1"].targets[0].votes == -31


def test_parse_scrollmapper_skips_blank_lines(tmp_path: Path):
    src = tmp_path / "scrollmapper"
    src.mkdir()
    tsv = src / "cross_references.txt"
    tsv.write_text("From Verse\tTo Verse\tVotes\n\nGen.1.1\tPs.33.9\t10\n\n")

    result = parse_scrollmapper(tmp_path)
    assert len(result) == 1
