import json
from pathlib import Path

from gnosis.parsers.dictionaries import (
    _convert_ref,
    link_dictionary_entities,
    parse_dictionaries,
)
from gnosis.types.dictionary import DictionaryDefinition, DictionaryEntry


def test_convert_ref():
    assert _convert_ref("Genesis 1:1") == "Gen.1.1"
    assert _convert_ref("Revelation 22:21") == "Rev.22.21"
    assert _convert_ref("1 Corinthians 13:4") == "1Cor.13.4"


def test_convert_ref_invalid():
    assert _convert_ref("not a reference") is None
    assert _convert_ref("") is None


def test_dictionary_entry_model():
    entry = DictionaryEntry(
        id="aaron", uuid="u-aaron", name="Aaron",
        definitions=[DictionaryDefinition(source="SMI", text="brother of Moses")],
        scripture_refs=["Exod.4.14"],
    )
    assert len(entry.definitions) == 1
    assert entry.related_people == []


def test_parse_dictionaries(tmp_path: Path):
    d = tmp_path / "dictionaries" / "smith"
    d.mkdir(parents=True)

    entries = {
        "AARON": {
            "name": "Aaron",
            "slug": "aaron",
            "definitions": [{"source": "SMI", "text": "brother of Moses"}],
            "scripture_refs": [{"reference": "Exodus 4:14", "original": "Ex 4:14"}],
        },
        "ABEL": {
            "name": "Abel",
            "slug": "abel",
            "definitions": [{"source": "SMI", "text": "son of Adam"}],
            "scripture_refs": [{"reference": "Genesis 4:2", "original": "Gen 4:2"}],
        },
    }
    (d / "a.json").write_text(json.dumps(entries))

    result = parse_dictionaries(tmp_path)
    assert "aaron" in result
    assert "abel" in result
    assert result["aaron"].definitions[0].source == "SMI"
    assert result["aaron"].scripture_refs == ["Exod.4.14"]


def test_parse_dictionaries_merge(tmp_path: Path):
    """Entries with same slug from different sources should merge."""
    for source in ["smith", "hastings"]:
        d = tmp_path / "dictionaries" / source
        d.mkdir(parents=True)
        code = "SMI" if source == "smith" else "HAS"
        entries = {
            "AARON": {
                "name": "Aaron",
                "slug": "aaron",
                "definitions": [{"source": code, "text": f"{source} definition"}],
                "scripture_refs": [{"reference": "Exodus 4:14", "original": "Ex 4:14"}],
            },
        }
        (d / "a.json").write_text(json.dumps(entries))

    result = parse_dictionaries(tmp_path)
    assert len(result["aaron"].definitions) == 2
    sources = {d.source for d in result["aaron"].definitions}
    assert sources == {"SMI", "HAS"}


def test_link_dictionary_entities():
    entry = DictionaryEntry(
        id="aaron", uuid="u", name="Aaron", definitions=[],
    )
    dictionary = {"aaron": entry}
    people = {"aaron": object(), "moses": object()}
    places = {"jerusalem": object()}

    link_dictionary_entities(dictionary, people, places)
    assert "aaron" in entry.related_people
    assert entry.related_places == []
