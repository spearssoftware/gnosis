# gnosis — repo conventions

A data build pipeline. Input: upstream bible/reference sources under `sources/`. Output: a set of JSON/SQLite/usearch artifacts in `output/` that ship as a GitHub Release (consumed by BibleMarker and gnosis-api).

## Commands

- `uv run gnosis build` — run the full pipeline (writes `output/`).
- `uv run gnosis validate` — run validation only.
- `uv run pytest` — 160 tests, should run <2s. Run after every change.

`output/` is gitignored. Rebuild locally to check effects.

## Source precedence

**Theographic is the authoritative upstream.** `sources/theographic/{people,places,events,verses}.json` is the anchor. Our job is to faithfully propagate it and fill documented gaps — not to overrule it with our own opinions.

When Theographic is internally inconsistent (e.g. events dated X, verses dated Y), prefer the value Theographic expressed with more specificity (e.g. full `startDate` strings over bare `yearNum` integers), and reconcile derived outputs to match — don't overwrite the more-specific field to match the less-specific one.

Example: Passion Week events carry explicit `0030-03-31` dates; verses just have `yearNum: 33`. Chapter timeline should prefer event `start_year` over verse `yearNum` when both are available. (See `_build_chapter_timeline` in `src/gnosis/build.py`.)

## Supplements

Two supplement files live at `sources/supplements/`:

- `people-dates.json` — curated birth/death years. **Only fills gaps.** Does not override Theographic values unless an entry sets `"override": true`. Use override sparingly; document the reason in `NOTES.md`.
- `events-dates.json` — curated event start/end years. **Always overrides** Theographic (corrects wrong dates, spreads pile-ups).

Every supplement entry carries a `confidence` tag: `exact` | `scholarly_consensus` | `tradition` | `estimate`. Optional `source` field is a human-readable reference (e.g. `"genesis-5-17"`, `"acts-12-2"`). Downstream consumers render uncertain confidences with dashed borders / `~` prefixes.

Any change to supplement values must also update `sources/supplements/NOTES.md` with the rationale.

## Build context

`BuildContext` (in `build.py`) collects parsed entities from all sources and is threaded through output writers. When adding a new data source:

1. Add a parser in `src/gnosis/parsers/`.
2. Extend `BuildContext` with the new field.
3. Call the parser from `_parse_all` and wire it into the output.
4. Emit to both JSON (via `_write_output`) and SQLite (via `sqlite_writer.py`) when relevant.

## Types

Dataclasses live in `src/gnosis/types/`. Add fields there first; they flow to both JSON and SQLite automatically when the writers are updated.

## Releases

Release workflow triggers on tag push (`v*`). Tagging `v0.9.x` from `main` builds the full pipeline and uploads `output/*.json`, both `.db` files, `gnosis.usearch`, `verse-similarity.json`, and a tarball.

`pyproject.toml` version is not synced to tags — the tag is the source of truth for released versions.

## Known upstream quirks

- **Person/place name conflation**: Theographic tags verses to people by name-matching, which conflates patriarchs with tribes/regions/gates (Benjamin, Judah, Gad, Dan, etc.). No fix yet — candidate signal is person lifespan vs. chapter timeframe.
- **`herod-dies`** refers to Herod Agrippa I (Acts 12:23), not Herod the Great.
- **Verse `yearNum` is less reliable** than event `startDate` where both exist.
