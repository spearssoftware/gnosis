from gnosis.build import BuildContext
from gnosis.types import Event, Person, Place
from gnosis.types.cross_reference import CrossReferenceEntry, CrossReferenceTarget
from gnosis.types.dictionary import DictionaryDefinition, DictionaryEntry
from gnosis.types.hebrew import HebrewVerse, HebrewWord, LexiconEntry
from gnosis.types.strongs import StrongsEntry
from gnosis.types.topic import Topic
from gnosis.validate.checks import validate


def _ctx(**overrides) -> BuildContext:
    """Build a minimal valid BuildContext, with optional field overrides."""
    defaults = {
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
        "match_log": {},
        "cross_refs": {},
        "strongs": {},
        "dictionary": {},
        "topics": {},
        "hebrew_verses": {},
        "lexicon": {},
        "greek_verses": {},
        "greek_lexicon": {},
        "kjv_verses": {},
    }
    defaults.update(overrides)
    return BuildContext(**defaults)


def test_validate_passes_with_valid_data():
    results = validate(_ctx())
    statuses = {r.name: r.status for r in results}
    assert statuses["Dangling refs"] == "pass"
    assert statuses["OSIS format"] == "pass"


def test_validate_detects_dangling_ref():
    ctx = _ctx()
    ctx.events["exodus"].participants = ["nonexistent"]
    results = validate(ctx)
    statuses = {r.name: r.status for r in results}
    assert statuses["Dangling refs"] == "warn"


def test_validate_detects_bad_osis():
    ctx = _ctx()
    ctx.people["moses"].verses = ["bad-ref"]
    results = validate(ctx)
    statuses = {r.name: r.status for r in results}
    assert statuses["OSIS format"] == "warn"


def test_validate_cross_refs_pass():
    results = validate(_ctx(cross_refs={
        "Gen.1.1": CrossReferenceEntry(targets=[
            CrossReferenceTarget(verse_start="Ps.33.9", votes=72),
        ]),
    }))
    statuses = {r.name: r.status for r in results}
    assert statuses["Cross-references"] == "pass"


def test_validate_cross_refs_invalid_osis():
    results = validate(_ctx(cross_refs={
        "Gen.1.1": CrossReferenceEntry(targets=[
            CrossReferenceTarget(verse_start="bad-ref", votes=1),
        ]),
    }))
    statuses = {r.name: r.status for r in results}
    assert statuses["Cross-references"] == "warn"


def test_validate_strongs_pass():
    results = validate(_ctx(strongs={
        "H1": StrongsEntry(id="H1", uuid="u", language="hebrew"),
        "G1": StrongsEntry(id="G1", uuid="u", language="greek"),
    }))
    statuses = {r.name: r.status for r in results}
    assert statuses["Strong's concordance"] == "pass"
    msg = next(r for r in results if r.name == "Strong's concordance").message
    assert "H:1" in msg


def test_validate_strongs_invalid_number():
    results = validate(_ctx(strongs={
        "X99": StrongsEntry(id="X99", uuid="u", language="hebrew"),
    }))
    statuses = {r.name: r.status for r in results}
    assert statuses["Strong's concordance"] == "warn"


def test_validate_dictionary_pass():
    results = validate(_ctx(dictionary={
        "moses": DictionaryEntry(
            id="moses", uuid="u", name="Moses",
            definitions=[DictionaryDefinition(source="SMI", text="leader")],
            scripture_refs=["Exod.3.1"],
        ),
    }))
    statuses = {r.name: r.status for r in results}
    assert statuses["Dictionary"] == "pass"


def test_validate_dictionary_bad_ref():
    results = validate(_ctx(dictionary={
        "moses": DictionaryEntry(
            id="moses", uuid="u", name="Moses",
            definitions=[DictionaryDefinition(source="SMI", text="leader")],
            scripture_refs=["not-a-ref"],
        ),
    }))
    statuses = {r.name: r.status for r in results}
    assert statuses["Dictionary"] == "warn"


def test_validate_topics_pass():
    results = validate(_ctx(topics={
        "faith": Topic(id="faith", uuid="u", name="FAITH", sources=["NAV"], see_also=[]),
    }))
    statuses = {r.name: r.status for r in results}
    assert statuses["Topics"] == "pass"


def test_validate_topics_dangling_see_also():
    results = validate(_ctx(topics={
        "faith": Topic(
            id="faith", uuid="u", name="FAITH",
            sources=["NAV"], see_also=["nonexistent"],
        ),
    }))
    statuses = {r.name: r.status for r in results}
    assert statuses["Topics"] == "warn"


def test_validate_hebrew_pass():
    results = validate(_ctx(
        hebrew_verses={
            "Gen.1.1": HebrewVerse(osis_ref="Gen.1.1", words=[
                HebrewWord(
                    word_id="01xeN", text="בְּ/רֵאשִׁ֖ית",
                    lemma_raw="b/7225", strongs_number="H7225", morph="HR/Ncfsa",
                ),
            ]),
        },
        lexicon={
            "aab": LexiconEntry(id="aab", uuid="u", hebrew="אֵב", gloss="freshness"),
        },
    ))
    statuses = {r.name: r.status for r in results}
    assert statuses["Hebrew Bible"] == "pass"
    msg = next(r for r in results if r.name == "Hebrew Bible").message
    assert "1 verses" in msg


def test_validate_entity_counts_include_all():
    results = validate(_ctx())
    counts_msg = next(r for r in results if r.name == "Entity counts").message
    assert "people" in counts_msg
    assert "cross-refs" in counts_msg
    assert "strongs" in counts_msg
    assert "dictionary" in counts_msg
    assert "topics" in counts_msg
    assert "hebrew words" in counts_msg
    assert "lexicon" in counts_msg


# --- Verse existence ---


def test_verse_existence_pass():
    results = validate(_ctx())
    statuses = {r.name: r.status for r in results}
    assert statuses["Verse existence"] == "pass"


def test_verse_existence_invalid_verse():
    ctx = _ctx()
    ctx.people["moses"].verses = ["Gen.50.27"]  # Gen 50 has 26 verses
    results = validate(ctx)
    statuses = {r.name: r.status for r in results}
    assert statuses["Verse existence"] == "warn"


def test_verse_existence_invalid_chapter():
    ctx = _ctx()
    ctx.places["sinai"].verses = ["Gen.51.1"]  # Gen has 50 chapters
    results = validate(ctx)
    statuses = {r.name: r.status for r in results}
    assert statuses["Verse existence"] == "warn"


# --- Relationship symmetry ---


def test_relationship_symmetry_pass():
    results = validate(_ctx(people={
        "parent": Person(
            id="parent", uuid="u", name="Parent",
            verses=["Gen.1.1"], children=["child"],
        ),
        "child": Person(
            id="child", uuid="u", name="Child",
            verses=["Gen.1.2"], father="parent",
        ),
    }))
    statuses = {r.name: r.status for r in results}
    assert statuses["Relationship symmetry"] == "pass"


def test_relationship_symmetry_father_missing_child():
    results = validate(_ctx(people={
        "parent": Person(
            id="parent", uuid="u", name="Parent",
            verses=["Gen.1.1"], children=[],
        ),
        "child": Person(
            id="child", uuid="u", name="Child",
            verses=["Gen.1.2"], father="parent",
        ),
    }))
    statuses = {r.name: r.status for r in results}
    assert statuses["Relationship symmetry"] == "warn"


def test_relationship_symmetry_siblings():
    results = validate(_ctx(people={
        "alice": Person(
            id="alice", uuid="u", name="Alice",
            verses=["Gen.1.1"], siblings=["bob"],
        ),
        "bob": Person(
            id="bob", uuid="u", name="Bob",
            verses=["Gen.1.2"], siblings=[],
        ),
    }))
    statuses = {r.name: r.status for r in results}
    assert statuses["Relationship symmetry"] == "warn"


def test_relationship_symmetry_partners():
    results = validate(_ctx(people={
        "adam": Person(
            id="adam", uuid="u", name="Adam",
            verses=["Gen.1.1"], partners=["eve"],
        ),
        "eve": Person(
            id="eve", uuid="u", name="Eve",
            verses=["Gen.1.2"], partners=[],
        ),
    }))
    statuses = {r.name: r.status for r in results}
    assert statuses["Relationship symmetry"] == "warn"


# --- Chronology ---


def test_chronology_pass():
    results = validate(_ctx(people={
        "moses": Person(
            id="moses", uuid="u", name="Moses",
            verses=["Exod.3.1"], birth_year=-1526, death_year=-1406,
        ),
    }))
    statuses = {r.name: r.status for r in results}
    assert statuses["Chronology"] == "pass"


def test_chronology_birth_after_death():
    results = validate(_ctx(people={
        "moses": Person(
            id="moses", uuid="u", name="Moses",
            verses=["Exod.3.1"], birth_year=-1406, death_year=-1526,
        ),
    }))
    statuses = {r.name: r.status for r in results}
    assert statuses["Chronology"] == "warn"


def test_chronology_parent_after_child():
    results = validate(_ctx(people={
        "parent": Person(
            id="parent", uuid="u", name="Parent",
            verses=["Gen.1.1"], birth_year=-1400, children=["child"],
        ),
        "child": Person(
            id="child", uuid="u", name="Child",
            verses=["Gen.1.2"], birth_year=-1500, father="parent",
        ),
    }))
    statuses = {r.name: r.status for r in results}
    assert statuses["Chronology"] == "warn"


def test_chronology_event_out_of_range():
    results = validate(_ctx(events={
        "future": Event(
            id="future", uuid="u", title="Future Event",
            verses=["Rev.1.1"], start_year=5000,
        ),
    }))
    statuses = {r.name: r.status for r in results}
    assert statuses["Chronology"] == "warn"
