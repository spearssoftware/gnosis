import sqlite3
from pathlib import Path

import pytest

from gnosis.build import BuildContext
from gnosis.sqlite_writer import write_sqlite
from gnosis.types import Event, PeopleGroup, Person, Place
from gnosis.types.cross_reference import CrossReferenceEntry, CrossReferenceTarget
from gnosis.types.dictionary import DictionaryDefinition, DictionaryEntry
from gnosis.types.hebrew import HebrewVerse, HebrewWord, LexiconEntry
from gnosis.types.strongs import StrongsEntry
from gnosis.types.topic import Topic, TopicAspect


def _build_fixture_data() -> dict:
    """Shared fixture data for all SQLite tests."""
    people = {
        "abraham": Person(
            id="abraham", uuid="u-abraham", name="Abraham",
            gender="Male", birth_year=-2165, birth_year_display="2166 BC",
            children=["isaac"], verses=["Gen.12.1", "Gen.15.1", "Gen.22.2"],
            verse_count=3, first_mention="Gen.12.1",
        ),
        "isaac": Person(
            id="isaac", uuid="u-isaac", name="Isaac",
            gender="Male", father="abraham", birth_place="beersheba",
            verses=["Gen.21.3", "Gen.22.2"], verse_count=2,
            first_mention="Gen.21.3", people_groups=["patriarchs"],
        ),
    }
    places = {
        "beersheba": Place(
            id="beersheba", uuid="u-beersheba", name="Beersheba",
            kjv_name="Beer-sheba", latitude=31.25, longitude=34.79,
            coordinate_source="theographic",
            verses=["Gen.21.14", "Gen.21.31"],
            theographic_id="rec-bs",
        ),
    }
    events = {
        "binding-of-isaac": Event(
            id="binding-of-isaac", uuid="u-binding", title="Binding of Isaac",
            start_year=-2065, start_year_display="2066 BC",
            sort_key=1.0, participants=["abraham", "isaac"],
            verses=["Gen.22.2"],
            theographic_id="rec-boi",
        ),
    }
    groups = {
        "patriarchs": PeopleGroup(
            id="patriarchs", uuid="u-patriarchs", name="Patriarchs",
            members=["abraham", "isaac"],
            theographic_id="rec-pat",
        ),
    }
    cross_refs = {
        "Gen.12.1": CrossReferenceEntry(targets=[
            CrossReferenceTarget(verse_start="Acts.7.3", votes=80),
            CrossReferenceTarget(
                verse_start="Heb.11.8", verse_end="Heb.11.10", votes=60,
            ),
        ]),
    }
    strongs = {
        "H1": StrongsEntry(
            id="H1", uuid="u-h1", language="hebrew",
            lemma="אָב", transliteration="ʼâb", pronunciation="awb",
            definition="father", kjv_usage="chief, father",
        ),
        "G3056": StrongsEntry(
            id="G3056", uuid="u-g3056", language="greek",
            lemma="λόγος", transliteration="lógos",
            definition="word", kjv_usage="word",
        ),
    }
    dictionary = {
        "abraham": DictionaryEntry(
            id="abraham", uuid="u-dict-abraham", name="Abraham",
            definitions=[
                DictionaryDefinition(source="SMI", text="Father of nations"),
            ],
            scripture_refs=["Gen.12.1"],
        ),
    }
    topics = {
        "faith": Topic(
            id="faith", uuid="u-faith", name="FAITH",
            sources=["NAV"],
            aspects=[TopicAspect(
                label="General", verses=["Heb.11.1", "Heb.11.8"],
                source="NAV",
            )],
            see_also=[],
        ),
    }
    hebrew_verses = {
        "Gen.1.1": HebrewVerse(osis_ref="Gen.1.1", words=[
            HebrewWord(
                word_id="01xeN", text="בְּ/רֵאשִׁ֖ית",
                lemma_raw="b/7225", strongs_number="H7225", morph="HR/Ncfsa",
            ),
            HebrewWord(
                word_id="01Nvk", text="בָּרָ֣א",
                lemma_raw="1254 a", strongs_number="H1254", morph="HVqp3ms",
            ),
        ]),
    }
    lexicon = {
        "aac": LexiconEntry(
            id="aac", uuid="u-aac", hebrew="אָב",
            transliteration="ʾāb", part_of_speech="N",
            gloss="father", strongs_number="H1", twot_number="4a",
        ),
    }
    return {
        "people": people, "places": places, "events": events,
        "groups": groups, "cross_refs": cross_refs, "strongs": strongs,
        "dictionary": dictionary, "topics": topics,
        "hebrew_verses": hebrew_verses, "lexicon": lexicon,
    }


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    """Build a small SQLite DB from fixture data and return its path."""
    d = _build_fixture_data()
    ctx = BuildContext(
        people=d["people"], places=d["places"], events=d["events"],
        groups=d["groups"], match_log={},
        cross_refs=d["cross_refs"], strongs=d["strongs"],
        dictionary=d["dictionary"], topics=d["topics"],
        hebrew_verses=d["hebrew_verses"], lexicon=d["lexicon"],
    )
    return write_sqlite(ctx, tmp_path)


def _query(db_path: Path, sql: str) -> list:
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    rows = con.execute(sql).fetchall()
    con.close()
    return rows


def test_tables_exist(db_path: Path) -> None:
    rows = _query(db_path, "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    names = {r["name"] for r in rows}
    expected = {
        "verse", "person", "place", "event", "people_group",
        "person_verse", "place_verse", "event_verse",
        "person_sibling", "person_child", "person_partner",
        "person_group", "event_participant", "gnosis_meta",
        "cross_reference", "strongs", "dictionary_entry",
        "dictionary_definition", "dictionary_verse",
        "topic", "topic_aspect", "topic_aspect_verse", "topic_see_also",
        "hebrew_word", "lexicon_entry",
    }
    assert expected.issubset(names)


def test_person_columns(db_path: Path) -> None:
    rows = _query(db_path, "PRAGMA table_info(person)")
    col_names = {r["name"] for r in rows}
    assert "slug" in col_names
    assert "father_id" in col_names
    assert "birth_place_id" in col_names


def test_person_count(db_path: Path) -> None:
    rows = _query(db_path, "SELECT count(*) as cnt FROM person")
    assert rows[0]["cnt"] == 2


def test_father_fk_resolves(db_path: Path) -> None:
    rows = _query(
        db_path,
        "SELECT p.name, parent.name AS father_name "
        "FROM person p LEFT JOIN person parent ON p.father_id = parent.id "
        "WHERE p.slug = 'isaac'",
    )
    assert len(rows) == 1
    assert rows[0]["father_name"] == "Abraham"


def test_birth_place_fk_resolves(db_path: Path) -> None:
    rows = _query(
        db_path,
        "SELECT p.name, pl.name AS place_name "
        "FROM person p JOIN place pl ON p.birth_place_id = pl.id "
        "WHERE p.slug = 'isaac'",
    )
    assert len(rows) == 1
    assert rows[0]["place_name"] == "Beersheba"


def test_person_verse_junction(db_path: Path) -> None:
    rows = _query(
        db_path,
        "SELECT v.osis_ref FROM person_verse pv "
        "JOIN verse v ON v.id = pv.verse_id "
        "JOIN person p ON p.id = pv.person_id "
        "WHERE p.slug = 'abraham' ORDER BY v.osis_ref",
    )
    refs = [r["osis_ref"] for r in rows]
    assert refs == ["Gen.12.1", "Gen.15.1", "Gen.22.2"]


def test_event_participant_junction(db_path: Path) -> None:
    rows = _query(
        db_path,
        "SELECT p.slug FROM event_participant ep "
        "JOIN person p ON p.id = ep.person_id "
        "JOIN event e ON e.id = ep.event_id "
        "WHERE e.slug = 'binding-of-isaac' ORDER BY p.slug",
    )
    slugs = [r["slug"] for r in rows]
    assert slugs == ["abraham", "isaac"]


def test_person_group_junction(db_path: Path) -> None:
    rows = _query(
        db_path,
        "SELECT pg.name FROM person_group pgj "
        "JOIN people_group pg ON pg.id = pgj.group_id "
        "JOIN person p ON p.id = pgj.person_id "
        "WHERE p.slug = 'isaac'",
    )
    assert rows[0]["name"] == "Patriarchs"


def test_person_child_junction(db_path: Path) -> None:
    rows = _query(
        db_path,
        "SELECT child.slug FROM person_child pc "
        "JOIN person child ON child.id = pc.child_id "
        "JOIN person parent ON parent.id = pc.parent_id "
        "WHERE parent.slug = 'abraham'",
    )
    assert rows[0]["slug"] == "isaac"


def test_meta(db_path: Path) -> None:
    rows = _query(db_path, "SELECT key, value FROM gnosis_meta ORDER BY key")
    meta = {r["key"]: r["value"] for r in rows}
    assert meta["version"] == "0.1.0"
    assert "build_date" in meta


def test_verse_query_from_osis_ref(db_path: Path) -> None:
    """Verify we can look up people by OSIS ref through the junction table."""
    rows = _query(
        db_path,
        "SELECT p.name FROM person p "
        "JOIN person_verse pv ON pv.person_id = p.id "
        "JOIN verse v ON v.id = pv.verse_id "
        "WHERE v.osis_ref = 'Gen.22.2' ORDER BY p.name",
    )
    names = [r["name"] for r in rows]
    assert names == ["Abraham", "Isaac"]


# --- Cross-references ---


def test_cross_reference_count(db_path: Path) -> None:
    rows = _query(db_path, "SELECT count(*) as cnt FROM cross_reference")
    assert rows[0]["cnt"] == 2


def test_cross_reference_votes(db_path: Path) -> None:
    rows = _query(
        db_path,
        "SELECT cr.votes, v.osis_ref FROM cross_reference cr "
        "JOIN verse v ON v.id = cr.to_verse_start_id "
        "ORDER BY cr.votes DESC",
    )
    assert rows[0]["votes"] == 80
    assert rows[0]["osis_ref"] == "Acts.7.3"


def test_cross_reference_range(db_path: Path) -> None:
    rows = _query(
        db_path,
        "SELECT v_end.osis_ref FROM cross_reference cr "
        "JOIN verse v_end ON v_end.id = cr.to_verse_end_id",
    )
    assert len(rows) == 1
    assert rows[0]["osis_ref"] == "Heb.11.10"


# --- Strong's ---


def test_strongs_count(db_path: Path) -> None:
    rows = _query(db_path, "SELECT count(*) as cnt FROM strongs")
    assert rows[0]["cnt"] == 2


def test_strongs_hebrew(db_path: Path) -> None:
    rows = _query(
        db_path,
        "SELECT number, lemma, definition FROM strongs WHERE language = 'hebrew'",
    )
    assert len(rows) == 1
    assert rows[0]["number"] == "H1"
    assert rows[0]["lemma"] == "אָב"


def test_strongs_greek(db_path: Path) -> None:
    rows = _query(
        db_path,
        "SELECT number, lemma FROM strongs WHERE language = 'greek'",
    )
    assert len(rows) == 1
    assert rows[0]["number"] == "G3056"


# --- Dictionary ---


def test_dictionary_entry(db_path: Path) -> None:
    rows = _query(
        db_path,
        "SELECT slug, name FROM dictionary_entry WHERE slug = 'abraham'",
    )
    assert len(rows) == 1
    assert rows[0]["name"] == "Abraham"


def test_dictionary_definition(db_path: Path) -> None:
    rows = _query(
        db_path,
        "SELECT dd.source, dd.text FROM dictionary_definition dd "
        "JOIN dictionary_entry de ON de.id = dd.entry_id "
        "WHERE de.slug = 'abraham'",
    )
    assert len(rows) == 1
    assert rows[0]["source"] == "SMI"
    assert "nations" in rows[0]["text"]


def test_dictionary_verse_junction(db_path: Path) -> None:
    rows = _query(
        db_path,
        "SELECT v.osis_ref FROM dictionary_verse dv "
        "JOIN verse v ON v.id = dv.verse_id "
        "JOIN dictionary_entry de ON de.id = dv.entry_id "
        "WHERE de.slug = 'abraham'",
    )
    assert len(rows) == 1
    assert rows[0]["osis_ref"] == "Gen.12.1"


# --- Topics ---


def test_topic_entry(db_path: Path) -> None:
    rows = _query(db_path, "SELECT slug, name FROM topic WHERE slug = 'faith'")
    assert len(rows) == 1
    assert rows[0]["name"] == "FAITH"


def test_topic_aspect(db_path: Path) -> None:
    rows = _query(
        db_path,
        "SELECT ta.label, ta.source FROM topic_aspect ta "
        "JOIN topic t ON t.id = ta.topic_id "
        "WHERE t.slug = 'faith'",
    )
    assert len(rows) == 1
    assert rows[0]["label"] == "General"
    assert rows[0]["source"] == "NAV"


def test_topic_aspect_verse(db_path: Path) -> None:
    rows = _query(
        db_path,
        "SELECT v.osis_ref FROM topic_aspect_verse tav "
        "JOIN topic_aspect ta ON ta.id = tav.aspect_id "
        "JOIN topic t ON t.id = ta.topic_id "
        "JOIN verse v ON v.id = tav.verse_id "
        "WHERE t.slug = 'faith' ORDER BY v.osis_ref",
    )
    refs = [r["osis_ref"] for r in rows]
    assert refs == ["Heb.11.1", "Heb.11.8"]


# --- Hebrew words ---


def test_hebrew_word_count(db_path: Path) -> None:
    rows = _query(db_path, "SELECT count(*) as cnt FROM hebrew_word")
    assert rows[0]["cnt"] == 2


def test_hebrew_word_content(db_path: Path) -> None:
    rows = _query(
        db_path,
        "SELECT word_id, text, strongs_number, morph FROM hebrew_word "
        "ORDER BY position",
    )
    assert rows[0]["word_id"] == "01xeN"
    assert rows[0]["strongs_number"] == "H7225"
    assert rows[1]["word_id"] == "01Nvk"
    assert rows[1]["strongs_number"] == "H1254"


def test_hebrew_word_verse_fk(db_path: Path) -> None:
    rows = _query(
        db_path,
        "SELECT v.osis_ref FROM hebrew_word hw "
        "JOIN verse v ON v.id = hw.verse_id "
        "WHERE hw.word_id = '01xeN'",
    )
    assert rows[0]["osis_ref"] == "Gen.1.1"


# --- Lexicon ---


def test_lexicon_entry(db_path: Path) -> None:
    rows = _query(
        db_path,
        "SELECT lexical_id, hebrew, gloss, strongs_number "
        "FROM lexicon_entry WHERE lexical_id = 'aac'",
    )
    assert len(rows) == 1
    assert rows[0]["hebrew"] == "אָב"
    assert rows[0]["gloss"] == "father"
    assert rows[0]["strongs_number"] == "H1"
