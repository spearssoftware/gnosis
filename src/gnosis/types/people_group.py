from pydantic import BaseModel


class PeopleGroup(BaseModel):
    id: str
    uuid: str
    name: str

    # Relations
    members: list[str] = []
    verses: list[str] = []

    # Traceability
    theographic_id: str | None = None
