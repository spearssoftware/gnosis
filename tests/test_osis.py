from gnosis.osis import (
    CHAPTER_VERSE_COUNTS,
    OSIS_BOOKS,
    book_to_osis,
    is_valid_osis_ref,
    to_osis_range,
    to_osis_ref,
)


def test_all_66_books_present():
    assert len(OSIS_BOOKS) == 66


def test_canonical_names():
    assert book_to_osis("Genesis") == "Gen"
    assert book_to_osis("Revelation") == "Rev"
    assert book_to_osis("Psalms") == "Ps"
    assert book_to_osis("Song of Solomon") == "Song"


def test_case_insensitive():
    assert book_to_osis("genesis") == "Gen"
    assert book_to_osis("GENESIS") == "Gen"
    assert book_to_osis("GeNeSiS") == "Gen"


def test_numbered_books():
    assert book_to_osis("1 Samuel") == "1Sam"
    assert book_to_osis("2 Kings") == "2Kgs"
    assert book_to_osis("1 Corinthians") == "1Cor"
    assert book_to_osis("2 Timothy") == "2Tim"


def test_roman_numeral_aliases():
    assert book_to_osis("I Samuel") == "1Sam"
    assert book_to_osis("II Kings") == "2Kgs"
    assert book_to_osis("III John") == "3John"


def test_abbreviation_aliases():
    assert book_to_osis("Gen") == "Gen"
    assert book_to_osis("Exo") == "Exod"
    assert book_to_osis("Psa") == "Ps"
    assert book_to_osis("Matt") == "Matt"
    assert book_to_osis("Rev") == "Rev"
    assert book_to_osis("1Ki") == "1Kgs"
    assert book_to_osis("2Ch") == "2Chr"
    assert book_to_osis("Phm") == "Phlm"


def test_variant_spellings():
    assert book_to_osis("Psalm") == "Ps"
    assert book_to_osis("Song of Songs") == "Song"
    assert book_to_osis("Revelation of John") == "Rev"


def test_unknown_book():
    assert book_to_osis("Maccabees") is None
    assert book_to_osis("") is None
    assert book_to_osis("NotABook") is None


def test_to_osis_ref():
    assert to_osis_ref("Genesis", 1, 1) == "Gen.1.1"
    assert to_osis_ref("Psalms", 119, 176) == "Ps.119.176"
    assert to_osis_ref("1 Corinthians", 13, 4) == "1Cor.13.4"


def test_to_osis_ref_unknown_book():
    assert to_osis_ref("FakeBook", 1, 1) is None


def test_to_osis_range():
    assert to_osis_range("Genesis", 1, 1, 5) == "Gen.1.1-5"
    assert to_osis_range("Romans", 8, 28, 30) == "Rom.8.28-30"


def test_to_osis_range_single_verse():
    assert to_osis_range("Genesis", 1, 1, 1) == "Gen.1.1"


def test_to_osis_range_unknown_book():
    assert to_osis_range("FakeBook", 1, 1, 5) is None


# --- is_valid_osis_ref tests ---


def test_chapter_verse_counts_covers_all_books():
    assert set(CHAPTER_VERSE_COUNTS.keys()) == OSIS_BOOKS


def test_valid_osis_ref():
    assert is_valid_osis_ref("Gen.1.1") is True
    assert is_valid_osis_ref("Rev.22.21") is True
    assert is_valid_osis_ref("Ps.119.176") is True


def test_valid_osis_ref_range():
    assert is_valid_osis_ref("Gen.1.1-5") is True
    assert is_valid_osis_ref("Rom.8.28-30") is True


def test_invalid_verse_number():
    assert is_valid_osis_ref("Gen.50.27") is False  # Gen 50 has 26 verses


def test_invalid_chapter_number():
    assert is_valid_osis_ref("Gen.51.1") is False  # Gen has 50 chapters


def test_invalid_book():
    assert is_valid_osis_ref("Fake.1.1") is False


def test_invalid_format():
    assert is_valid_osis_ref("Gen.1") is False
    assert is_valid_osis_ref("Gen") is False
    assert is_valid_osis_ref("") is False


def test_verse_zero():
    assert is_valid_osis_ref("Gen.1.0") is False


def test_chapter_zero():
    assert is_valid_osis_ref("Gen.0.1") is False
