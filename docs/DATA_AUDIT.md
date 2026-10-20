# Data and API audit

**Source access checked:** 20 October 2026. **Snapshot analysis:** seven captures retrieved from 20 October 2026 22:51:59.572 UTC through 23:25:45 UTC. The first six are the short baseline; the seventh was the first capture after restarting the interrupted 24-hour pilot. **Purpose:** establish access and data quality before making any reliability or policy claim.

## 1. Live feed access

The operator GBFS source is linked from the [official Vélib open-data listing](https://transport.data.gouv.fr/datasets/velib-velos-et-bornes-disponibilite-temps-reel). All three feeds were reachable by unauthenticated HTTPS `GET`; each station feed returned HTTP 200 and 1,517 rows in all seven captures.

| Feed | URL | Role | Observed result |
|---|---|---|---|
| Discovery | `https://velib-metropole-opendata.smovengo.cloud/opendata/Velib_Metropole/gbfs.json` | Feed discovery | Advertised `gbfs`, `system_information`, `station_information`, `station_status`; `ttl=3600` |
| Station information | `https://velib-metropole-opendata.smovengo.cloud/opendata/Velib_Metropole/station_information.json` | Station IDs/codes, names, coordinates, capacity and descriptive fields | 1,517 records |
| Station status | `https://velib-metropole-opendata.smovengo.cloud/opendata/Velib_Metropole/station_status.json` | Bikes by type, free docks, operating flags and `last_reported` | 1,517 records per capture |

The portal says no key is required and reports a one-minute refresh cadence under GBFS 1.0. The captured discovery TTL was 3,600 seconds. Across the six capture manifests, feed-level `last_updated` and the sampled `Cache-Control`, `Age`, and `ETag` response headers were absent. We therefore store request retrieval time separately and do not equate a poll with a new upstream observation. The provider's discovered URLs are used at runtime; status URL is not guessed from a fixed path.

## 2. Six-capture baseline

These are **one-time network snapshots**, not rates of service, trip counts or demand. Bike totals include the reported mechanical and e-bike counts. Median source-report age uses the nearest-rank p50 across `last_reported` ages relative to status retrieval time.

| Status retrieved (UTC) | Seconds since previous | Bikes total (mechanical / e-bike) | Docks | Zero-bike stations | Zero-dock stations | Median `last_reported` age (min) | Reports older than 5 min |
|---|---:|---:|---:|---:|---:|---:|---:|
| 22:51:59.572 | — | 19,772 (11,755 / 8,017) | 28,404 | 55 | 54 | 49.0 | 1,517 |
| 22:52:54.462 | 54.9 | 19,777 (11,752 / 8,025) | 28,397 | 55 | 54 | 49.9 | 1,517 |
| 22:59:42.774 | 408.3 | 19,812 (11,754 / 8,058) | 28,364 | 56 | 60 | 56.6 | 1,517 |
| 23:08:20.892 | 518.1 | 19,776 (11,738 / 8,038) | 28,402 | 59 | 61 | 5.4 | 895 |
| 23:08:57.467 | 36.6 | 19,774 (11,735 / 8,039) | 28,403 | 58 | 61 | 6.1 | 1,116 |
| 23:13:58.382 | 300.9 | 19,773 (11,735 / 8,038) | 28,403 | 58 | 63 | 11.0 | 1,517 |
| 23:25:45 | 706.7 | 19,878 (11,772 / 8,106) | 28,297 | 59 | 68 | 22.8 | 1,517 |

All seven status payload hashes were distinct. In each snapshot, 1,517 unique status station IDs joined one-to-one to 1,517 station-information IDs. Status JSON bodies were 463,945–463,965 bytes. At 288 five-minute polls per day, that observed size implies about **133.6 MB/day** of status bodies before filesystem overhead, plus small discovery and metadata files.

The first five-minute-cadence pair was 300.9 seconds apart. Bike or dock counts changed at **253 of 1,517 stations**; `last_reported` changed at **58**, and both inventory and timestamp changed at **8**. The final two captures were 706.7 seconds apart because the first pilot was interrupted and restarted; inventory changed at 407 stations and `last_reported` at none across that longer gap. The inventory changes show the feed is dynamic. Their partial overlap with report-time changes shows `last_reported` should not be treated as a proxy for inventory-change time.

### Integrity and field checks

The reusable audit (`python -m velib_lab.audit`) processed all 10,619 station-time rows and found:

- all six discovery, status and station-information body SHA-256 hashes matched their capture metadata;
- status and information station IDs were valid and unique, and the two sets joined exactly in both directions;
- no negative or invalid bike/dock counts were observed, and all operating flags were boolean or 0/1 values;
- mechanical/e-bike type breakdowns summed to `num_bikes_available` at every station;
- the duplicate camel-case counts (`numBikesAvailable`, `numDocksAvailable`) agreed with the snake-case fields in every row;
- latitude/longitude and capacity fields passed the implemented bounds/type checks in all joined station records.

At the latest sample, reported counts were 19,878 bikes (11,772 mechanical; 8,106 e-bikes) and 28,297 free docks; 59 stations reported zero bikes and 68 reported zero docks. `is_renting` and `is_returning` were false at 19 stations each; one station had `is_installed=0`. Zero count, service flags, missing records and timestamps are kept as separate states.

## 3. Timestamp freshness is an unresolved data issue

At the latest capture, `last_reported` ages were: minimum **1,262.1 seconds**, p50 **1,365.1 seconds**, p90 **1,630.1 seconds**, p95 **1,737.1 seconds**, p99 **11,265.1 seconds**, maximum **280,748,709.1 seconds** (about 8.9 years). All 1,517 reports were older than five minutes and 15 minutes; 17 were older than one hour; and 14 were older than 24 hours. No report timestamps were missing or in the future in this sample.

The portal labels the feed GBFS 1.0, which the current [GBFS release history](https://github.com/MobilityData/gbfs) marks deprecated. Current GBFS documentation describes `last_reported` as the station's last report to the operator backend and provides a five-minute latency guideline for near-real-time status feeds. This is a useful comparison, not a claim that this legacy feed implements the current version's requirements. Keep source-report age as a quality diagnostic, retain inventory snapshots, and do not drop records or choose a final stale cutoff until the producer's version and timestamp behavior are understood over a longer pilot.

The transport-data listing currently exposes quality indicators and validation results. These may change over time; the dataset quality table showed 98% availability, 0% compliance and 0% freshness, while the feed resource panel showed 99.9% availability and 3,042 validation errors. These platform indicators motivate independent schema and timestamp checks but do not by themselves prove the dataset unusable.

## 4. History and interpretation limits

The GBFS feed provides current system state, not a historical archive. No dependable official snapshot archive was verified for this audit. The project is collecting prospective snapshots locally. The seven-capture window spans under 34 minutes (the first-six baseline spans under 22 minutes) and cannot establish typical stockout duration, time-of-day effects, weekly reliability, causality or rebalancing impact.

Inventory deltas are net changes. They cannot distinguish customer rides, operator rebalancing, maintenance, disabled vehicles or feed corrections. These endpoints contain no trip trajectories, rider identifiers or operator vehicle routes. Missing or stale data must remain **unknown**, not zero. Before estimating gap duration, declare how long an observation gap may be bridged and how stale records are treated.

## 5. Existing work and project distinction

The data portal's reuse listings include [PasDeVélib](https://pasdevelib.app/paris), which predicts arrival availability and offers reliability analytics and trip planning, plus live availability maps. A new arrival-probability app would duplicate existing work. This project focuses on network-level service gaps, distribution across areas, and a later assumption-explicit rebalancing simulation.

## 6. Other potential sources (not yet ingested)

| Source | Use | Access and current decision |
|---|---|---|
| [INSEE 2022 population by IRIS](https://www.insee.fr/fr/statistiques/8647014) | Optional denominator for neighbourhood service measures | Downloadable CSV/XLSX, not a live API; add after snapshot pipeline |
| [IGN/INSEE IRIS boundaries](https://www.data.gouv.fr/datasets/contours-iris-r-2) | Spatial assignment of station points | Downloadable geospatial data; align geography vintage before joining |
| [Open-Meteo](https://open-meteo.com/en/docs) | Optional weather covariate | Not needed for availability measurement; not called yet |
| [Île-de-France Mobilités PRIM Vélib API](https://prim.iledefrance-mobilites.fr/en/apis/idfm-velib) | Alternative source | Requires account/quotas; unnecessary while direct open GBFS works |

## 7. Licensing and attribution

The listing identifies the dataset with the [Open Database License (ODbL)](https://doc.transport.data.gouv.fr/le-point-d-acces-national/cadre-juridique/conditions-dutilisation-des-donnees/licence-odbl). Preserve attribution to Vélib Métropole / Smovengo. Raw feed history and station-level derived rows stay local; before distributing derived databases, review attribution and share-alike terms. See the [data dictionary](DATA_DICTIONARY.md) for fields and storage provenance.

