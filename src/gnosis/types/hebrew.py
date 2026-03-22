from pydantic import BaseModel


class HebrewWord(BaseModel):
    word_id: str
    text: str
    lemma_raw: str
    strongs_number: str | None = None
    morph: str


class HebrewVerse(BaseModel):
    osis_ref: str
    words: list[HebrewWord]


class LexiconEntry(BaseModel):
    id: str
    uuid: str
    hebrew: str
    transliteration: str | None = None
    part_of_speech: str | None = None
    gloss: str | None = None
    strongs_number: str | None = None
    twot_number: str | None = None
