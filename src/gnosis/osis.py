"""OSIS book name mapping and verse reference utilities."""

# Canonical OSIS abbreviations used throughout gnosis.
# Maps common English book names (and aliases) to OSIS abbreviations.
BOOK_TO_OSIS: dict[str, str] = {
    # Old Testament
    "Genesis": "Gen",
    "Exodus": "Exod",
    "Leviticus": "Lev",
    "Numbers": "Num",
    "Deuteronomy": "Deut",
    "Joshua": "Josh",
    "Judges": "Judg",
    "Ruth": "Ruth",
    "1 Samuel": "1Sam",
    "2 Samuel": "2Sam",
    "1 Kings": "1Kgs",
    "2 Kings": "2Kgs",
    "1 Chronicles": "1Chr",
    "2 Chronicles": "2Chr",
    "Ezra": "Ezra",
    "Nehemiah": "Neh",
    "Esther": "Esth",
    "Job": "Job",
    "Psalms": "Ps",
    "Proverbs": "Prov",
    "Ecclesiastes": "Eccl",
    "Song of Solomon": "Song",
    "Isaiah": "Isa",
    "Jeremiah": "Jer",
    "Lamentations": "Lam",
    "Ezekiel": "Ezek",
    "Daniel": "Dan",
    "Hosea": "Hos",
    "Joel": "Joel",
    "Amos": "Amos",
    "Obadiah": "Obad",
    "Jonah": "Jonah",
    "Micah": "Mic",
    "Nahum": "Nah",
    "Habakkuk": "Hab",
    "Zephaniah": "Zeph",
    "Haggai": "Hag",
    "Zechariah": "Zech",
    "Malachi": "Mal",
    # New Testament
    "Matthew": "Matt",
    "Mark": "Mark",
    "Luke": "Luke",
    "John": "John",
    "Acts": "Acts",
    "Romans": "Rom",
    "1 Corinthians": "1Cor",
    "2 Corinthians": "2Cor",
    "Galatians": "Gal",
    "Ephesians": "Eph",
    "Philippians": "Phil",
    "Colossians": "Col",
    "1 Thessalonians": "1Thess",
    "2 Thessalonians": "2Thess",
    "1 Timothy": "1Tim",
    "2 Timothy": "2Tim",
    "Titus": "Titus",
    "Philemon": "Phlm",
    "Hebrews": "Heb",
    "James": "Jas",
    "1 Peter": "1Pet",
    "2 Peter": "2Pet",
    "1 John": "1John",
    "2 John": "2John",
    "3 John": "3John",
    "Jude": "Jude",
    "Revelation": "Rev",
}

# Common aliases that map to the same OSIS abbreviation.
_ALIASES: dict[str, str] = {
    # Variant spellings
    "Psalm": "Ps",
    "Song of Songs": "Song",
    "Revelation of John": "Rev",
    # Roman numeral forms
    "I Samuel": "1Sam",
    "II Samuel": "2Sam",
    "I Kings": "1Kgs",
    "II Kings": "2Kgs",
    "I Chronicles": "1Chr",
    "II Chronicles": "2Chr",
    "I Corinthians": "1Cor",
    "II Corinthians": "2Cor",
    "I Thessalonians": "1Thess",
    "II Thessalonians": "2Thess",
    "I Timothy": "1Tim",
    "II Timothy": "2Tim",
    "I Peter": "1Pet",
    "II Peter": "2Pet",
    "I John": "1John",
    "II John": "2John",
    "III John": "3John",
    # Abbreviation forms commonly seen in datasets
    "Gen": "Gen",
    "Exod": "Exod",
    "Exo": "Exod",
    "Lev": "Lev",
    "Num": "Num",
    "Deut": "Deut",
    "Deu": "Deut",
    "Josh": "Josh",
    "Jos": "Josh",
    "Judg": "Judg",
    "Jdg": "Judg",
    "Rth": "Ruth",
    "1Sam": "1Sam",
    "1Sa": "1Sam",
    "2Sam": "2Sam",
    "2Sa": "2Sam",
    "1Kgs": "1Kgs",
    "1Ki": "1Kgs",
    "2Kgs": "2Kgs",
    "2Ki": "2Kgs",
    "1Chr": "1Chr",
    "1Ch": "1Chr",
    "2Chr": "2Chr",
    "2Ch": "2Chr",
    "Ezr": "Ezra",
    "Neh": "Neh",
    "Est": "Esth",
    "Esth": "Esth",
    "Psa": "Ps",
    "Ps": "Ps",
    "Pro": "Prov",
    "Prov": "Prov",
    "Ecc": "Eccl",
    "Eccl": "Eccl",
    "Sol": "Song",
    "Song": "Song",
    "SOS": "Song",
    "Isa": "Isa",
    "Jer": "Jer",
    "Lam": "Lam",
    "Ezek": "Ezek",
    "Eze": "Ezek",
    "Dan": "Dan",
    "Hos": "Hos",
    "Joe": "Joel",
    "Amo": "Amos",
    "Oba": "Obad",
    "Obad": "Obad",
    "Jon": "Jonah",
    "Mic": "Mic",
    "Nah": "Nah",
    "Hab": "Hab",
    "Zep": "Zeph",
    "Zeph": "Zeph",
    "Hag": "Hag",
    "Zec": "Zech",
    "Zech": "Zech",
    "Mal": "Mal",
    "Mat": "Matt",
    "Matt": "Matt",
    "Mar": "Mark",
    "Mrk": "Mark",
    "Luk": "Luke",
    "Joh": "John",
    "Jhn": "John",
    "Act": "Acts",
    "Rom": "Rom",
    "1Cor": "1Cor",
    "1Co": "1Cor",
    "2Cor": "2Cor",
    "2Co": "2Cor",
    "Gal": "Gal",
    "Eph": "Eph",
    "Phi": "Phil",
    "Phil": "Phil",
    "Col": "Col",
    "1Thess": "1Thess",
    "1Th": "1Thess",
    "2Thess": "2Thess",
    "2Th": "2Thess",
    "1Tim": "1Tim",
    "1Ti": "1Tim",
    "2Tim": "2Tim",
    "2Ti": "2Tim",
    "Tit": "Titus",
    "Phm": "Phlm",
    "Phlm": "Phlm",
    "Heb": "Heb",
    "Jas": "Jas",
    "Jam": "Jas",
    "1Pet": "1Pet",
    "1Pe": "1Pet",
    "2Pet": "2Pet",
    "2Pe": "2Pet",
    "1John": "1John",
    "1Jn": "1John",
    "2John": "2John",
    "2Jn": "2John",
    "3John": "3John",
    "3Jn": "3John",
    "Jud": "Jude",
    "Rev": "Rev",
}

# Build a case-insensitive lookup combining canonical names and aliases.
_LOOKUP: dict[str, str] = {}
for _name, _osis in BOOK_TO_OSIS.items():
    _LOOKUP[_name.lower()] = _osis
for _name, _osis in _ALIASES.items():
    _LOOKUP[_name.lower()] = _osis

# The set of all valid OSIS book abbreviations.
OSIS_BOOKS: set[str] = set(BOOK_TO_OSIS.values())


def book_to_osis(book: str) -> str | None:
    """Look up the OSIS abbreviation for a book name or alias.

    Returns None if the book name is not recognized.
    """
    return _LOOKUP.get(book.lower())


def to_osis_ref(book: str, chapter: int, verse: int) -> str | None:
    """Convert book name + chapter + verse to an OSIS reference string.

    Returns None if the book name is not recognized.
    Example: to_osis_ref("Genesis", 1, 1) -> "Gen.1.1"
    """
    osis = book_to_osis(book)
    if osis is None:
        return None
    return f"{osis}.{chapter}.{verse}"


def to_osis_range(
    book: str, chapter: int, verse_start: int, verse_end: int
) -> str | None:
    """Convert book name + chapter + verse range to an OSIS range string.

    If verse_start == verse_end, returns a single reference (no range suffix).
    Returns None if the book name is not recognized.
    Example: to_osis_range("Genesis", 1, 1, 5) -> "Gen.1.1-5"
    """
    osis = book_to_osis(book)
    if osis is None:
        return None
    if verse_start == verse_end:
        return f"{osis}.{chapter}.{verse_start}"
    return f"{osis}.{chapter}.{verse_start}-{verse_end}"
