import json
from pathlib import Path

from gnosis.parsers.topics import _parse_ref_string, parse_topics
from gnosis.types.topic import Topic, TopicAspect


def test_parse_ref_simple():
    assert _parse_ref_string("Genesis 1:1") == ["Gen.1.1"]


def test_parse_ref_range():
    refs = _parse_ref_string("Genesis 4:1-15")
    assert refs == ["Gen.4.1-15"]


def test_parse_ref_compound():
    refs = _parse_ref_string("Genesis 4:1-15,25")
    assert refs == ["Gen.4.1-15", "Gen.4.25"]


def test_parse_ref_invalid():
    assert _parse_ref_string("not a ref") == []
    assert _parse_ref_string("") == []


def test_topic_model():
    t = Topic(
        id="abel", uuid="u-abel", name="ABEL",
        sources=["NAV"],
        aspects=[TopicAspect(label="1.", verses=["Gen.4.1-15"], source="NAV")],
        see_also=["cain"],
    )
    assert len(t.aspects) == 1
    assert t.see_also == ["cain"]


def test_parse_topics(tmp_path: Path):
    d = tmp_path / "topics" / "A"
    d.mkdir(parents=True)

    topic = {
        "topic": "ABEL",
        "slug": "abel",
        "sources": ["NAV"],
        "see_also": ["CAIN"],
        "aspects": [
            {
                "label": "Son of Adam",
                "references": ["Genesis 4:2", "Hebrews 11:4"],
                "source": "NAV",
            },
        ],
        "biblical_references": [],
        "stats": {},
    }
    (d / "abel.json").write_text(json.dumps(topic))

    result = parse_topics(tmp_path)
    assert "abel" in result
    assert result["abel"].name == "ABEL"
    assert result["abel"].sources == ["NAV"]
    assert result["abel"].see_also == ["cain"]
    assert len(result["abel"].aspects) == 1
    assert result["abel"].aspects[0].verses == ["Gen.4.2", "Heb.11.4"]
