# OpenWahlkreisMap

Open-source mapping of German 5-digit postal codes (PLZ) to electoral constituencies for **all 17 German parliaments** — the Bundestag and all 16 Landtage.

Published as static JSON, CSV, npm package, and a free public API via GitHub Pages.

## Quick Start

### API (no setup needed)

```bash
curl https://maximilion-ai.github.io/OpenWahlkreisMap/v1/10117.json
```

```json
{
  "plz": "10117",
  "bundestag": {
    "wahlkreise": [{ "nr": 74, "name": "Berlin-Mitte", "overlap": 1.0 }],
    "primary": 74,
    "period_id": 161
  },
  "landtage": [{
    "state": "berlin",
    "wahlkreise": [
      { "nr": 102, "name": "Alexanderplatz, Engelbecken", "overlap": 0.520094 },
      { "nr": 101, "name": "Charité, Oranienburger Tor", "overlap": 0.479906 }
    ],
    "primary": 102,
    "period_id": 176
  }]
}
```

### npm package

```bash
npm install open-wahlkreis-map
```

```typescript
import {
  getBundestagWahlkreis,
  getConstituencies,
  getLandtagWahlkreise,
} from 'open-wahlkreis-map';

const result = getConstituencies('10117');
// { plz: '10117', bundestag: { primary: 74, ... }, landtage: [{ state: 'berlin', ... }] }

const bt = getBundestagWahlkreis('10117');
// { wahlkreise: [{ nr: 74, name: 'Berlin-Mitte', overlap: 1.0 }], primary: 74, period_id: 161 }

const berlin = getLandtagWahlkreise('10117', 'berlin');
// [{ state: 'berlin', wahlkreise: [...], primary: 102, period_id: 176 }]
```

The npm package is intended for backend and server-side use. It is an in-memory lookup table and bundles the full dataset for fast local reads, currently about 3 MB of JSON before transport compression. Importing it directly in a browser app will add that dataset to the frontend bundle; if bundle size matters, prefer the static API or consume generated JSON directly.

## Important Caveat

Postal codes are **not** electoral districts.

A single PLZ can overlap multiple Bundestag or Landtag constituencies, especially near district borders and in large cities. OpenWahlkreisMap therefore returns:
- a `primary` constituency with the largest overlap
- the full list of overlapping constituencies with overlap shares

This makes the dataset suitable for postcode-level inference and routing. For address-level certainty, a full geocoded address is more precise than a PLZ-only lookup.

## The Problem

There is **no official dataset** that maps PLZ → Wahlkreis. This has been confirmed through multiple FragDenStaat freedom-of-information requests — the Bundeswahlleiterin explicitly states they only map at the Gemeinde (municipality) level.

PLZ boundaries (managed by Deutsche Post) and Wahlkreis boundaries (managed by the Bundeswahlleiterin) **do not align**:
- One PLZ can span multiple Wahlkreise
- One Wahlkreis can contain parts of many PLZ areas
- PLZ boundaries follow postal logistics, Wahlkreis boundaries follow population counts

Every civic tech project that needs this mapping (abgeordnetenwatch.de, wahl-o-mat tools, lobbying platforms, etc.) builds their own internal lookup — usually closed-source and not shared.

## Goal

Produce an open, machine-readable, verified mapping:

```
PLZ (5-digit) → Wahlkreis number(s) + confidence
```

Published as:
- **JSON** (`plz-wahlkreis.json`) — primary format
- **CSV** (`plz-wahlkreis.csv`) — for spreadsheet users
- **TypeScript** (`plz-wahlkreis.ts`) — for JS/TS projects
- **npm package** — `open-wahlkreis-map` for easy consumption

## Data Sources

[SOURCES.md](SOURCES.md) lists every source with its URL, license, and attribution.

## Output Format

### JSON (primary)

```json
{
  "meta": {
    "election": "BTW 2025",
    "constituencies": 299,
    "plz_count": 8168,
    "generated": "2026-03-24",
    "sources": [
      "Bundeswahlleiterin Wahlkreiseinteilung 2025",
      "BKG Postleitzahlengebiete 2025"
    ]
  },
  "data": {
    "87435": {
      "wahlkreise": [
        { "nr": 256, "name": "Oberallgäu", "overlap": 0.95 },
        { "nr": 255, "name": "Memmingen – Unterallgäu", "overlap": 0.05 }
      ],
      "primary": 256
    }
  }
}
```

### CSV

```csv
plz,wahlkreis_nr,wahlkreis_name,overlap,is_primary
87435,256,Oberallgäu,0.95,true
87435,255,Memmingen – Unterallgäu,0.05,false
```

### TypeScript

```typescript
export function getConstituencies(plz: string): PlzResult | null
export function getBundestagWahlkreis(plz: string): BundestagEntry | null
export function getLandtagWahlkreise(plz: string, state?: string): LandtagEntry[]
```

## Tech Stack

- **Python 3.11+** for data processing
- **geopandas** + **shapely** for spatial operations
- **pandas** for data joins
- **pytest** for unit and fixture-based integration tests

## Verification

- Total Wahlkreise in output must equal 299
- Every Wahlkreis must appear at least once
- Every valid 5-digit PLZ must map to at least one Wahlkreis
- Primary Wahlkreis must have the largest overlap for each PLZ
- Spot-check: `tests/expected_samples.json` and `tests/expected_landtag_samples.json`

## Update Cycle

The mapping only changes when:
- Wahlkreis boundaries are redrawn (every ~4 years, before each Bundestagswahl)
- PLZ boundaries change (Deutsche Post updates these occasionally)

For BTW 2025, this mapping is valid 2025–2029.

## Coverage

### Bundestag

299 Wahlkreise. The exact bundled PLZ count is stored in [`data/bundestag/plz-wahlkreis.json`](data/bundestag/plz-wahlkreis.json) under `meta.plz_count`.

### Landtage (all 16 states)

| State | Parliament | WK | PLZ | Method | Election | period_id |
|-------|-----------|-----|-----|--------|----------|-----------|
| Baden-Württemberg | Landtag | 70 | 1,199 | spatial | Baden-Württemberg 2026 | 165 |
| Bayern | Landtag | 91 | 2,063 | spatial | Bayern 2023 | 149 |
| Berlin | Abgeordnetenhaus | 78 | 190 | spatial | Berlin 2026 | 176 |
| Brandenburg | Landtag | 44 | 228 | spatial | Brandenburg 2024 | 158 |
| Bremen | Bürgerschaft | 2 | 40 | municipality_join | Bremen 2023 | 146 |
| Hamburg | Bürgerschaft | 17 | 100 | spatial | Hamburg 2025 | 162 |
| Hessen | Landtag | 55 | 555 | spatial | Hessen 2023 | 150 |
| Mecklenburg-Vorpommern | Landtag | 36 | 193 | spatial | Mecklenburg-Vorpommern 2026 | 177 |
| Niedersachsen | Landtag | 87 | 802 | spatial | Niedersachsen 2022 | 143 |
| Nordrhein-Westfalen | Landtag | 128 | 865 | spatial | NRW 2022 | 139 |
| Rheinland-Pfalz | Landtag | 52 | 661 | spatial | Rheinland-Pfalz 2026 | 166 |
| Saarland | Landtag | 3 | 71 | municipality_join | Saarland 2022 | 137 |
| Sachsen | Landtag | 60 | 383 | spatial | Sachsen 2024 | 157 |
| Sachsen-Anhalt | Landtag | 41 | 202 | spatial | Sachsen-Anhalt 2026 | 178 |
| Schleswig-Holstein | Landtag | 35 | 456 | spatial | Schleswig-Holstein 2022 | 138 |
| Thüringen | Landtag | 44 | 216 | spatial | Thüringen 2024 | 156 |
| **Total** | | **843** | **8,224** | | | |

Processing methods:
- **spatial**: intersection of PLZ polygons with the state's official Wahlkreis geometry. Used wherever the state has one, including Brandenburg and Sachsen, which provide it on request.
- **municipality_join**: PLZ→AGS→Wahlkreis via VG250 municipality boundaries. Used for Bremen and Saarland, whose Wahlkreise are whole municipalities or Kreise.

Both methods drop overlaps below 1% of a PLZ's area as boundary misalignment. A PLZ whose area inside a state stays below 1% is left out of that state.

`period_id` is the abgeordnetenwatch legislature period whose members were elected in these Wahlkreise.

`make download-landtag` fetches every state source from config. Berlin's WFS publishes only Wahlkreis codes; `configs/landtag/berlin-wahlkreisnamen.csv` supplies the names from the official [Wahlkreiskarten 2026](https://www.statistik-berlin-brandenburg.de/wahlkreiskarten-2026/).

## Testing

Use two layers:

- `make test` runs the fast `pytest` suite for parser helpers, checksum helpers, and small fixture-based processing tests.
- `make verify` runs `scripts/verify.py`, which is the release gate for final published outputs and built artifacts.

## Related Projects

| Project | What it does | PLZ mapping? |
|---------|-------------|--------------|
| [abgeordnetenwatch.de](https://www.abgeordnetenwatch.de) | Politician transparency platform | Internal, closed-source |
| [bundestag.de Wahlkreissuche](https://www.bundestag.de/abgeordnete/wahlkreissuche) | Official constituency finder | Web UI only, no API |
| [okfde/wahldaten](https://github.com/okfde/wahldaten) | Open election data | Wahlkreis geometries, no PLZ |
| [yetzt/postleitzahlen](https://github.com/yetzt/postleitzahlen) | PLZ GeoJSON boundaries | No Wahlkreis linkage |
| [WZBSocialScienceCenter/plz_geocoord](https://github.com/WZBSocialScienceCenter/plz_geocoord) | PLZ centroids | No Wahlkreis linkage |

## Legal / Licensing

- Bundeswahlleiterin data: public domain (Amtliche Werke, §5 UrhG)
- BKG data: dl-de/by-2-0 (attribution required)
- Destatis data: dl-de/by-2-0
- Output dataset: to be published under CC0 or MIT

## Future

- EU AI Act (Art. 50, Aug 2026): if this data is used to power AI-assisted civic participation tools, the generated content may need labeling
- Wirtschafts-Identifikationsnummer (W-IdNr., Dec 2026): not relevant to this project but worth noting for downstream users
- Landtag coverage complete (all 16 states, 843 Wahlkreise)
- Potential expansion: EU Parliament constituencies
