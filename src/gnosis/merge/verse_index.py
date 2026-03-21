"""Build a verse index mapping OSIS refs to entity IDs."""

from gnosis.types import Event, Person, Place, VerseEntry
from gnosis.types.topic import Topic


def build_verse_index(
    people: dict[str, Person],
    places: dict[str, Place],
    events: dict[str, Event],
    topics: dict[str, Topic] | None = None,
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

    if topics:
        for topic in topics.values():
            for aspect in topic.aspects:
                for verse in aspect.verses:
                    # Strip range suffixes for index lookup (e.g. "Gen.4.1-15" -> "Gen.4.1")
                    base_ref = verse.split("-")[0] if "-" in verse else verse
                    index.setdefault(base_ref, VerseEntry()).topics.append(topic.id)

    return index
