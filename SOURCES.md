# Data Sources

All source datasets used by OpenWahlkreisMap, with provenance and licensing.

## Bundestag Constituency Boundaries

| Field | Value |
|-------|-------|
| **Publisher** | Bundeswahlleiterin |
| **URL** | https://www.bundeswahlleiterin.de/bundestagswahlen/2025/wahlkreiseinteilung/downloads.html |
| **Files** | `btw25_wahlkreisnummern_namen.csv`, `btw25_wahlkreise_gemeinden.csv`, Shapefiles |
| **License** | Public domain (§5 UrhG — Amtliche Werke) |
| **Attribution** | Not legally required, but credited as good practice |
| **Election** | BTW 2025 (valid 2025–2029) |
| **Constituencies** | 299 |

## PLZ Boundary Polygons

| Field | Value |
|-------|-------|
| **Publisher** | BKG (Bundesamt für Kartographie und Geodäsie) |
| **URL** | https://gdz.bkg.bund.de/index.php/default/postleitzahlgebiete-deutschland-plz.html |
| **Documentation** | https://sg.geodatenzentrum.de/web_public/gdz/dokumentation/deu/plz.pdf |
| **License** | dl-de/by-2-0 (Datenlizenz Deutschland – Namensnennung – Version 2.0) |
| **Attribution** | © GeoBasis-DE / BKG (year of data) |
| **Contains** | PLZ polygons with AGS (Amtlicher Gemeindeschlüssel) mapping |

## Gemeindeverzeichnis (supplementary)

| Field | Value |
|-------|-------|
| **Publisher** | Destatis (Statistisches Bundesamt) |
| **URL** | https://www.destatis.de/DE/Themen/Laender-Regionen/Regionales/Gemeindeverzeichnis |
| **License** | dl-de/by-2-0 |
| **Attribution** | © Statistisches Bundesamt (Destatis) |
| **Limitation** | Only one PLZ per Gemeinde (Verwaltungssitz) |

## PLZ GeoJSON (open alternative)

| Field | Value |
|-------|-------|
| **Publisher** | yetzt/postleitzahlen (GitHub community) |
| **URL** | https://github.com/yetzt/postleitzahlen |
| **License** | ODbl |
| **Contains** | GeoJSON/TopoJSON of all PLZ areas |

## Abgeordnetenwatch API (constituency metadata)

| Field | Value |
|-------|-------|
| **Publisher** | abgeordnetenwatch.de |
| **URL** | https://www.abgeordnetenwatch.de/api/v2 |
| **License** | CC0 1.0 |
| **Contains** | Constituency names, numbers, parliament period IDs for all 17 German parliaments |
| **Limitation** | No PLZ lookup, no geodata |

## VG250 Gemeindegrenzen (municipality boundaries)

| Field | Value |
|-------|-------|
| **Publisher** | BKG (Bundesamt für Kartographie und Geodäsie) |
| **URL** | https://daten.gdz.bkg.bund.de/produkte/vg/vg250_ebenen_0101/ |
| **License** | dl-de/by-2-0 |
| **Attribution** | © GeoBasis-DE / BKG (2025) |
| **Contains** | VG250_GEM — Gemeinde boundary polygons with AGS codes |
| **Used for** | PLZ→AGS spatial join (municipality_join method for Landtag states) |

## Landtag Constituency Data (per state)

Each state source is fetched by `scripts/download_landtag.py` from its config in `configs/landtag/`. States that publish official Wahlkreis geometry use it directly. Sachsen and Brandenburg publish none, so they use the official municipality→Wahlkreis table; Bremen and Saarland map whole municipalities or Kreise from the config.

The geometry publishers state no open license but require the copyright notice quoted below. Only derived PLZ→Wahlkreis assignments are published here; the geometries themselves are not redistributed.

| State | Source and attribution | URL | Format | WK |
|-------|------------------------|-----|--------|-----|
| Baden-Württemberg | Statistisches Landesamt Baden-Württemberg — Wahlkreiskarte Landtagswahl 2026 (© Statistisches Landesamt Baden-Württemberg, Fellbach 2025; Kartengrundlage: LGL, Städte Freiburg, Karlsruhe, Mannheim, Stuttgart) | `https://www.statistik-bw.de/fileadmin/user_upload/medien/bilder/Karten_und_Geometrien_der_Wahlkreise/LTWahlkreise2026-BW_SHP.zip` | shapefile | 70 |
| Bayern | Bayerisches Landesamt für Statistik — Stimmkreiszuschnitte Landtagswahl 2023 (Datenquelle: Bayerisches Landesamt für Statistik) | `https://www.statistik.bayern.de/mam/wahlen/landtagswahlen/ergebnisse/shapefile_stimmkreiseltw_bayern_2023.zip` | shapefile | 91 |
| Berlin | Amt für Statistik Berlin-Brandenburg — Wahlkreise AGH 2026 via GDI Berlin WFS (CC BY 3.0 DE) | `https://gdi.berlin.de/services/wfs/wahlgebiete_agh2026?service=WFS&version=2.0.0&request=GetFeature&typeNames=wahlgebiete_agh2026:agh2026_awk&outputFormat=application/json&srsName=EPSG:25833` | geojson | 78 |
| Brandenburg | Amt für Statistik Berlin-Brandenburg (public domain) | `https://download.statistik-berlin-brandenburg.de/797f02a07ccf0c80/60948eac20a4/SB_B07-02-04_2024j05_BB.xlsx` | excel | 44 |
| Bremen | Landeswahlleiter Bremen (public domain) | — | config mapping + VG250 | 2 |
| Hamburg | LGV Hamburg — Geodienste WFS (dl-de/by-2-0) | `https://geodienste.hamburg.de/HH_WFS_Wahlen?SERVICE=WFS&VERSION=1.1.0&REQUEST=GetFeature&TYPENAME=de.hh.up:buergerschaftswahlkreise&OUTPUTFORMAT=text/xml%3B%20subtype%3Dgml/3.1.1&SRSNAME=EPSG:25832` | gml | 17 |
| Hessen | Hessisches Statistisches Landesamt — Landtagswahlkreise 2023 (© Hessisches Statistisches Landesamt, Wiesbaden 2022; Kartengrundlage © GeoBasis-DE / BKG 2021) | `https://statistik.hessen.de/sites/statistik.hessen.de/files/2024-08/hsl_landtagswahlkreise_2023.zip` | shapefile | 55 |
| Mecklenburg-Vorpommern | LAIV Mecklenburg-Vorpommern / Landeswahlleiterin (dl-de/by-2-0) | `https://www.laiv-mv.de/static/LAIV/Geoinformation/Dateien/Karten/LTwahl_Wahlkreise.zip` | shapefile | 36 |
| Niedersachsen | Landesamt für Statistik Niedersachsen — Wahlkreiskarte für die Wahl zum 19. Niedersächsischen Landtag (© Landesamt für Statistik Niedersachsen, Hannover 2022; Quelle: Auszug aus den Geodaten des LGLN, © 2022) | `https://www.statistik.niedersachsen.de/download/182342` | shapefile | 87 |
| Nordrhein-Westfalen | IT.NRW — Wahlkreiseinteilung zur Landtagswahl 2022 (© Ministerium des Innern des Landes Nordrhein-Westfalen, IT.NRW, Düsseldorf) | `https://www.wahlergebnisse.nrw/landtagswahlen/2022/wahlkreiskarten/16_LW2022_NRW_Wahlkreise.zip` | shapefile | 128 |
| Rheinland-Pfalz | Statistisches Landesamt Rheinland-Pfalz — Geodaten Landtagswahl 2026 (Quelle: Statistisches Landesamt Rheinland-Pfalz) | `https://www.wahlen.rlp.de/fileadmin/wahlen.rlp.de/dokumente-wahlen/ltw/Shapefiles/Geodaten_LW2026_RP.zip` | shapefile | 52 |
| Saarland | Landeswahlleiter Saarland (public domain) | — | config mapping + VG250 | 3 |
| Sachsen | Landeswahlleiter Sachsen / Statistisches Landesamt (public domain) | `https://wahlen.sachsen.de/download/Landtag/statistik-sachsen_LW24_endgErgebniss.xlsx` | excel | 60 |
| Sachsen-Anhalt | Statistisches Landesamt Sachsen-Anhalt — Wahlkreiskarte für die Wahl zum 9. Landtag (© GeoBasis-DE / LVermGeo ST) | `https://statistik.sachsen-anhalt.de/fileadmin/Bibliothek/Landesaemter/StaLa/startseite/Themen/Wahlen/Wahlkreise/Wahlkreise_LTW_2026.zip` | shapefile | 41 |
| Schleswig-Holstein | Statistikamt Nord — Landtagswahlkreise Schleswig-Holstein 2022 (© Statistisches Amt für Hamburg und Schleswig-Holstein 2022; © GeoBasis-DE/LVermGeo SH/BKG 2022) | `https://www.statistik-nord.de/fileadmin/Dokumente/Wahlen/Schleswig-Holstein/Landtagswahlen/2022/Vor_der_Wahl/Landtagswahlkreise.zip` | shapefile | 35 |
| Thüringen | Thüringer Landesamt für Statistik — Wahlkreiseinteilung Landtagswahl 2024 (© GDI-Th / Thüringer Landesamt für Statistik) | `https://wahlen.thueringen.de/landtagswahlen/informationen/vektor/2024/16TH_L24_Wahlkreiseinteilung.zip` | gpkg | 44 |
