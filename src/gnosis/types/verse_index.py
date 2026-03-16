from pydantic import BaseModel


class VerseEntry(BaseModel):
    people: list[str] = []
    places: list[str] = []
    events: list[str] = []
