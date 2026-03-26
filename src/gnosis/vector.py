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

    index = Index(ndim=NDIM, metric=MetricKind.Cos, dtype=ScalarKind.F32)
    keys = np.arange(len(docs), dtype=np.uint64)
    index.add(keys, embeddings)

    index_path = output_dir / "gnosis.usearch"
    index.save(str(index_path))
    size_mb = index_path.stat().st_size / 1024 / 1024
    console.print(f"    Index: {size_mb:.1f} MB, {len(docs)} vectors")

    _write_vector_meta(db_path, docs)
    console.print(f"    Wrote vector_meta table ({len(docs)} rows)")

    return index_path
