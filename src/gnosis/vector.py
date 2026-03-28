"""Build a static HNSW vector index for semantic search."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from rich.console import Console
from sentence_transformers import SentenceTransformer
from usearch.index import Index, MetricKind, ScalarKind

if TYPE_CHECKING:
    from gnosis.build import BuildContext

MODEL_NAME = "all-MiniLM-L6-v2"
NDIM = 384

console = Console()


def _entity_text(*parts: str | None) -> str:
    """Join non-None parts with '. ' separator."""
    return ". ".join(p for p in parts if p)


def _collect_documents(ctx: BuildContext) -> list[tuple[str, str, str]]:
    """Collect all embeddable documents as (slug, entity_type, text) tuples."""
    docs: list[tuple[str, str, str]] = []

    for slug, p in ctx.people.items():
        text = _entity_text(p.name, p.name_meaning, p.role, p.narrative_arc)
        if text:
            docs.append((slug, "person", text))

    for slug, p in ctx.places.items():
        text = _entity_text(p.name, p.kjv_name, p.modern_name, p.feature_type)
        if text:
            docs.append((slug, "place", text))

    for slug, e in ctx.events.items():
        text = _entity_text(e.title, e.narrative_arc, e.duration)
        if text:
            docs.append((slug, "event", text))

    for slug, t in ctx.topics.items():
        labels = [a.label for a in t.aspects if a.label]
        text = _entity_text(t.name, ", ".join(labels) if labels else None)
        if text:
            docs.append((slug, "topic", text))

    for slug, d in ctx.dictionary.items():
        first_def = d.definitions[0].text if d.definitions else None
        text = _entity_text(d.name, first_def)
        if text:
            docs.append((slug, "dictionary", text))

    for slug, s in ctx.strongs.items():
        text = _entity_text(s.lemma, s.definition, s.kjv_usage)
        if text:
            docs.append((slug, "strongs", text))

    for slug, lx in ctx.lexicon.items():
        text = _entity_text(lx.hebrew, lx.gloss)
        if text:
            docs.append((slug, "lexicon", text))

    for slug, gl in ctx.greek_lexicon.items():
        text = _entity_text(gl.greek, gl.short_gloss or gl.long_gloss)
        if text:
            docs.append((slug, "greek_lexicon", text))

    for ref, verse_text in ctx.kjv_verses.items():
        if verse_text:
            docs.append((ref, "verse", verse_text))

    return docs


def _write_vector_meta(
    db_path: Path,
    docs: list[tuple[str, str, str]],
) -> None:
    """Write vector_meta table into gnosis.db."""
    con = sqlite3.connect(str(db_path))
    con.executescript("""
        CREATE TABLE IF NOT EXISTS vector_meta (
            vector_id INTEGER PRIMARY KEY,
            entity_slug TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            embed_text TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_vector_meta_type ON vector_meta(entity_type);
        CREATE INDEX IF NOT EXISTS idx_vector_meta_slug ON vector_meta(entity_slug);
    """)
    sql = (
        "INSERT INTO vector_meta (vector_id, entity_slug, entity_type, embed_text)"
        " VALUES (?, ?, ?, ?)"
    )
    con.executemany(
        sql,
        [(i, slug, etype, text) for i, (slug, etype, text) in enumerate(docs)],
    )
    con.commit()
    con.close()


def compute_verse_similarity(
    embeddings: np.ndarray,
    docs: list[tuple[str, str, str]],
    top_n: int = 25,
    chunk_size: int = 1000,
    adjacency_window: int = 2,
) -> list[tuple[str, list[tuple[str, float]]]]:
    """Compute top-N most similar verses for every verse.

    Uses chunked matrix multiplication on normalized embeddings (dot product = cosine).
    Excludes self-matches and adjacent verses within the same chapter.
    """
    # Extract verse-only embeddings and refs
    verse_indices = [i for i, (_, etype, _) in enumerate(docs) if etype == "verse"]
    verse_refs = [docs[i][0] for i in verse_indices]
    verse_emb = embeddings[verse_indices].astype(np.float32)
    n_verses = len(verse_refs)

    # Build adjacency exclusion sets
    from collections import defaultdict
    chapter_groups: dict[tuple[str, str], list[tuple[int, int]]] = defaultdict(list)
    for idx, ref in enumerate(verse_refs):
        parts = ref.split(".")
        book, ch, v = parts[0], parts[1], int(parts[2])
        chapter_groups[(book, ch)].append((v, idx))

    exclusions: list[set[int]] = [set() for _ in range(n_verses)]
    for group in chapter_groups.values():
        for v1, i in group:
            exclusions[i].add(i)  # always exclude self
            for v2, j in group:
                if i != j and abs(v1 - v2) <= adjacency_window:
                    exclusions[i].add(j)

    # Chunked cosine similarity computation
    results: list[tuple[str, list[tuple[str, float]]]] = []
    effective_top_n = min(top_n, n_verses - 1)

    for chunk_start in range(0, n_verses, chunk_size):
        chunk_end = min(chunk_start + chunk_size, n_verses)
        chunk = verse_emb[chunk_start:chunk_end]
        sim = chunk @ verse_emb.T  # (chunk_size, n_verses)

        for local_i in range(chunk_end - chunk_start):
            global_i = chunk_start + local_i
            row = sim[local_i].copy()

            # Zero out excluded verses
            for excl_j in exclusions[global_i]:
                row[excl_j] = -2.0

            # Top-N via argpartition
            top_idx = np.argpartition(row, -effective_top_n)[-effective_top_n:]
            top_idx = top_idx[np.argsort(-row[top_idx])]
            pairs = [(verse_refs[j], round(float(row[j]), 4)) for j in top_idx]
            results.append((verse_refs[global_i], pairs))

    return results


def _write_verse_similarity_sqlite(
    db_path: Path,
    results: list[tuple[str, list[tuple[str, float]]]],
) -> None:
    """Write verse_similarity table into gnosis.db."""
    con = sqlite3.connect(str(db_path))

    # Build osis_ref -> verse.id mapping
    ref_to_id = dict(con.execute("SELECT osis_ref, id FROM verse").fetchall())

    con.executescript("""
        CREATE TABLE IF NOT EXISTS verse_similarity (
            verse_id         INTEGER NOT NULL REFERENCES verse(id),
            rank             INTEGER NOT NULL,
            similar_verse_id INTEGER NOT NULL REFERENCES verse(id),
            score            REAL NOT NULL,
            PRIMARY KEY (verse_id, rank)
        );
        CREATE INDEX IF NOT EXISTS idx_vsim_verse ON verse_similarity(verse_id);
    """)

    rows = []
    for osis_ref, pairs in results:
        verse_id = ref_to_id.get(osis_ref)
        if verse_id is None:
            continue
        for rank, (sim_ref, score) in enumerate(pairs, 1):
            sim_id = ref_to_id.get(sim_ref)
            if sim_id is not None:
                rows.append((verse_id, rank, sim_id, score))

    con.executemany(
        "INSERT INTO verse_similarity (verse_id, rank, similar_verse_id, score)"
        " VALUES (?, ?, ?, ?)",
        rows,
    )
    con.execute("ANALYZE verse_similarity")
    con.commit()
    con.close()


def _write_verse_similarity_json(
    output_dir: Path,
    results: list[tuple[str, list[tuple[str, float]]]],
) -> None:
    """Write verse-similarity.json."""
    import json

    data = {
        ref: [{"ref": sim_ref, "score": score} for sim_ref, score in pairs]
        for ref, pairs in results
    }
    path = output_dir / "verse-similarity.json"
    with open(path, "w") as f:
        json.dump(data, f, ensure_ascii=False)
        f.write("\n")


def build_vector_index(ctx: BuildContext, output_dir: Path, db_path: Path) -> Path:
    """Build HNSW index and write vector_meta table.

    Returns the path to the .usearch index file.
    """
    console.print("  Building vector index...")

    docs = _collect_documents(ctx)
    console.print(f"    Collected {len(docs)} documents")

    console.print(f"    Loading model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)

    texts = [text for _, _, text in docs]
    console.print(f"    Encoding {len(texts)} texts...")
    embeddings = model.encode(
        texts,
        batch_size=256,
        show_progress_bar=True,
        normalize_embeddings=True,
    )
    index = Index(ndim=NDIM, metric=MetricKind.Cos, dtype=ScalarKind.I8)
    keys = np.arange(len(docs), dtype=np.uint64)
    index.add(keys, embeddings)

    index_path = output_dir / "gnosis.usearch"
    index.save(str(index_path))
    size_mb = index_path.stat().st_size / 1024 / 1024
    console.print(f"    Index: {size_mb:.1f} MB, {len(docs)} vectors")

    _write_vector_meta(db_path, docs)
    console.print(f"    Wrote vector_meta table ({len(docs)} rows)")

    console.print("  Computing verse similarity...")
    similarity = compute_verse_similarity(embeddings, docs)
    _write_verse_similarity_sqlite(db_path, similarity)
    console.print(f"    Wrote verse_similarity table ({len(similarity)} verses)")
    _write_verse_similarity_json(output_dir, similarity)
    console.print("    Wrote verse-similarity.json")

    return index_path
