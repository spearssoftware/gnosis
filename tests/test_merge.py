from gnosis.merge.places import merge_places
from gnosis.merge.verse_index import build_verse_index
from gnosis.parsers.openbible import OpenBiblePlace
from gnosis.types import Event, Person, Place
from gnosis.types.topic import Topic, TopicAspect


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


def test_build_verse_index_with_topics():
    people: dict = {}
    places: dict = {}
    events: dict = {}
    topics = {
        "faith": Topic(
            id="faith", uuid="u-faith", name="FAITH",
            sources=["NAV"],
            aspects=[TopicAspect(
                label="General", verses=["Heb.11.1", "Rom.1.17"],
                source="NAV",
            )],
        ),
    }
    index = build_verse_index(people, places, events, topics)
    assert "faith" in index["Heb.11.1"].topics
    assert "faith" in index["Rom.1.17"].topics


def test_build_verse_index_topics_strips_ranges():
    """Verse ranges like 'Gen.4.1-15' should index under 'Gen.4.1'."""
    people: dict = {}
    places: dict = {}
    events: dict = {}
    topics = {
        "cain": Topic(
            id="cain", uuid="u-cain", name="CAIN",
            sources=["NAV"],
            aspects=[TopicAspect(
                label="Story", verses=["Gen.4.1-15"], source="NAV",
            )],
        ),
    }
    index = build_verse_index(people, places, events, topics)
    assert "cain" in index["Gen.4.1"].topics
