"""Tests for build pipeline helper functions."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from gnosis.build import _apply_supplements, _recompute_year_ranges
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
