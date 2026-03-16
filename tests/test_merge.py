from gnosis.merge.places import merge_places
from gnosis.merge.verse_index import build_verse_index
from gnosis.parsers.openbible import OpenBiblePlace
from gnosis.types import Event, Person, Place


def test_merge_exact_match():
    places = {
        "jerusalem": Place(
            id="jerusalem", uuid="u1", name="Jerusalem", kjv_name="Jerusalem"
        ),
    }
    ob_places = {
        "Jerusalem": OpenBiblePlace(
            friendly_id="Jerusalem", latitude=31.77, longitude=35.21
        ),
    }
    merged, log = merge_places(places, ob_places)
    assert merged["jerusalem"].latitude == 31.77
    assert merged["jerusalem"].coordinate_source == "openbible"
    assert log["jerusalem"] == "exact"


def test_merge_unmatched():
    places = {
        "unknown-place": Place(id="unknown-place", uuid="u2", name="Xyzzyville"),
    }
    ob_places = {
        "Jerusalem": OpenBiblePlace(friendly_id="Jerusalem", latitude=31.77, longitude=35.21),
    }
    _, log = merge_places(places, ob_places)
    assert log["unknown-place"] == "unmatched"


def test_build_verse_index():
    people = {
        "abraham": Person(
            id="abraham", uuid="u1", name="Abraham", verses=["Gen.12.1", "Gen.15.1"]
        ),
    }
    places = {
        "ur": Place(id="ur", uuid="u2", name="Ur", verses=["Gen.11.31", "Gen.12.1"]),
    }
    events = {
        "call-of-abraham": Event(
            id="call-of-abraham", uuid="u3", title="Call of Abraham", verses=["Gen.12.1"]
        ),
    }
    index = build_verse_index(people, places, events)
    assert "abraham" in index["Gen.12.1"].people
    assert "ur" in index["Gen.12.1"].places
    assert "call-of-abraham" in index["Gen.12.1"].events
    assert "abraham" in index["Gen.15.1"].people
