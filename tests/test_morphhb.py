from pathlib import Path

from gnosis.parsers.morphhb import _extract_strongs, parse_morphhb
from gnosis.types.hebrew import HebrewVerse, HebrewWord


def test_extract_strongs_simple():
    assert _extract_strongs("7225") == "H7225"


def test_extract_strongs_with_prefix():
    assert _extract_strongs("b/7225") == "H7225"


def test_extract_strongs_with_augmentation():
    assert _extract_strongs("1254 a") == "H1254"


def test_extract_strongs_multiple_prefixes():
    assert _extract_strongs("c/d/776") == "H776"


def test_extract_strongs_prefix_only():
    assert _extract_strongs("b") is None


def test_hebrew_word_model():
    w = HebrewWord(
        word_id="01xeN", text="בְּ/רֵאשִׁ֖ית",
        lemma_raw="b/7225", strongs_number="H7225", morph="HR/Ncfsa",
    )
    assert w.word_id == "01xeN"


def test_hebrew_verse_model():
    v = HebrewVerse(
        osis_ref="Gen.1.1",
        words=[HebrewWord(
            word_id="01xeN", text="בְּ/רֵאשִׁ֖ית",
            lemma_raw="b/7225", strongs_number="H7225", morph="HR/Ncfsa",
        )],
    )
    assert len(v.words) == 1


def test_parse_morphhb(tmp_path: Path):
    d = tmp_path / "morphhb"
    d.mkdir()
    xml = d / "Gen.xml"
    xml.write_text("""\
<?xml version="1.0" encoding="utf-8"?>
<osis xmlns="http://www.bibletechnologies.net/2003/OSIS/namespace">
<osisText><div type="book" osisID="Gen">
<chapter osisID="Gen.1">
<verse osisID="Gen.1.1">
<w lemma="b/7225" morph="HR/Ncfsa" id="01xeN">בְּ/רֵאשִׁ֖ית</w>
<w lemma="1254 a" morph="HVqp3ms" id="01Nvk">בָּרָ֣א</w>
</verse>
</chapter>
</div></osisText></osis>
""")

    result = parse_morphhb(tmp_path)
    assert "Gen.1.1" in result
    assert len(result["Gen.1.1"].words) == 2
    assert result["Gen.1.1"].words[0].strongs_number == "H7225"
    assert result["Gen.1.1"].words[1].strongs_number == "H1254"
