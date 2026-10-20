# Data and API audit

**Checked:** 21 October 2026  
**Purpose:** determine whether the proposed Vélib service-balance project can be built from accessible, documented data.

## 1. Vélib live station data — verified reachable

The primary source is the operator-hosted GBFS feed, linked from the official [Île-de-France open-data listing](https://transport.data.gouv.fr/datasets/velib-velos-et-bornes-disponibilite-temps-reel).

| Feed | URL | Role | Live check |
|---|---|---|---|
| GBFS discovery | `https://velib-metropole-opendata.smovengo.cloud/opendata/Velib_Metropole/gbfs.json` | Advertises the available GBFS feeds | Responded; listed `station_information` and `station_status`; reported `ttl=3600` |
| Station information | `https://velib-metropole-opendata.smovengo.cloud/opendata/Velib_Metropole/station_information.json` | Station ID/code, name, latitude, longitude, capacity | Responded; 1,517 station records |
| Station status | `https://velib-metropole-opendata.smovengo.cloud/opendata/Velib_Metropole/station_status.json` | Available bikes and docks, station operating flags, report time | Responded; 1,517 station records |

The status sample contained fields including `num_bikes_available`, `num_bikes_available_types` (mechanical and e-bike counts), `num_docks_available`, `is_installed`, `is_renting`, `is_returning`, `stationCode`, and `last_reported`. The station-information sample contained `station_id`, `stationCode`, `name`, `lat`, `lon`, and `capacity`.

### Access, cadence, and history

- The data portal says the JSON APIs are available without a key and the datasets are updated every minute under GBFS 1.0.
- The GBFS discovery response advertises a 3,600-second TTL. This differs from the portal's one-minute update statement. The collector should initially poll conservatively, retain source timestamps, and measure how often actual records change before choosing a permanent interval.
- The live endpoints provide current state. No official historical station-status archive was verified. We need to start our own snapshot history; until enough data accumulates, analyses must be described as preliminary.
- At one poll per minute, 1,517 station rows would be about 2.18 million rows per day before compression; five-minute snapshots would be about 437,000. Partitioned Parquet is a reasonable local starting point.

### Initial two-snapshot freshness probe

The collector captured two status feeds 60.9 seconds apart on 20 October 2026. Both contained the same 1,517 station identifiers. Bike counts changed at 61 stations and dock counts at 62 (63 stations had at least one tracked inventory/operating-field change), while `last_reported` stayed unchanged for all 1,517 records. In the second capture, 1,500 reported timestamps were 15–60 minutes before retrieval, three were 1–24 hours old, and 14 were over 24 hours old; one timestamp dated to 2017. The feed-level `last_updated` and HTTP cache headers were absent.

This is only a two-point probe, but it shows why source timestamps cannot be treated as a complete freshness test: reported inventory changed while per-station timestamps did not. Preserve both retrieval time and `last_reported`, quantify their behavior over a longer pilot, and do not discard data or label a station stale solely from `last_reported` until its semantics are understood.

### Quality and licensing

At the time of review, the transport-data page showed 98% availability, 0% compliance, 0% freshness, and 3,042 feed-validation errors. These platform quality indicators are a warning to independently validate timestamps, station coverage, count ranges, schema, and feed outages. They do not by themselves establish that the feed is unusable.

The dataset is listed under the [Open Database License (ODbL)](https://opendatacommons.org/licenses/odbl/). Preserve attribution. Before publishing collected or transformed databases, review the license's share-alike and database distribution requirements. Do not commit large raw snapshots to Git; keep them in local ignored storage and publish only permitted derived data.

## 2. Existing user-facing work — scope check

The data portal's [reuse listing](https://transport.data.gouv.fr/datasets/velib-velos-et-bornes-disponibilite-temps-reel) describes **PasDeVélib**, which already predicts near-future station availability in Paris, provides reliability analytics, and offers a trip planner. It also lists **VélibMap**, a live availability map. A direct arrival-probability app would therefore duplicate existing work.

This project's proposed distinction is network-level service balance: measure stockout intervals over time and space, then evaluate transparent rebalancing priorities under explicit capacity assumptions.

## 3. Neighbourhood geometry and population — downloadable, not an API dependency

| Source | URL | Use | Access/status |
|---|---|---|---|
| INSEE 2022 population by IRIS | [INSEE Population 2022 — IRIS](https://www.insee.fr/fr/statistiques/8647014) | Population denominator for neighbourhood-level service measures | Public CSV/XLSX download; national CSV is listed at about 22 MB. Data use the geography in force on 1 January 2024. Not a live API. |
| IRIS boundaries | [IGN/INSEE Contours…IRIS](https://www.data.gouv.fr/datasets/contours-iris-r-2) and [INSEE reference tables](https://www.insee.fr/fr/information/7708995) | Spatially join station coordinates to neighbourhoods | Public downloadable boundaries and reference files; select 2024 geography to align with the 2022 population release. |

Population is only a rough exposure denominator: residents are not the same as Vélib users or trip demand, and a station can serve people across an IRIS boundary. We should compare point-in-polygon assignment with small walking catchments and state the limitation in any map or report.

## 4. Optional weather covariate — not required for the first collector

[Open-Meteo Forecast API](https://open-meteo.com/en/docs) can provide hourly weather forecasts, and its [terms](https://open-meteo.com/en/terms) allow free non-commercial use subject to rate limits and CC-BY 4.0 attribution. It can help explain observed seasonal patterns. It is not needed to establish station-level availability measures, so adding it should wait until the base data pipeline is stable. Commercial use would require a paid plan.

## 5. Access decision

Use the operator GBFS discovery, station-information, and station-status feeds first. The [PRIM Vélib API page](https://prim.iledefrance-mobilites.fr/en/apis/idfm-velib) documents an alternative endpoint but requires a logged-in account and exposes quotas; it is unnecessary for the initial data audit because the open GBFS feed worked without credentials.
