"""Tests for verse similarity computation."""

import json
import sqlite3
from pathlib import Path

import numpy as np
import pytest

from gnosis.vector import (
    _write_verse_similarity_json,
    _write_verse_similarity_sqlite,
    compute_verse_similarity,
)


def _make_docs_and_embeddings(
    n_verses: int = 8,
    ndim: int = 16,
) -> tuple[list[tuple[str, str, str]], np.ndarray]:
    """Create synthetic docs and normalized embeddings for testing.

    Makes 2 chapters of 4 verses each: Gen.1.1-4 and Gen.2.1-4.
    Plus 2 non-verse docs (person, place) to verify filtering.
    """
    docs: list[tuple[str, str, str]] = [
        ("adam", "person", "Adam the first man"),
        ("eden", "place", "Garden of Eden"),
    ]
    for ch in range(1, 3):
        for v in range(1, n_verses // 2 + 1):
            docs.append((f"Gen.{ch}.{v}", "verse", f"Verse text Gen {ch}:{v}"))

    rng = np.random.default_rng(42)
    emb = rng.standard_normal((len(docs), ndim)).astype(np.float32)
    # Normalize
    norms = np.linalg.norm(emb, axis=1, keepdims=True)
    emb = emb / norms
    return docs, emb


class TestComputeVerseSimilarity:
    def test_returns_only_verses(self) -> None:
        docs, emb = _make_docs_and_embeddings()
        results = compute_verse_similarity(emb, docs, top_n=3)
        refs = {ref for ref, _ in results}
        assert all(ref.startswith("Gen.") for ref in refs)
        assert len(results) == 8

    def test_self_exclusion(self) -> None:
        docs, emb = _make_docs_and_embeddings()
        results = compute_verse_similarity(emb, docs, top_n=3)
        for ref, pairs in results:
            sim_refs = [r for r, _ in pairs]
            assert ref not in sim_refs

    def test_adjacency_exclusion(self) -> None:
        docs, emb = _make_docs_and_embeddings()
        results = compute_verse_similarity(emb, docs, top_n=3, adjacency_window=2)
        for ref, pairs in results:
            parts = ref.split(".")
            book, ch, v = parts[0], parts[1], int(parts[2])
            sim_refs = [r for r, _ in pairs]
            for sr in sim_refs:
                sp = sr.split(".")
                if sp[0] == book and sp[1] == ch:
                    assert abs(int(sp[2]) - v) > 2

    def test_top_n_count(self) -> None:
        docs, emb = _make_docs_and_embeddings()
        results = compute_verse_similarity(emb, docs, top_n=3)
        for _, pairs in results:
            assert len(pairs) == 3

    def test_descending_scores(self) -> None:
        docs, emb = _make_docs_and_embeddings()
        results = compute_verse_similarity(emb, docs, top_n=3)
        for _, pairs in results:
            scores = [s for _, s in pairs]
            assert scores == sorted(scores, reverse=True)

    def test_scores_are_rounded(self) -> None:
        docs, emb = _make_docs_and_embeddings()
        results = compute_verse_similarity(emb, docs, top_n=3)
        for _, pairs in results:
            for _, score in pairs:
                assert score == round(score, 4)


class TestWriteVerseSimilaritySqlite:
    @pytest.fixture()
    def db_with_verses(self, tmp_path: Path) -> Path:
        db_path = tmp_path / "test.db"
        con = sqlite3.connect(str(db_path))
        con.execute("CREATE TABLE verse (id INTEGER PRIMARY KEY, osis_ref TEXT NOT NULL UNIQUE)")
        verses = []
        vid = 1
        for ch in range(1, 3):
            for v in range(1, 5):
                verses.append((vid, f"Gen.{ch}.{v}"))
                vid += 1
        con.executemany("INSERT INTO verse VALUES (?, ?)", verses)
        con.commit()
        con.close()
        return db_path

    def test_writes_rows(self, db_with_verses: Path) -> None:
        docs, emb = _make_docs_and_embeddings()
        results = compute_verse_similarity(emb, docs, top_n=3)
        _write_verse_similarity_sqlite(db_with_verses, results)

        con = sqlite3.connect(str(db_with_verses))
        count = con.execute("SELECT COUNT(*) FROM verse_similarity").fetchone()[0]
        assert count == 8 * 3
        con.close()

    def test_ranks_are_sequential(self, db_with_verses: Path) -> None:
        docs, emb = _make_docs_and_embeddings()
        results = compute_verse_similarity(emb, docs, top_n=3)
        _write_verse_similarity_sqlite(db_with_verses, results)

        con = sqlite3.connect(str(db_with_verses))
        for vid in range(1, 9):
            ranks = [
                r[0]
                for r in con.execute(
                    "SELECT rank FROM verse_similarity WHERE verse_id = ? ORDER BY rank",
                    (vid,),
                ).fetchall()
            ]
            assert ranks == [1, 2, 3]
        con.close()


class TestWriteVerseSimilarityJson:
    def test_writes_file(self, tmp_path: Path) -> None:
        docs, emb = _make_docs_and_embeddings()
        results = compute_verse_similarity(emb, docs, top_n=3)
        _write_verse_similarity_json(tmp_path, results)

        path = tmp_path / "verse-similarity.json"
        assert path.exists()
        data = json.loads(path.read_text())
        assert len(data) == 8
        assert "Gen.1.1" in data
        assert len(data["Gen.1.1"]) == 3
        assert "ref" in data["Gen.1.1"][0]
        assert "score" in data["Gen.1.1"][0]
