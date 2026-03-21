import sqlite3
from pathlib import Path

import pytest

from gnosis.sqlite_writer import write_sqlite
from gnosis.types import Event, PeopleGroup, Person, Place


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    """Build a small SQLite DB from fixture data and return its path."""
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
    cross_refs: dict = {}
    strongs: dict = {}
    dictionary: dict = {}
    topics: dict = {}
    return write_sqlite(
        people, places, events, groups, cross_refs, strongs, dictionary,
        topics, tmp_path,
    )


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
