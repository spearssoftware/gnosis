"""Parser for openscriptures/strongs concordance data."""

import json
from pathlib import Path

from gnosis.ids import make_uuid
from gnosis.types.strongs import StrongsEntry


def _load_js_json(path: Path) -> dict:
    """Load a JSON object from a JS file that wraps it in a variable assignment."""
    raw = path.read_text(encoding="utf-8")
    start = raw.index("{")
    end = raw.rindex("}") + 1
    return json.loads(raw[start:end])


def parse_strongs(sources_dir: Path) -> dict[str, StrongsEntry]:
    """Parse Strong's Hebrew and Greek dictionaries.

    Returns dict keyed by Strong's number (e.g. "H1", "G3056").
    """
    result: dict[str, StrongsEntry] = {}
    strongs_dir = sources_dir / "strongs"

    # Hebrew
    hebrew = _load_js_json(strongs_dir / "hebrew.json")
    for number, entry in hebrew.items():
        result[number] = StrongsEntry(
            id=number,
            uuid=make_uuid(number.lower()),
            language="hebrew",
            lemma=entry.get("lemma"),
            transliteration=entry.get("xlit"),
            pronunciation=entry.get("pron"),
            definition=entry.get("strongs_def"),
            kjv_usage=entry.get("kjv_def"),
        )

    # Greek
    greek = _load_js_json(strongs_dir / "greek.json")
    for number, entry in greek.items():
        result[number] = StrongsEntry(
            id=number,
            uuid=make_uuid(number.lower()),
            language="greek",
            lemma=entry.get("lemma"),
            transliteration=entry.get("translit"),
            pronunciation=None,
            definition=entry.get("strongs_def"),
            kjv_usage=entry.get("kjv_def"),
        )

    return dict(sorted(result.items(), key=lambda kv: kv[0]))
