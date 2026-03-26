from pathlib import Path

from gnosis.parsers.dodson import parse_dodson
from gnosis.types.greek import GreekLexiconEntry


def test_greek_lexicon_entry_model():
    entry = GreekLexiconEntry(
        strongs_number="G3056",
        uuid="u-g3056",
        greek="lo/gos",
        short_gloss="a word",
        long_gloss="a word, speech, divine expression",
        gk_number="3364",
    )
    assert entry.strongs_number == "G3056"
    assert entry.greek == "lo/gos"


def test_parse_dodson(tmp_path: Path):
    d = tmp_path / "dodson"
    d.mkdir()
    csv = d / "dodson.csv"
    csv.write_text(
        '"Strong\'s"\t"Goodrick-Kohlenberger"\t"Greek Word"\t'
        '"English Definition (brief)"\t"English Definition (longer)"\n'
        '"3056"\t"3364"\t"lo/gos"\t"a word"\t"a word, speech, divine expression"\n'
        '"3057"\t"3365"\t"lo/gxh"\t"a lance"\t"a lance, spear"\n'
    )

    result = parse_dodson(tmp_path)
    assert "G3056" in result
    assert "G3057" in result
    assert result["G3056"].greek == "lo/gos"
    assert result["G3056"].short_gloss == "a word"
    assert result["G3056"].gk_number == "3364"
    assert result["G3056"].uuid  # deterministic UUID was generated
