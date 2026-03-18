# Gnosis

A curated biblical knowledge graph merging [Theographic Bible Metadata](https://github.com/robertrouse/theographic-bible-metadata) and [OpenBible Geocoding Data](https://github.com/openbibleinfo/Bible-Geocoding-Data) into a clean, versioned dataset.

## Output

Published via GitHub Releases as JSON files and a SQLite database:

- **people.json** — Biblical figures with relations, dates, verse refs
- **places.json** — Locations with coordinates, classifications, verse refs
- **events.json** — Biblical events with participants, dates, verse refs
- **people-groups.json** — Tribes and ethnic groups
- **verse-index.json** — Reverse index: verse → entities mentioned
- **gnosis.db** — SQLite database with all entities, junction tables, and indexes

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
