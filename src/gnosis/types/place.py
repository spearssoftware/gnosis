from pydantic import BaseModel


class Place(BaseModel):
    id: str
    uuid: str
    name: str
    kjv_name: str | None = None
    esv_name: str | None = None

    # Geo
    latitude: float | None = None
    longitude: float | None = None
    geo_confidence: float | None = None
    precision_meters: float | None = None
    coordinate_source: str | None = None

    # Classification
    feature_type: str | None = None
    feature_sub_type: str | None = None
    place_types: list[str] = []

    # Relations (slug ID refs)
    verses: list[str] = []
    people_born: list[str] = []
    people_died: list[str] = []
    events: list[str] = []

    # Enrichment
    modern_name: str | None = None
    modern_country: str | None = None
    aliases: list[str] = []

    # Traceability
    theographic_id: str | None = None
    openbible_id: str | None = None
    status: str | None = None
