"""Write gnosis data to a SQLite database for BibleMarker bundling."""

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from gnosis.types import Event, PeopleGroup, Person, Place
from gnosis.types.cross_reference import CrossReferenceEntry
from gnosis.types.dictionary import DictionaryEntry
from gnosis.types.strongs import StrongsEntry
from gnosis.types.topic import Topic

_SCHEMA = """
CREATE TABLE verse (
    id INTEGER PRIMARY KEY,
    osis_ref TEXT NOT NULL UNIQUE
);

CREATE TABLE place (
    id INTEGER PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    uuid TEXT NOT NULL,
    name TEXT NOT NULL,
    kjv_name TEXT,
    esv_name TEXT,
    latitude REAL,
    longitude REAL,
    coordinate_source TEXT,
    feature_type TEXT,
    feature_sub_type TEXT,
    modern_name TEXT,
    theographic_id TEXT,
    openbible_id TEXT,
    status TEXT
);

CREATE TABLE person (
    id INTEGER PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    uuid TEXT NOT NULL,
    name TEXT NOT NULL,
    gender TEXT,
    birth_year INTEGER,
    death_year INTEGER,
    birth_year_display TEXT,
    death_year_display TEXT,
    birth_place_id INTEGER REFERENCES place(id),
    death_place_id INTEGER REFERENCES place(id),
    father_id INTEGER REFERENCES person(id),
    mother_id INTEGER REFERENCES person(id),
    verse_count INTEGER NOT NULL DEFAULT 0,
    first_mention TEXT,
    name_meaning TEXT,
    status TEXT
);

CREATE TABLE event (
    id INTEGER PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    uuid TEXT NOT NULL,
    title TEXT NOT NULL,
    start_year INTEGER,
    start_year_display TEXT,
    duration TEXT,
    sort_key REAL,
    parent_event_id INTEGER REFERENCES event(id),
    predecessor_id INTEGER REFERENCES event(id),
    theographic_id TEXT,
    status TEXT
);

CREATE TABLE people_group (
    id INTEGER PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    uuid TEXT NOT NULL,
    name TEXT NOT NULL,
    theographic_id TEXT
);

CREATE TABLE person_verse (
    person_id INTEGER NOT NULL REFERENCES person(id),
    verse_id INTEGER NOT NULL REFERENCES verse(id),
    PRIMARY KEY (person_id, verse_id)
);

CREATE TABLE place_verse (
    place_id INTEGER NOT NULL REFERENCES place(id),
    verse_id INTEGER NOT NULL REFERENCES verse(id),
    PRIMARY KEY (place_id, verse_id)
);

CREATE TABLE event_verse (
    event_id INTEGER NOT NULL REFERENCES event(id),
    verse_id INTEGER NOT NULL REFERENCES verse(id),
    PRIMARY KEY (event_id, verse_id)
);

CREATE TABLE person_sibling (
    person_id INTEGER NOT NULL REFERENCES person(id),
    sibling_id INTEGER NOT NULL REFERENCES person(id),
    PRIMARY KEY (person_id, sibling_id)
);

CREATE TABLE person_child (
    parent_id INTEGER NOT NULL REFERENCES person(id),
    child_id INTEGER NOT NULL REFERENCES person(id),
    PRIMARY KEY (parent_id, child_id)
);

CREATE TABLE person_partner (
    person_id INTEGER NOT NULL REFERENCES person(id),
    partner_id INTEGER NOT NULL REFERENCES person(id),
    PRIMARY KEY (person_id, partner_id)
);

CREATE TABLE person_group (
    person_id INTEGER NOT NULL REFERENCES person(id),
    group_id INTEGER NOT NULL REFERENCES people_group(id),
    PRIMARY KEY (person_id, group_id)
);

CREATE TABLE event_participant (
    event_id INTEGER NOT NULL REFERENCES event(id),
    person_id INTEGER NOT NULL REFERENCES person(id),
    PRIMARY KEY (event_id, person_id)
);

CREATE TABLE strongs (
    id INTEGER PRIMARY KEY,
    number TEXT NOT NULL UNIQUE,
    uuid TEXT NOT NULL,
    language TEXT NOT NULL,
    lemma TEXT,
    transliteration TEXT,
    pronunciation TEXT,
    definition TEXT,
    kjv_usage TEXT
);

CREATE TABLE dictionary_entry (
    id INTEGER PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    uuid TEXT NOT NULL,
    name TEXT NOT NULL
);

CREATE TABLE dictionary_definition (
    id INTEGER PRIMARY KEY,
    entry_id INTEGER NOT NULL REFERENCES dictionary_entry(id),
    source TEXT NOT NULL,
    text TEXT NOT NULL
);

CREATE TABLE dictionary_verse (
    entry_id INTEGER NOT NULL REFERENCES dictionary_entry(id),
    verse_id INTEGER NOT NULL REFERENCES verse(id),
    PRIMARY KEY (entry_id, verse_id)
);

CREATE TABLE topic (
    id INTEGER PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    uuid TEXT NOT NULL,
    name TEXT NOT NULL
);

CREATE TABLE topic_aspect (
    id INTEGER PRIMARY KEY,
    topic_id INTEGER NOT NULL REFERENCES topic(id),
    label TEXT,
    source TEXT
);

CREATE TABLE topic_aspect_verse (
    aspect_id INTEGER NOT NULL REFERENCES topic_aspect(id),
    verse_id INTEGER NOT NULL REFERENCES verse(id),
    PRIMARY KEY (aspect_id, verse_id)
);

CREATE TABLE topic_see_also (
    topic_id INTEGER NOT NULL REFERENCES topic(id),
    related_topic_id INTEGER NOT NULL REFERENCES topic(id),
    PRIMARY KEY (topic_id, related_topic_id)
);

CREATE TABLE cross_reference (
    id INTEGER PRIMARY KEY,
    from_verse_id INTEGER NOT NULL REFERENCES verse(id),
    to_verse_start_id INTEGER NOT NULL REFERENCES verse(id),
    to_verse_end_id INTEGER REFERENCES verse(id),
    votes INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE gnosis_meta (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE INDEX idx_verse_osis_ref ON verse(osis_ref);
CREATE INDEX idx_person_name ON person(name);
CREATE INDEX idx_person_father_id ON person(father_id);
CREATE INDEX idx_person_mother_id ON person(mother_id);
CREATE INDEX idx_place_name ON place(name);
CREATE INDEX idx_event_sort_key ON event(sort_key);
CREATE INDEX idx_person_verse_verse_id ON person_verse(verse_id);
CREATE INDEX idx_place_verse_verse_id ON place_verse(verse_id);
CREATE INDEX idx_event_verse_verse_id ON event_verse(verse_id);
CREATE INDEX idx_person_sibling_sibling_id ON person_sibling(sibling_id);
CREATE INDEX idx_person_child_child_id ON person_child(child_id);
CREATE INDEX idx_person_partner_partner_id ON person_partner(partner_id);
CREATE INDEX idx_person_group_group_id ON person_group(group_id);
CREATE INDEX idx_event_participant_person_id ON event_participant(person_id);
CREATE INDEX idx_strongs_number ON strongs(number);
CREATE INDEX idx_dict_entry_name ON dictionary_entry(name);
CREATE INDEX idx_dict_def_entry ON dictionary_definition(entry_id);
CREATE INDEX idx_topic_name ON topic(name);
CREATE INDEX idx_topic_aspect_topic ON topic_aspect(topic_id);
CREATE INDEX idx_xref_from ON cross_reference(from_verse_id);
CREATE INDEX idx_xref_to ON cross_reference(to_verse_start_id);
"""


def write_sqlite(
    people: dict[str, Person],
    places: dict[str, Place],
    events: dict[str, Event],
    groups: dict[str, PeopleGroup],
    cross_refs: dict[str, CrossReferenceEntry],
    strongs: dict[str, StrongsEntry],
    dictionary: dict[str, DictionaryEntry],
    topics: dict[str, Topic],
    output_dir: Path,
) -> Path:
    """Write all gnosis data to a SQLite database. Returns the path to the DB file."""
    db_path = output_dir / "gnosis.db"
    db_path.unlink(missing_ok=True)

    con = sqlite3.connect(str(db_path))
    con.execute("PRAGMA journal_mode=DELETE")
    con.execute("PRAGMA page_size=4096")
    con.execute("PRAGMA foreign_keys=ON")

    con.executescript(_SCHEMA)
    con.execute("BEGIN")

    # 1. Collect all unique verses and insert
    all_verses: set[str] = set()
    for p in people.values():
        all_verses.update(p.verses)
    for pl in places.values():
        all_verses.update(pl.verses)
    for e in events.values():
        all_verses.update(e.verses)
    for from_v, entry in cross_refs.items():
        all_verses.add(from_v)
        for t in entry.targets:
            all_verses.add(t.verse_start)
            if t.verse_end:
                all_verses.add(t.verse_end)
    for d_entry in dictionary.values():
        all_verses.update(d_entry.scripture_refs)
    for t in topics.values():
        for asp in t.aspects:
            all_verses.update(asp.verses)

    verse_to_id: dict[str, int] = {}
    for i, ref in enumerate(sorted(all_verses), start=1):
        verse_to_id[ref] = i
    con.executemany(
        "INSERT INTO verse (id, osis_ref) VALUES (?, ?)",
        ((vid, ref) for ref, vid in verse_to_id.items()),
    )

    # 2. Insert places
    place_slug_to_id: dict[str, int] = {}
    for i, (slug, pl) in enumerate(sorted(places.items()), start=1):
        place_slug_to_id[slug] = i
        con.execute(
            "INSERT INTO place (id, slug, uuid, name, kjv_name, esv_name, "
            "latitude, longitude, coordinate_source, feature_type, feature_sub_type, "
            "modern_name, theographic_id, openbible_id, status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                i, slug, pl.uuid, pl.name, pl.kjv_name, pl.esv_name,
                pl.latitude, pl.longitude, pl.coordinate_source,
                pl.feature_type, pl.feature_sub_type, pl.modern_name,
                pl.theographic_id, pl.openbible_id, pl.status,
            ),
        )

    # 3. Insert people — first pass without self-referential FKs
    person_slug_to_id: dict[str, int] = {}
    for i, (slug, p) in enumerate(sorted(people.items()), start=1):
        person_slug_to_id[slug] = i
        con.execute(
            "INSERT INTO person (id, slug, uuid, name, gender, "
            "birth_year, death_year, birth_year_display, death_year_display, "
            "birth_place_id, death_place_id, verse_count, first_mention, "
            "name_meaning, status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                i, slug, p.uuid, p.name, p.gender,
                p.birth_year, p.death_year, p.birth_year_display, p.death_year_display,
                place_slug_to_id.get(p.birth_place) if p.birth_place else None,
                place_slug_to_id.get(p.death_place) if p.death_place else None,
                p.verse_count, p.first_mention, p.name_meaning, p.status,
            ),
        )

    # Second pass: set father_id and mother_id
    for slug, p in people.items():
        father_id = person_slug_to_id.get(p.father) if p.father else None
        mother_id = person_slug_to_id.get(p.mother) if p.mother else None
        if father_id or mother_id:
            con.execute(
                "UPDATE person SET father_id=?, mother_id=? WHERE id=?",
                (father_id, mother_id, person_slug_to_id[slug]),
            )

    # 4. Insert events — first pass without self-referential FKs
    event_slug_to_id: dict[str, int] = {}
    for i, (slug, e) in enumerate(sorted(events.items()), start=1):
        event_slug_to_id[slug] = i
        con.execute(
            "INSERT INTO event (id, slug, uuid, title, start_year, "
            "start_year_display, duration, sort_key, theographic_id, status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                i, slug, e.uuid, e.title, e.start_year,
                e.start_year_display, e.duration, e.sort_key,
                e.theographic_id, e.status,
            ),
        )

    # Second pass: set parent_event_id and predecessor_id
    for slug, e in events.items():
        parent_id = event_slug_to_id.get(e.parent_event) if e.parent_event else None
        pred_id = event_slug_to_id.get(e.predecessor) if e.predecessor else None
        if parent_id or pred_id:
            con.execute(
                "UPDATE event SET parent_event_id=?, predecessor_id=? WHERE id=?",
                (parent_id, pred_id, event_slug_to_id[slug]),
            )

    # 5. Insert groups
    group_slug_to_id: dict[str, int] = {}
    for i, (slug, g) in enumerate(sorted(groups.items()), start=1):
        group_slug_to_id[slug] = i
        con.execute(
            "INSERT INTO people_group (id, slug, uuid, name, theographic_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (i, slug, g.uuid, g.name, g.theographic_id),
        )

    # 6. Junction tables
    con.executemany(
        "INSERT OR IGNORE INTO person_verse (person_id, verse_id) VALUES (?, ?)",
        (
            (person_slug_to_id[slug], verse_to_id[v])
            for slug, p in people.items()
            for v in p.verses
            if v in verse_to_id
        ),
    )

    con.executemany(
        "INSERT OR IGNORE INTO place_verse (place_id, verse_id) VALUES (?, ?)",
        (
            (place_slug_to_id[slug], verse_to_id[v])
            for slug, pl in places.items()
            for v in pl.verses
            if v in verse_to_id
        ),
    )

    con.executemany(
        "INSERT OR IGNORE INTO event_verse (event_id, verse_id) VALUES (?, ?)",
        (
            (event_slug_to_id[slug], verse_to_id[v])
            for slug, e in events.items()
            for v in e.verses
            if v in verse_to_id
        ),
    )

    con.executemany(
        "INSERT OR IGNORE INTO person_sibling (person_id, sibling_id) VALUES (?, ?)",
        (
            (person_slug_to_id[slug], person_slug_to_id[sib])
            for slug, p in people.items()
            for sib in p.siblings
            if sib in person_slug_to_id
        ),
    )

    con.executemany(
        "INSERT OR IGNORE INTO person_child (parent_id, child_id) VALUES (?, ?)",
        (
            (person_slug_to_id[slug], person_slug_to_id[child])
            for slug, p in people.items()
            for child in p.children
            if child in person_slug_to_id
        ),
    )

    con.executemany(
        "INSERT OR IGNORE INTO person_partner (person_id, partner_id) VALUES (?, ?)",
        (
            (person_slug_to_id[slug], person_slug_to_id[partner])
            for slug, p in people.items()
            for partner in p.partners
            if partner in person_slug_to_id
        ),
    )

    con.executemany(
        "INSERT OR IGNORE INTO person_group (person_id, group_id) VALUES (?, ?)",
        (
            (person_slug_to_id[slug], group_slug_to_id[grp])
            for slug, p in people.items()
            for grp in p.people_groups
            if grp in group_slug_to_id
        ),
    )

    con.executemany(
        "INSERT OR IGNORE INTO event_participant (event_id, person_id) VALUES (?, ?)",
        (
            (event_slug_to_id[slug], person_slug_to_id[part])
            for slug, e in events.items()
            for part in e.participants
            if part in person_slug_to_id
        ),
    )

    # 7. Strong's concordance
    for i, (number, s) in enumerate(sorted(strongs.items()), start=1):
        con.execute(
            "INSERT INTO strongs (id, number, uuid, language, lemma, "
            "transliteration, pronunciation, definition, kjv_usage) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                i, number, s.uuid, s.language, s.lemma,
                s.transliteration, s.pronunciation, s.definition, s.kjv_usage,
            ),
        )

    # 8. Dictionary entries
    dict_slug_to_id: dict[str, int] = {}
    def_id = 0
    for i, (slug, d) in enumerate(sorted(dictionary.items()), start=1):
        dict_slug_to_id[slug] = i
        con.execute(
            "INSERT INTO dictionary_entry (id, slug, uuid, name) "
            "VALUES (?, ?, ?, ?)",
            (i, slug, d.uuid, d.name),
        )
        for defn in d.definitions:
            def_id += 1
            con.execute(
                "INSERT INTO dictionary_definition (id, entry_id, source, text) "
                "VALUES (?, ?, ?, ?)",
                (def_id, i, defn.source, defn.text),
            )

    con.executemany(
        "INSERT OR IGNORE INTO dictionary_verse (entry_id, verse_id) "
        "VALUES (?, ?)",
        (
            (dict_slug_to_id[slug], verse_to_id[v])
            for slug, d in dictionary.items()
            for v in d.scripture_refs
            if v in verse_to_id
        ),
    )

    # 9. Topics
    topic_slug_to_id: dict[str, int] = {}
    aspect_id = 0
    for i, (slug, t) in enumerate(sorted(topics.items()), start=1):
        topic_slug_to_id[slug] = i
        con.execute(
            "INSERT INTO topic (id, slug, uuid, name) VALUES (?, ?, ?, ?)",
            (i, slug, t.uuid, t.name),
        )
        for asp in t.aspects:
            aspect_id += 1
            con.execute(
                "INSERT INTO topic_aspect (id, topic_id, label, source) "
                "VALUES (?, ?, ?, ?)",
                (aspect_id, i, asp.label, asp.source),
            )
            con.executemany(
                "INSERT OR IGNORE INTO topic_aspect_verse (aspect_id, verse_id) "
                "VALUES (?, ?)",
                (
                    (aspect_id, verse_to_id[v])
                    for v in asp.verses
                    if v in verse_to_id
                ),
            )

    con.executemany(
        "INSERT OR IGNORE INTO topic_see_also (topic_id, related_topic_id) "
        "VALUES (?, ?)",
        (
            (topic_slug_to_id[slug], topic_slug_to_id[sa])
            for slug, t in topics.items()
            for sa in t.see_also
            if sa in topic_slug_to_id
        ),
    )

    # 10. Cross-references
    xref_rows = []
    for from_v, entry in cross_refs.items():
        from_id = verse_to_id.get(from_v)
        if from_id is None:
            continue
        for t in entry.targets:
            start_id = verse_to_id.get(t.verse_start)
            if start_id is None:
                continue
            end_id = verse_to_id.get(t.verse_end) if t.verse_end else None
            xref_rows.append((from_id, start_id, end_id, t.votes))
    con.executemany(
        "INSERT INTO cross_reference (from_verse_id, to_verse_start_id, to_verse_end_id, votes) "
        "VALUES (?, ?, ?, ?)",
        xref_rows,
    )

    # 11. Metadata
    con.execute(
        "INSERT INTO gnosis_meta (key, value) VALUES (?, ?)",
        ("version", "0.1.0"),
    )
    con.execute(
        "INSERT INTO gnosis_meta (key, value) VALUES (?, ?)",
        ("build_date", datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")),
    )

    con.execute("COMMIT")
    con.execute("VACUUM")
    con.close()

    return db_path
