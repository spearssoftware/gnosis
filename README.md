# Gnosis

A curated biblical knowledge graph merging 11 open-licensed upstream sources into a clean, versioned dataset. See [SOURCES.md](SOURCES.md) for full attribution.

## Output

Published via GitHub Releases as JSON files and a SQLite database:

- **people.json** — Biblical figures with relations, dates, verse refs
- **places.json** — Locations with coordinates, classifications, verse refs
- **events.json** — Biblical events with participants, dates, verse refs
- **people-groups.json** — Tribes and ethnic groups
- **verse-index.json** — Reverse index: verse → entities mentioned
- **cross-references.json** — ~340k verse-to-verse cross-references with vote scores
- **strongs.json** — Strong's Hebrew and Greek concordance entries
- **dictionary.json** — Merged entries from Smith's, Hastings', Schaff's, and Hitchcock's dictionaries
- **lexicon.json** — Brown-Driver-Briggs Hebrew lexicon
- **greek-lexicon.json** — Dodson Greek-English lexicon
- **topics.json** — Nave's and Torrey's topical indexes with verse references
- **hebrew-words.json** — Hebrew Bible words with morphology and Strong's numbers
- **greek-words.json** — Greek NT words with morphology, lemmas, and Louw-Nida domains
- **verse-similarity.json** — Pre-computed verse-to-verse semantic similarity index
- **gnosis.db** — SQLite database with all entities, junction tables, and indexes
- **gnosis-lite.db** — Lightweight SQLite build (no word-level morphology tables)
- **gnosis.usearch** — HNSW vector index for semantic verse search

JSON files are dicts keyed by slug ID (e.g. `"abraham"`, `"jerusalem"`). Each entity includes a deterministic UUID v5. The SQLite database mirrors the same data with integer PKs, foreign keys, and junction tables for many-to-many relationships.

## Usage

```bash
uv sync
uv run gnosis build       # full pipeline → output/
uv run gnosis validate    # validation only
uv run pytest             # tests
```

## Schema

See type definitions in `src/gnosis/types/` for full field documentation.

## License

CC-BY-SA 4.0 — see [LICENSE](LICENSE) and [SOURCES.md](SOURCES.md) for upstream attribution.
