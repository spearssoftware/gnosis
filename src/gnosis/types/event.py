from pydantic import BaseModel


class Event(BaseModel):
    id: str
    uuid: str
    title: str

    # Dates (astronomical year integers)
    start_year: int | None = None
    start_year_display: str | None = None
    end_year: int | None = None
    end_year_display: str | None = None
    duration: str | None = None
    sort_key: float | None = None
    dates_confidence: str | None = None
    dates_source: str | None = None

    # Relations (slug ID refs)
    participants: list[str] = []
    locations: list[str] = []
    verses: list[str] = []
    parent_event: str | None = None
    predecessor: str | None = None

    # Enrichment
    date_confidence: str | None = None
    narrative_arc: str | None = None
    nt_complete: bool | None = None

    # Traceability
    theographic_id: str | None = None
    status: str | None = None
