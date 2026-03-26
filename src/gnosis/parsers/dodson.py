"""Parser for biblicalhumanities/Dodson-Greek-Lexicon data."""

import csv
from pathlib import Path

from gnosis.ids import make_uuid
from gnosis.types.greek import GreekLexiconEntry


def parse_dodson(sources_dir: Path) -> dict[str, GreekLexiconEntry]:
    """Parse Dodson Greek Lexicon CSV into GreekLexiconEntry objects.

    Returns dict keyed by Strong's number (e.g., 'G3056').
    """
    csv_path = sources_dir / "dodson" / "dodson.csv"

    result: dict[str, GreekLexiconEntry] = {}

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t", quotechar='"')
        for row in reader:
            raw_num = row["Strong's"].strip()
            if not raw_num:
                continue
            strongs_number = f"G{int(raw_num)}"

            gk = row.get("Goodrick-Kohlenberger", "").strip() or None
            greek = row.get("Greek Word", "").strip() or ""
            short_gloss = row.get("English Definition (brief)", "").strip() or None
            long_gloss = row.get("English Definition (longer)", "").strip() or None

            if not greek:
                continue

            result[strongs_number] = GreekLexiconEntry(
                strongs_number=strongs_number,
                uuid=make_uuid(f"greek-lex-{strongs_number}"),
                greek=greek,
                part_of_speech=None,
                short_gloss=short_gloss,
                long_gloss=long_gloss,
                gk_number=gk,
            )

    return result
