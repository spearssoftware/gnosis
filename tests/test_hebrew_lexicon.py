from pathlib import Path

from gnosis.parsers.hebrew_lexicon import parse_hebrew_lexicon
from gnosis.types.hebrew import LexiconEntry


def test_lexicon_entry_model():
    e = LexiconEntry(
        id="aab", uuid="u-aab", hebrew="אֵב",
        transliteration="ʾēb", part_of_speech="N",
        gloss="freshness", strongs_number="H3", twot_number="1a",
    )
    assert e.hebrew == "אֵב"
    assert e.strongs_number == "H3"


def test_parse_hebrew_lexicon(tmp_path: Path):
    d = tmp_path / "hebrew-lexicon"
    d.mkdir()

    (d / "LexicalIndex.xml").write_text("""\
<?xml version="1.0" encoding="UTF-8"?>
<index xmlns="http://openscriptures.github.com/morphhb/namespace">
<entry id="aab">
  <w xlit="ʾēb">אֵב</w>
  <pos>N</pos>
  <def>freshness</def>
  <xref bdb="a.ab.ab" strong="3" twot="1a"/>
</entry>
<entry id="aac">
  <w xlit="ʾāb">אָב</w>
  <pos>N</pos>
  <def>father</def>
  <xref bdb="a.ae.ab" strong="1" twot="4a"/>
</entry>
</index>
""")

    result = parse_hebrew_lexicon(tmp_path)
    assert "aab" in result
    assert "aac" in result
    assert result["aab"].gloss == "freshness"
    assert result["aab"].strongs_number == "H3"
    assert result["aac"].gloss == "father"
    assert result["aac"].strongs_number == "H1"
