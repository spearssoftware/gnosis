import json
from pathlib import Path

from gnosis.parsers.strongs import _load_js_json, parse_strongs
from gnosis.types.strongs import StrongsEntry


def test_strongs_entry_model():
    e = StrongsEntry(
        id="H1", uuid="u-h1", language="hebrew",
        lemma="אָב", transliteration="ʼâb", pronunciation="awb",
        definition="father", kjv_usage="chief, father",
    )
    assert e.id == "H1"
    assert e.language == "hebrew"


def test_strongs_entry_minimal():
    e = StrongsEntry(id="G1", uuid="u-g1", language="greek")
    assert e.lemma is None
    assert e.definition is None


def test_load_js_json(tmp_path: Path):
    js = tmp_path / "test.json"
    js.write_text('var dict = {"key": "value"};\nmodule.exports = dict;\n')
    data = _load_js_json(js)
    assert data == {"key": "value"}


def test_parse_strongs(tmp_path: Path):
    d = tmp_path / "strongs"
    d.mkdir()

    heb = {"H1": {"lemma": "אָב", "xlit": "ab", "pron": "awb",
                   "strongs_def": "father", "kjv_def": "father"}}
    (d / "hebrew.json").write_text(
        f"var strongsHebrewDictionary = {json.dumps(heb)};\n"
    )

    grk = {"G1": {"lemma": "Α", "translit": "A",
                   "strongs_def": "first letter", "kjv_def": "Alpha"}}
    (d / "greek.json").write_text(
        f"var strongsGreekDictionary = {json.dumps(grk)};\n"
    )

    result = parse_strongs(tmp_path)
    assert "H1" in result
    assert "G1" in result
    assert result["H1"].language == "hebrew"
    assert result["H1"].pronunciation == "awb"
    assert result["G1"].language == "greek"
    assert result["G1"].pronunciation is None
    # UUIDs should be deterministic
    assert result["H1"].uuid == result["H1"].uuid
