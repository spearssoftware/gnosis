"""Parser for openscriptures/HebrewLexicon data."""

import xml.etree.ElementTree as ET
from pathlib import Path

from gnosis.ids import make_uuid
from gnosis.types.hebrew import LexiconEntry

_NS = {"hl": "http://openscriptures.github.com/morphhb/namespace"}


def _parse_aug_index(path: Path) -> dict[int, str]:
    """Parse AugIndex.xml: maps augmented Strong's number -> lexical ID."""
    tree = ET.parse(path)
    root = tree.getroot()
    result: dict[int, str] = {}
    for w in root.findall(".//hl:w", _NS):
        aug = w.get("aug")
        if aug and w.text:
            try:
                result[int(aug)] = w.text.strip()
            except ValueError:
                continue
    return result


def _parse_lexical_index(path: Path) -> dict[str, dict]:
    """Parse LexicalIndex.xml into raw entry dicts keyed by lexical ID."""
    tree = ET.parse(path)
    root = tree.getroot()
    result: dict[str, dict] = {}

    for entry in root.findall(".//hl:entry", _NS):
        lex_id = entry.get("id", "")
        if not lex_id:
            continue

        w = entry.find("hl:w", _NS)
        pos = entry.find("hl:pos", _NS)
        defn = entry.find("hl:def", _NS)
        xref = entry.find("hl:xref", _NS)

        hebrew = w.text if w is not None and w.text else ""
        if not hebrew:
            continue

        strongs_num = None
        twot = None
        if xref is not None:
            strong_str = xref.get("strong")
            if strong_str:
                strongs_num = f"H{strong_str}"
            twot = xref.get("twot")

        result[lex_id] = {
            "hebrew": hebrew,
            "transliteration": w.get("xlit") if w is not None else None,
            "part_of_speech": pos.text if pos is not None and pos.text else None,
            "gloss": defn.text if defn is not None and defn.text else None,
            "strongs_number": strongs_num,
            "twot_number": twot,
        }

    return result


def parse_hebrew_lexicon(sources_dir: Path) -> dict[str, LexiconEntry]:
    """Parse HebrewLexicon data into LexiconEntry objects.

    Returns dict keyed by 3-letter lexical ID.
    """
    lex_dir = sources_dir / "hebrew-lexicon"
    raw_entries = _parse_lexical_index(lex_dir / "LexicalIndex.xml")

    result: dict[str, LexiconEntry] = {}
    for lex_id, data in sorted(raw_entries.items()):
        result[lex_id] = LexiconEntry(
            id=lex_id,
            uuid=make_uuid(f"lex-{lex_id}"),
            hebrew=data["hebrew"],
            transliteration=data["transliteration"],
            part_of_speech=data["part_of_speech"],
            gloss=data["gloss"],
            strongs_number=data["strongs_number"],
            twot_number=data["twot_number"],
        )

    return result
