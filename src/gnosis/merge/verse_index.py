"""Build a verse index mapping OSIS refs to entity IDs."""

from gnosis.types import Event, Person, Place, VerseEntry


def build_verse_index(
    people: dict[str, Person],
    places: dict[str, Place],
    events: dict[str, Event],
) -> dict[str, VerseEntry]:
    """Build a verse index from all entities.

    Returns a dict of OSIS ref → VerseEntry with lists of entity IDs.
    """
    index: dict[str, VerseEntry] = {}

    for person in people.values():
        for verse in person.verses:
            index.setdefault(verse, VerseEntry()).people.append(person.id)

    for place in places.values():
        for verse in place.verses:
            index.setdefault(verse, VerseEntry()).places.append(place.id)

    for event in events.values():
        for verse in event.verses:
            index.setdefault(verse, VerseEntry()).events.append(event.id)

    return index
