from pydantic import BaseModel


class CrossReferenceTarget(BaseModel):
    verse_start: str
    verse_end: str | None = None
    votes: int = 0


class CrossReferenceEntry(BaseModel):
    targets: list[CrossReferenceTarget]
