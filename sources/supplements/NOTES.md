# Supplement Assumptions

Context and reasoning for curated values in `people-dates.json` and `events-dates.json`. Update this file whenever supplement values are added or revised.

All years are astronomical integers (year `0` = 1 BC; year `-3` = 4 BC).

## Confidence levels

Every curated entry carries a `confidence` tag:

| Value | Meaning |
|---|---|
| `exact` | Value is derived from an explicit biblical lifespan or date (e.g. Gen 5 ages, Exodus 6:16). Precise within the source. |
| `scholarly_consensus` | Well-anchored by external history (e.g. Herod the Great's 4 BC death per Josephus, Nebuchadnezzar's regnal years). |
| `tradition` | Religious tradition, not scripture (e.g. apostle martyrdom dates, Coptic stay-in-Egypt duration). |
| `estimate` | Our best guess filling a gap, typically using surrounding genealogy or typical patriarchal lifespans. |

An optional `source` field provides a human-readable reference (e.g. `"genesis-5-17"`, `"acts-12-2"`, `"herod-died-4bc"`).

Consumers should treat `tradition` and `estimate` as uncertain — render dashed borders, fuzzy glow, or a prefix like `~` on timelines.

---

## People (`people-dates.json`)

### Pre-flood patriarchs (Genesis 5)
Ussher chronology, anchored to Creation = 4004 BC.
- `mahalaleel`: -3609 → -2714 (895 yrs, Gen 5:17) — **exact**
- All other Gen 5 patriarchs were already in Theographic.

### Post-flood patriarchs (Genesis 11)
- `shelah`: -2311 → -1878 (433 yrs, Gen 11:15) — **exact**
- `cainan-son-of-arphaxad`: -2311 → -1880 — tagged **tradition** because this name only appears in the LXX/Luke genealogy, not in the Masoretic Gen 11 text.

### Jacob's family
- `jacob` (separate slug from `israel`, which already had dates): -1836 → -1689 (Gen 47:28, 147 yrs) — **exact**
- `sarah`: -1986 → -1859 (127 yrs, Gen 23:1) — **exact**
- `esau`, `hagar`, `leah`: **estimates** from surrounding genealogy.

### 12 Tribal patriarchs (Jacob's sons)
Birth years from Theographic (Jacob's 14 yrs in Paddan-aram). Death years were missing, which caused timeline bars to stretch via the `latest_year_mentioned` fallback (tribe names reappear in Numbers, Ezekiel, Rev 7, etc.).

Assumption: each lived ~130 yrs (typical patriarchal lifespan) — **estimate** — except:
- `levi-son-of-israel`: 137 yrs (Exodus 6:16) — **exact**
- `simeon-son-of-israel`: 120 yrs (rabbinic tradition, less certain) — tagged **estimate**
- `benjamin-son-of-israel`: 120 yrs (youngest; tradition) — **estimate**

### Joseph's sons
`ephraim`, `manasseh-son-of-joseph`: estimated 120 yrs. No scripture gives ages. **estimate**.

### Post-flood lineage (Ham, Japheth)
Born ~100 yrs before flood (-2446), died ~500 yrs later. Noah's 3 sons were born within ~5 yrs of each other (Gen 5:32 + 7:6). **estimate**.

### Judges
Dates anchored to 1 Kings 6:1 (Exodus 480 yrs before Solomon's temple → Exodus ~1446 BC) + Judges chronology. All **estimate**.
- `gideon`: 40-yr rule (Judges 8:28), placed ~-1249 → -1169.
- `samson`: 20-yr rule (Judges 15:20).
- `deborah-judge`, `barak`: contemporaries, placed ~-1240.

### Original 24 curated figures (apostles, prophets, kings)
Added in PR #22. Mostly **tradition** (apostle martyrdoms) with a few **scholarly_consensus** (kings anchored to regnal-year chronology: Nebuchadnezzar, Jeroboam, Ahab, John the Baptist, Judas, James son of Zebedee via Acts 12:2).

Worth revisiting individually if any become contentious.

---

## Events (`events-dates.json`)

### Infancy of Jesus
Theographic lumps all six infancy events at year `-3` (4 BC) with 1-day duration, which renders as a pile-up on timelines (flee and return appear in the same year with no visible duration).

Scholarly anchors:
- Jesus's birth: ~5 BC (-4), with a range of 6-4 BC. Herod's 4 BC death caps the late end.
- Herod the Great's death: **spring 4 BC** (Josephus, eclipse-anchored) — **scholarly_consensus**.
- Wise Men visit: Matthew calls Jesus "young child" (παιδίον); Herod's decree targets children ≤ 2 yrs. So Magi could be months to ~2 yrs post-birth.
- Stay in Egypt: undefined in scripture. Scholarly range "months to ~2 years"; Coptic tradition is 3y 6m 10d or 3y 11m.

Our spread (~1-2 yr Egypt stay at year granularity):

| Event | Start | End | Confidence |
|---|---|---|---|
| Wise Men Visit Herod | -4 (5 BC) | — | estimate |
| Wise Men Visit Jesus | -4 | — | estimate |
| Herod slays male children | -4 | — | estimate |
| Flee to Egypt | -4 | -3 | estimate (~1-2 yr span) |
| Return from Egypt | -3 (4 BC) | — | scholarly_consensus (Herod's death) |
| Return to Nazareth | -3 | — | estimate |

**Note on "duration"**: at year resolution, a start of `-4` and end of `-3` naturally represents anywhere from ~1 to ~2 years depending on specific months. Don't interpret as "exactly 1 year."

### Refinement candidates
- Adopt Coptic ~3.5-yr Egypt stay → shift flee to -6, birth to ~7 BC (still within scholarly range, requires Jupiter-Saturn conjunction argument for the star). Would tag `confidence: "tradition"`.
- Sub-year (month) granularity if we ever need it. Would require schema changes (`start_month`, etc.) — not worth until we have multiple entities that need it.

### Note: Theographic's "Herod dies" event
The `herod-dies` event is at 45 AD — this is **Herod Agrippa I** (Acts 12:23, died 44 AD), not Herod the Great. There is no explicit "Herod the Great dies" event in the upstream data.
