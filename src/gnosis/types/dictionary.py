from pydantic import BaseModel


class DictionaryDefinition(BaseModel):
    source: str
    text: str


class DictionaryEntry(BaseModel):
    id: str
    uuid: str
    name: str
    definitions: list[DictionaryDefinition]
    scripture_refs: list[str] = []
    deuterocanonical_refs: list[str] = []
    related_people: list[str] = []
    related_places: list[str] = []
