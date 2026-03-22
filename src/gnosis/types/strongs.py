from typing import Literal

from pydantic import BaseModel


class StrongsEntry(BaseModel):
    id: str
    uuid: str
    language: Literal["hebrew", "greek"]
    lemma: str | None = None
    transliteration: str | None = None
    pronunciation: str | None = None
    definition: str | None = None
    kjv_usage: str | None = None
