from pydantic import BaseModel


class Person(BaseModel):
    id: str
    uuid: str
    name: str
    gender: str | None = None

    # Dates (astronomical year integers)
    birth_year: int | None = None
    death_year: int | None = None
    birth_year_display: str | None = None
    death_year_display: str | None = None

    # Relations (slug ID refs)
    birth_place: str | None = None
    death_place: str | None = None
    father: str | None = None
    mother: str | None = None
    siblings: list[str] = []
    children: list[str] = []
    partners: list[str] = []

    # Scripture
    verses: list[str] = []
    verse_count: int = 0

    # Enrichment
    name_meaning: str | None = None
    role: str | None = None
    narrative_arc: str | None = None
    first_mention: str | None = None

    # Groups
    people_groups: list[str] = []

    # Traceability
    theographic_id: str | None = None
    status: str | None = None
