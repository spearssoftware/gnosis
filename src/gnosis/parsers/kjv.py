"""Parser for KJV verse text from scrollmapper/bible_databases SQLite."""

import sqlite3
from pathlib import Path

from gnosis.osis import book_to_osis


def parse_kjv(sources_dir: Path) -> dict[str, str]:
    """Parse KJV verse text into a dict of {osis_ref: text}.

    Source: scrollmapper/bible_databases KJV.db
    """
    db_path = sources_dir / "scrollmapper" / "kjv.db"
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row

    books = {row["id"]: row["name"] for row in con.execute("SELECT id, name FROM KJV_books")}

    # Build book_id → OSIS abbreviation mapping
    book_osis: dict[int, str] = {}
    for book_id, name in books.items():
        osis = book_to_osis(name)
        if osis is None:
            raise ValueError(f"Unknown KJV book name: {name!r} (id={book_id})")
        book_osis[book_id] = osis

    verses: dict[str, str] = {}
    for row in con.execute("SELECT book_id, chapter, verse, text FROM KJV_verses ORDER BY id"):
        osis = book_osis.get(row["book_id"])
        if osis is None:
            continue
        ref = f"{osis}.{row['chapter']}.{row['verse']}"
        verses[ref] = row["text"].strip()

    con.close()
    return verses
