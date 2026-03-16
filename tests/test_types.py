from gnosis.types import Event, PeopleGroup, Person, Place, VerseEntry


def test_person_minimal():
    p = Person(id="abraham", uuid="abc-123", name="Abraham")
    assert p.id == "abraham"
    assert p.verses == []
    assert p.verse_count == 0


def test_person_full():
    p = Person(
        id="abraham",
        uuid="abc-123",
        name="Abraham",
        gender="Male",
        birth_year=-2165,
        birth_year_display="2166 BC",
        birth_era="BC",
        father="terah",
        children=["isaac", "ishmael"],
        verses=["Gen.12.1"],
        verse_count=1,
    )
    assert p.father == "terah"
    assert len(p.children) == 2


def test_place_serialization():
    p = Place(
        id="jerusalem",
        uuid="xyz-456",
        name="Jerusalem",
        latitude=31.7683,
        longitude=35.2137,
    )
    data = p.model_dump(exclude_none=True)
    assert "latitude" in data
    assert "openbible_id" not in data


def test_event_minimal():
    e = Event(id="exodus", uuid="evt-789", title="The Exodus")
    assert e.participants == []


def test_people_group():
    g = PeopleGroup(id="tribe-of-judah", uuid="grp-1", name="Tribe of Judah")
    assert g.members == []


def test_verse_entry():
    v = VerseEntry(people=["abraham"], places=["ur"])
    assert v.events == []
