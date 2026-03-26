from pathlib import Path

from gnosis.parsers.macula_greek import _ref_to_osis, parse_macula_greek
from gnosis.types.greek import GreekVerse, GreekWord


def test_ref_to_osis_simple():
    assert _ref_to_osis("MAT 1:1!1") == "Matt.1.1"


def test_ref_to_osis_strips_position():
    assert _ref_to_osis("REV 22:21!14") == "Rev.22.21"


def test_ref_to_osis_unknown_book():
    assert _ref_to_osis("XYZ 1:1!1") is None


def test_greek_word_model():
    w = GreekWord(
        word_id="n40001001001", text="Βίβλος",
        lemma="βίβλος", strongs_number="G976", morph="N-NSF",
    )
    assert w.word_id == "n40001001001"
    assert w.strongs_number == "G976"


def test_greek_verse_model():
    v = GreekVerse(
        osis_ref="Matt.1.1",
        words=[GreekWord(
            word_id="n40001001001", text="Βίβλος",
            lemma="βίβλος", strongs_number="G976", morph="N-NSF",
        )],
    )
    assert len(v.words) == 1


def test_parse_macula_greek(tmp_path: Path):
    d = tmp_path / "macula-greek"
    d.mkdir()
    tsv = d / "macula-greek-SBLGNT.tsv"
    tsv.write_text(
        "xml:id\tref\trole\tclass\ttype\tenglish\tmandarin\tgloss\ttext\t"
        "after\tlemma\tnormalized\tstrong\tmorph\tperson\tnumber\tgender\t"
        "case\ttense\tvoice\tmood\tdegree\tdomain\tln\tframe\tsubjref\treferent\n"
        "n40001001001\tMAT 1:1!1\t\tnoun\tcommon\tbook\t谱\t[The] book\t"
        "Βίβλος\t \tβίβλος\tΒίβλος\t976\tN-NSF\t\t\t\t\t\t\t\t\t\t\t\t\t\n"
        "n40001001002\tMAT 1:1!2\t\tnoun\tcommon\tgenealogy\t族\t"
        "of [the] genealogy\tγενέσεως\t \tγένεσις\tγενέσεως\t1078\tN-GSF\t"
        "\t\t\t\t\t\t\t\t\t\t\t\t\n"
    )

    result = parse_macula_greek(tmp_path)
    assert "Matt.1.1" in result
    assert len(result["Matt.1.1"].words) == 2
    assert result["Matt.1.1"].words[0].strongs_number == "G976"
    assert result["Matt.1.1"].words[1].strongs_number == "G1078"
    assert result["Matt.1.1"].words[0].text == "Βίβλος"
