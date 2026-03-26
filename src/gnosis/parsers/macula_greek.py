"""Parser for Clear-Bible/macula-greek NT morphological data (SBLGNT edition)."""

from pathlib import Path

import pandas as pd

from gnosis.types.greek import GreekVerse, GreekWord

# Macula-greek book abbreviations -> OSIS abbreviations.
_BOOK_TO_OSIS: dict[str, str] = {
    "MAT": "Matt", "MRK": "Mark", "LUK": "Luke", "JHN": "John",
    "ACT": "Acts", "ROM": "Rom", "1CO": "1Cor", "2CO": "2Cor",
    "GAL": "Gal", "EPH": "Eph", "PHP": "Phil", "COL": "Col",
    "1TH": "1Thess", "2TH": "2Thess", "1TI": "1Tim", "2TI": "2Tim",
    "TIT": "Titus", "PHM": "Phlm", "HEB": "Heb", "JAS": "Jas",
    "1PE": "1Pet", "2PE": "2Pet", "1JN": "1John", "2JN": "2John",
    "3JN": "3John", "JUD": "Jude", "REV": "Rev",
}


def _ref_to_osis(ref: str) -> str | None:
    """Convert macula ref like 'MAT 1:1!1' to OSIS ref like 'Matt.1.1'.

    Returns None if the book is unrecognized.
    """
    # Strip word position suffix (e.g., "!1")
    base = ref.split("!")[0]
    parts = base.split(" ")
    if len(parts) != 2:
        return None
    book_abbr, cv = parts
    osis_book = _BOOK_TO_OSIS.get(book_abbr)
    if osis_book is None:
        return None
    cv_parts = cv.split(":")
    if len(cv_parts) != 2:
        return None
    return f"{osis_book}.{cv_parts[0]}.{cv_parts[1]}"


def parse_macula_greek(sources_dir: Path) -> dict[str, GreekVerse]:
    """Parse macula-greek SBLGNT TSV into GreekVerse objects.

    Returns dict keyed by OSIS ref (e.g., 'Matt.1.1').
    """
    tsv_path = sources_dir / "macula-greek" / "macula-greek-SBLGNT.tsv"
    df = pd.read_csv(tsv_path, sep="\t", dtype=str, keep_default_na=False)

    verses: dict[str, list[GreekWord]] = {}

    for _, row in df.iterrows():
        osis_ref = _ref_to_osis(row["ref"])
        if osis_ref is None:
            continue

        strong = row.get("strong", "")
        strongs_number = f"G{strong}" if strong else None

        word = GreekWord(
            word_id=row["xml:id"],
            text=row["text"],
            lemma=row["lemma"],
            strongs_number=strongs_number,
            morph=row["morph"],
        )

        if osis_ref not in verses:
            verses[osis_ref] = []
        verses[osis_ref].append(word)

    return {
        ref: GreekVerse(osis_ref=ref, words=words)
        for ref, words in verses.items()
    }
