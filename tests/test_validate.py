from gnosis.types import Event, Person, Place
from gnosis.types.cross_reference import CrossReferenceEntry, CrossReferenceTarget
from gnosis.types.dictionary import DictionaryDefinition, DictionaryEntry
from gnosis.types.hebrew import HebrewVerse, HebrewWord, LexiconEntry
from gnosis.types.strongs import StrongsEntry
from gnosis.types.topic import Topic
from gnosis.validate.checks import validate


def _base_data() -> dict:
    """Minimal valid data for all entity types."""
    return {
        "people": {
            "moses": Person(
                id="moses", uuid="u", name="Moses",
                verses=["Exod.3.1"], verse_count=1,
            ),
        },
        "places": {
            "sinai": Place(id="sinai", uuid="u", name="Sinai", verses=["Exod.19.1"]),
        },
        "events": {
            "exodus": Event(
                id="exodus", uuid="u", title="Exodus",
                participants=["moses"], locations=["sinai"],
                verses=["Exod.14.21"],
            ),
        },
        "groups": {},
    }


def test_validate_passes_with_valid_data():
    d = _base_data()
    results = validate(d["people"], d["places"], d["events"], d["groups"])
    statuses = {r.name: r.status for r in results}
    assert statuses["Dangling refs"] == "pass"
    assert statuses["OSIS format"] == "pass"


def test_validate_detects_dangling_ref():
    d = _base_data()
    d["events"]["exodus"].participants = ["nonexistent"]
    results = validate(d["people"], d["places"], d["events"], d["groups"])
    statuses = {r.name: r.status for r in results}
    assert statuses["Dangling refs"] == "warn"


def test_validate_detects_bad_osis():
    d = _base_data()
    d["people"]["moses"].verses = ["bad-ref"]
    results = validate(d["people"], d["places"], d["events"], d["groups"])
    statuses = {r.name: r.status for r in results}
    assert statuses["OSIS format"] == "warn"


def test_validate_cross_refs_pass():
    d = _base_data()
    xrefs = {
        "Gen.1.1": CrossReferenceEntry(targets=[
            CrossReferenceTarget(verse_start="Ps.33.9", votes=72),
        ]),
    }
    results = validate(
        d["people"], d["places"], d["events"], d["groups"],
        cross_refs=xrefs,
    )
    statuses = {r.name: r.status for r in results}
    assert statuses["Cross-references"] == "pass"


def test_validate_cross_refs_invalid_osis():
    d = _base_data()
    xrefs = {
        "Gen.1.1": CrossReferenceEntry(targets=[
            CrossReferenceTarget(verse_start="bad-ref", votes=1),
        ]),
    }
    results = validate(
        d["people"], d["places"], d["events"], d["groups"],
        cross_refs=xrefs,
    )
    statuses = {r.name: r.status for r in results}
    assert statuses["Cross-references"] == "warn"


def test_validate_strongs_pass():
    d = _base_data()
    strongs = {
        "H1": StrongsEntry(id="H1", uuid="u", language="hebrew"),
        "G1": StrongsEntry(id="G1", uuid="u", language="greek"),
    }
    results = validate(
        d["people"], d["places"], d["events"], d["groups"],
        strongs=strongs,
    )
    statuses = {r.name: r.status for r in results}
    assert statuses["Strong's concordance"] == "pass"
    assert "H:1" in results[next(
        i for i, r in enumerate(results) if r.name == "Strong's concordance"
    )].message


def test_validate_strongs_invalid_number():
    d = _base_data()
    strongs = {"X99": StrongsEntry(id="X99", uuid="u", language="hebrew")}
    results = validate(
        d["people"], d["places"], d["events"], d["groups"],
        strongs=strongs,
    )
    statuses = {r.name: r.status for r in results}
    assert statuses["Strong's concordance"] == "warn"


def test_validate_dictionary_pass():
    d = _base_data()
    dictionary = {
        "moses": DictionaryEntry(
            id="moses", uuid="u", name="Moses",
            definitions=[DictionaryDefinition(source="SMI", text="leader")],
            scripture_refs=["Exod.3.1"],
        ),
    }
    results = validate(
        d["people"], d["places"], d["events"], d["groups"],
        dictionary=dictionary,
    )
    statuses = {r.name: r.status for r in results}
    assert statuses["Dictionary"] == "pass"


def test_validate_dictionary_bad_ref():
    d = _base_data()
    dictionary = {
        "moses": DictionaryEntry(
            id="moses", uuid="u", name="Moses",
            definitions=[DictionaryDefinition(source="SMI", text="leader")],
            scripture_refs=["not-a-ref"],
        ),
    }
    results = validate(
        d["people"], d["places"], d["events"], d["groups"],
        dictionary=dictionary,
    )
    statuses = {r.name: r.status for r in results}
    assert statuses["Dictionary"] == "warn"


def test_validate_topics_pass():
    d = _base_data()
    topics = {
        "faith": Topic(
            id="faith", uuid="u", name="FAITH",
            sources=["NAV"], see_also=[],
        ),
    }
    results = validate(
        d["people"], d["places"], d["events"], d["groups"],
        topics=topics,
    )
    statuses = {r.name: r.status for r in results}
    assert statuses["Topics"] == "pass"


def test_validate_topics_dangling_see_also():
    d = _base_data()
    topics = {
        "faith": Topic(
            id="faith", uuid="u", name="FAITH",
            sources=["NAV"], see_also=["nonexistent"],
        ),
    }
    results = validate(
        d["people"], d["places"], d["events"], d["groups"],
        topics=topics,
    )
    statuses = {r.name: r.status for r in results}
    assert statuses["Topics"] == "warn"


def test_validate_hebrew_pass():
    d = _base_data()
    hv = {
        "Gen.1.1": HebrewVerse(osis_ref="Gen.1.1", words=[
            HebrewWord(
                word_id="01xeN", text="בְּ/רֵאשִׁ֖ית",
                lemma_raw="b/7225", strongs_number="H7225", morph="HR/Ncfsa",
            ),
        ]),
    }
    lex = {
        "aab": LexiconEntry(
            id="aab", uuid="u", hebrew="אֵב", gloss="freshness",
        ),
    }
    results = validate(
        d["people"], d["places"], d["events"], d["groups"],
        hebrew_verses=hv, lexicon=lex,
    )
    statuses = {r.name: r.status for r in results}
    assert statuses["Hebrew Bible"] == "pass"
    assert "1 verses" in results[next(
        i for i, r in enumerate(results) if r.name == "Hebrew Bible"
    )].message


def test_validate_entity_counts_include_all():
    d = _base_data()
    results = validate(
        d["people"], d["places"], d["events"], d["groups"],
        cross_refs={}, strongs={}, dictionary={}, topics={},
        hebrew_verses={}, lexicon={},
    )
    counts_msg = next(r for r in results if r.name == "Entity counts").message
    assert "people" in counts_msg
    assert "cross-refs" in counts_msg
    assert "strongs" in counts_msg
    assert "dictionary" in counts_msg
    assert "topics" in counts_msg
    assert "hebrew words" in counts_msg
    assert "lexicon" in counts_msg
