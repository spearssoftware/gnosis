"""Tests for build pipeline helper functions."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from gnosis.build import _apply_supplements, _build_chapter_timeline, _recompute_year_ranges
from gnosis.types import Event, Person


def _person(**kwargs) -> Person:
    defaults = {"id": "test", "uuid": "00000000-0000-0000-0000-000000000000", "name": "Test"}
    return Person(**{**defaults, **kwargs})


def _event(**kwargs) -> Event:
    defaults = {"id": "evt", "uuid": "00000000-0000-0000-0000-000000000001", "title": "Event"}
    return Event(**{**defaults, **kwargs})


def test_recompute_year_ranges():
    person = _person(verses=["Gen.22.1", "Gen.22.2"], earliest_year_mentioned=None)
    event = _event(verses=["Gen.22.1", "Gen.22.2"], start_year=-2054)

    _recompute_year_ranges({"test": person}, {"evt": event})

    assert person.earliest_year_mentioned == -2054
    assert person.latest_year_mentioned == -2054
    assert person.earliest_year_mentioned_display == "2055 BC"
    assert person.latest_year_mentioned_display == "2055 BC"


def test_recompute_extends_range():
    person = _person(
        verses=["Matt.10.3", "Luke.6.15"],
        earliest_year_mentioned=31,
        latest_year_mentioned=33,
    )
    event = _event(verses=["Luke.6.15"], start_year=28)

    _recompute_year_ranges({"test": person}, {"evt": event})

    assert person.earliest_year_mentioned == 28
    assert person.earliest_year_mentioned_display == "28 AD"
    assert person.latest_year_mentioned == 33


def test_recompute_preserves_wider_existing():
    person = _person(
        verses=["Gen.1.1"],
        earliest_year_mentioned=-4004,
        latest_year_mentioned=96,
    )
    event = _event(verses=["Gen.1.1"], start_year=-4004)

    _recompute_year_ranges({"test": person}, {"evt": event})

    assert person.earliest_year_mentioned == -4004
    assert person.latest_year_mentioned == 96


def test_supplements_applied():
    person = _person(id="paul", birth_year=None, death_year=None)
    supplements = {"paul": {"birth_year": 5, "death_year": 64}}

    with tempfile.TemporaryDirectory() as tmpdir:
        supp_dir = Path(tmpdir) / "supplements"
        supp_dir.mkdir()
        (supp_dir / "people-dates.json").write_text(json.dumps(supplements))

        with patch("gnosis.build.SOURCES_DIR", Path(tmpdir)):
            _apply_supplements({"paul": person})

    assert person.birth_year == 5
    assert person.death_year == 64
    assert person.birth_year_display == "5 AD"
    assert person.death_year_display == "64 AD"


def test_supplements_no_override():
    person = _person(id="paul", birth_year=10, death_year=70)
    supplements = {"paul": {"birth_year": 5, "death_year": 64}}

    with tempfile.TemporaryDirectory() as tmpdir:
        supp_dir = Path(tmpdir) / "supplements"
        supp_dir.mkdir()
        (supp_dir / "people-dates.json").write_text(json.dumps(supplements))

        with patch("gnosis.build.SOURCES_DIR", Path(tmpdir)):
            _apply_supplements({"paul": person})

    assert person.birth_year == 10
    assert person.death_year == 70


def test_build_chapter_timeline():
    verse_years = {
        "Jer.37.1": -596, "Jer.37.2": -596, "Jer.37.3": -596,
        "Jer.38.1": -590, "Jer.38.2": -590,
        "Gen.1.1": -4004, "Gen.1.2": -4004,
    }
    result = _build_chapter_timeline(verse_years)

    assert result["Jer.37"] == {"year": -596, "year_display": "597 BC"}
    assert result["Jer.38"] == {"year": -590, "year_display": "591 BC"}
    assert result["Gen.1"] == {"year": -4004, "year_display": "4005 BC"}
    assert len(result) == 3


def test_build_chapter_timeline_uses_mode():
    verse_years = {
        "Jer.52.1": -600, "Jer.52.2": -588, "Jer.52.3": -588,
        "Jer.52.4": -588, "Jer.52.5": -562,
    }
    result = _build_chapter_timeline(verse_years)

    assert result["Jer.52"]["year"] == -588
