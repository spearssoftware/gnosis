from pydantic import BaseModel


class GreekWord(BaseModel):
    word_id: str
    text: str
    lemma: str
    strongs_number: str | None = None
    morph: str


class GreekVerse(BaseModel):
    osis_ref: str
    words: list[GreekWord]


class GreekLexiconEntry(BaseModel):
    strongs_number: str
    uuid: str
    greek: str
    transliteration: str | None = None
    part_of_speech: str | None = None
    short_gloss: str | None = None
    long_gloss: str | None = None
    gk_number: str | None = None
