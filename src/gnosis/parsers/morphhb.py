"""Parser for openscriptures/morphhb Hebrew Bible morphological data."""

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from gnosis.types.hebrew import HebrewVerse, HebrewWord

_NS = {"o": "http://www.bibletechnologies.net/2003/OSIS/namespace"}

# Hebrew prefix codes in morphhb lemma fields.
_PREFIXES = {"b", "c", "d", "k", "l", "m", "s"}

# Pattern to detect a Strong's number (with optional augmentation letter).
_STRONGS_RE = re.compile(r"^(\d+)(\s+[a-z])?$")


def _extract_strongs(lemma_raw: str) -> str | None:
    """Extract the primary Strong's number from a lemma field.

    Lemma format: slash-separated segments where prefixes are single letters
    and the core is a Strong's number (e.g., "b/7225" -> "H7225",
    "1254 a" -> "H1254").
    """
    segments = lemma_raw.split("/")
    for seg in segments:
        seg = seg.strip()
        if seg in _PREFIXES:
            continue
        m = _STRONGS_RE.match(seg)
        if m:
            return f"H{m.group(1)}"
    return None


def parse_morphhb(sources_dir: Path) -> dict[str, HebrewVerse]:
    """Parse morphhb OSIS XML files into HebrewVerse objects.

    Returns dict keyed by OSIS ref (e.g., "Gen.1.1").
    """
    morphhb_dir = sources_dir / "morphhb"
    result: dict[str, HebrewVerse] = {}

    for xml_path in sorted(morphhb_dir.glob("*.xml")):
        if xml_path.name == "VerseMap.xml":
            continue

        tree = ET.parse(xml_path)
        root = tree.getroot()

        for verse_el in root.iter(f"{{{_NS['o']}}}verse"):
            osis_ref = verse_el.get("osisID", "")
            if not osis_ref:
                continue

            words: list[HebrewWord] = []
            for w_el in verse_el.findall("o:w", _NS):
                text = w_el.text or ""
                lemma = w_el.get("lemma", "")
                morph = w_el.get("morph", "")
                word_id = w_el.get("id", "")

                if not word_id:
                    continue

                words.append(HebrewWord(
                    word_id=word_id,
                    text=text,
                    lemma_raw=lemma,
                    strongs_number=_extract_strongs(lemma),
                    morph=morph,
                ))

            if words:
                result[osis_ref] = HebrewVerse(osis_ref=osis_ref, words=words)

    return result
