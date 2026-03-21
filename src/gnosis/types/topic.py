from pydantic import BaseModel


class TopicAspect(BaseModel):
    label: str | None = None
    verses: list[str] = []
    source: str | None = None


class Topic(BaseModel):
    id: str
    uuid: str
    name: str
    sources: list[str] = []
    aspects: list[TopicAspect] = []
    see_also: list[str] = []
