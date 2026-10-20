# Data dictionary and provenance

**Source checked:** 20–21 October 2026. **Captured sample:** eight local snapshots from 20 October 2026 UTC: a six-snapshot baseline plus two replacement-pilot captures after a process interruption. The source is the operator-hosted Vélib Métropole GBFS endpoint listed by [transport.data.gouv.fr](https://transport.data.gouv.fr/datasets/velib-velos-et-bornes-disponibilite-temps-reel).

## Source feeds

All requests are unauthenticated HTTPS `GET` requests returning UTF-8 JSON. The collector discovers the station feed URLs from `gbfs.json` on every capture rather than hard-coding the status URL.

| Feed | Current URL observed | Purpose | Captured locally as |
|---|---|---|---|
| GBFS discovery | `https://velib-metropole-opendata.smovengo.cloud/opendata/Velib_Metropole/gbfs.json` | Advertises URLs for the system's feeds | `gbfs.json` in every capture |
| Station information | `https://velib-metropole-opendata.smovengo.cloud/opendata/Velib_Metropole/station_information.json` | Station identity, location, capacity and descriptive metadata | Initially per capture; now a dated reference snapshot, refreshed at most daily |
| Station status | `https://velib-metropole-opendata.smovengo.cloud/opendata/Velib_Metropole/station_status.json` | Current available bikes, docks, operating flags and station report time | `station_status.json` in every capture |

The public listing states that access needs no API key, labels the feed GBFS 1.0, and says the data is updated each minute. The six captured discovery responses advertised `ttl=3600`; their discovery and status payloads did not contain a feed-level `last_updated` or `version`. These are different pieces of evidence and are retained separately. The provider's discovery data exposed `gbfs`, `system_information`, `station_information`, and `station_status` feed names.

## Fields observed in the captured payloads

Types below describe the sampled JSON, not a guarantee that a future response cannot change. The source is labelled GBFS 1.0 by the portal, so its exact deployed schema must be checked against the raw feed rather than silently upgraded to current GBFS semantics.

### `station_information.data.stations[]`

| Field | Sampled JSON type | Use and handling |
|---|---|---|
| `station_id` | integer | Stable join key in these captures. Converted to text for matching and output; original JSON is preserved. |
| `stationCode` | string | Operator-facing station code; retain as a label, not as the join key. |
| `name` | string | Station label. |
| `lat`, `lon` | number | WGS84 latitude and longitude; validated against legal coordinate ranges before spatial analysis. |
| `capacity` | non-negative integer | Station capacity field. Do not infer usable docks from this field alone. |
| `rental_methods` | array | Source-provided rental-method metadata. |
| `station_opening_hours` | null or source-defined value | Preserve raw value; its interpretation depends on the feed schema. |

### `station_status.data.stations[]`

| Field | Sampled JSON type | Use and handling |
|---|---|---|
| `station_id` | integer | Join key to station information. Every sampled status ID joined to exactly one information ID. |
| `num_bikes_available` | non-negative integer | Sampled total count. Retained as reported. |
| `num_bikes_available_types` | array of one-key objects | Sampled breakdown, e.g. `mechanical` and `ebike`. The audit accepts this representation and a future object representation; it checks that the type counts sum to `num_bikes_available`. |
| `num_docks_available` | non-negative integer | Sampled available return-dock count. Retained separately from bike inventory. |
| `numBikesAvailable`, `numDocksAvailable` | integer aliases | Camel-case duplicates appeared alongside snake-case fields. They agreed in every sampled row; analysis uses the snake-case fields and reports alias mismatches. |
| `is_installed`, `is_renting`, `is_returning` | integer flags, 0 or 1 in sample | Preserve the source values. A false flag is not the same as a zero bike/dock count. |
| `last_reported` | integer Unix epoch seconds | Converted to UTC and compared with the status request's retrieval time. It represents the station's reported time; it is not assumed to be the time this feed was published or the time inventory changed. |
| `stationCode` | string | Redundant operator label; preserve for display. |
| `station_opening_hours` | null or source-defined value | Preserve raw value; not used in the initial availability metrics. |

The capture manifest adds local `capture_started_at_utc` and request `retrieved_at_utc`, response HTTP status, SHA-256 of the exact response body, content type and selected cache headers (`Cache-Control`, `Age`, `ETag`), counts, TTL, and the path/hash/time of the station-information reference. Retrieval time and `last_reported` are separate clocks.

## Derived station-time table

`python -m velib_lab.audit` writes ignored local outputs under `data/processed/`:

- `station_snapshots.csv`: one row per status station per capture, joined to that capture's station-information snapshot. It includes capture and retrieval times, station identity/location/capacity, mechanical/e-bike/other breakdown, total bikes, available docks, operating flags, report epoch and UTC, and report age in seconds.
- `capture_summary.csv`: one row per capture with response hashes and bytes, record and join counts, totals and zero-count stations, field-quality counters, report-age quantiles, and comparisons with the previous capture, including newly-zero, recovered and persistently-zero bike/dock states.
- `audit_report.json`: machine-readable run manifest, field-name unions, and global integrity results.

For report-age quantiles the audit uses the nearest-rank method: sort valid ages and select rank `ceil(p*n)` for percentile `p`. Future or invalid timestamps are counted separately. Count errors, ID mismatches, alias disagreements and type-total discrepancies are reported; the audit does not fill missing values with zero.

## Provenance, storage and reuse

Raw response bodies remain local under `data/raw/`; station information remains local under `data/reference/`; generated CSV and JSON remain local under `data/processed/`. These directories are Git-ignored. The public repository contains code, methodology, field definitions, source links and aggregate audit results only, not the raw feed archive or station-level derived CSV.

The dataset listing points to the [Open Database License (ODbL)](https://doc.transport.data.gouv.fr/le-point-d-acces-national/cadre-juridique/conditions-dutilisation-des-donnees/licence-odbl). Attribute the Vélib Métropole / Smovengo source. Before distributing a derived database or a substantial transformed dataset, review the license's attribution and share-alike requirements. The listing also explains its [data-quality indicators](https://transport.data.gouv.fr/datasets/velib-velos-et-bornes-disponibilite-temps-reel).

## Related optional sources (not yet ingested)

- [INSEE 2022 population by IRIS](https://www.insee.fr/fr/statistiques/8647014) and [IGN/INSEE IRIS boundaries](https://www.data.gouv.fr/datasets/contours-iris-r-2): downloadable files for a later spatial exposure analysis; not APIs used by the collector.
- [Open-Meteo API](https://open-meteo.com/en/docs): optional weather covariate only after the station-time pipeline is stable; not currently called.

