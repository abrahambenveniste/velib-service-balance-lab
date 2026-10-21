# Vélib Service Balance Lab

An applied data and systems project to measure where and when Vélib stations fail to provide a usable bike or dock, then evaluate transparent ways to prioritize rebalancing. Intended users are riders and people planning or operating shared-mobility services.

## Research question

How are bike and dock stockouts distributed across stations, time, and neighbourhoods, and which constrained rebalancing priorities could improve service without concentrating it only in the busiest areas?

## Why this scope

The basic rider-facing idea—predicting whether a Vélib station will have a bike or dock on arrival—already exists in [PasDeVélib](https://pasdevelib.app/paris), which also describes trip planning and reliability analytics. This project studies network-level service balance and rebalancing decisions instead of recreating that product.

## Feasibility and data audit — 20–21 October 2026

- The operator-hosted GBFS discovery, `station_information` and `station_status` feeds were reachable by HTTPS without an API key. The current sample returned HTTP 200 and 1,519 records in both station feeds.
- The 21:06 UTC audit covered 15 captures / 22,767 station-time rows with 14 distinct status-body hashes. Body hashes, unique IDs, count aliases, bike-type totals and operating flags passed. Three captures used a 21.8-hour-old, 1,517-record station-information reference against a 1,519-record status feed; the two missing IDs appeared after metadata refresh. Later captures join 1,519-to-1,519.
- The latest sample in that audit (21 October, 21:05:51 UTC) reports 18,953 bikes (11,388 mechanical; 7,565 e-bikes), 29,227 free docks, 61 zero-bike stations and 38 zero-dock stations. These are point-in-time counts, not trends or service rates.
- All 1,519 `last_reported` timestamps in that sample were over 15 minutes old; 952 were over one hour and 16 over 24 hours. Median report age was 60.6 minutes. See the [data audit](docs/DATA_AUDIT.md) for definitions and limits.
- The official listing says one-minute updates and labels its feed GBFS 1.0; discovery and station-information feeds advertised `ttl=3600`. The collector now refreshes station information hourly. Sampled status responses lacked feed-level `last_updated` and cache headers.
- The capture window spans about 22 hours but includes a 21-hour gap. It is not a continuous or completed 24-hour series and does not establish typical reliability, demand or intervention impact.

See the [data audit](docs/DATA_AUDIT.md), [data dictionary](docs/DATA_DICTIONARY.md), [project work log](docs/WORKLOG.md), [research design](docs/PROJECT_DESIGN.md), [technical stack](docs/TECHNICAL_STACK.md), [operations](docs/OPERATIONS.md) and [roadmap](docs/ROADMAP.md).

## Project stages

1. **Collection and data audit (implemented):** preserve raw public GBFS snapshots and freshness metadata, then verify hashes, station joins, counts, timestamps and changes between snapshots.
2. **Rider reliability:** measure no-bike, no-dock, station-state and unknown/stale intervals separately after enough history has accumulated.
3. **Planning view:** show where and when service gaps recur, including area distribution and uncertainty.
4. **Policy experiment (later):** replay constrained rebalancing priorities under visible assumptions. Do not claim operational savings without operator trip and vehicle data.

## Languages and tools

- **Implemented:** Python, HTTPX and Python standard library for collection, audit, hashing and CSV normalization; PowerShell for local operations; Git/GitHub and Markdown for code and research records.
- **Planned, not yet used:** DuckDB SQL, Parquet, geospatial joins, weather covariates, optimization, and an optional TypeScript map. See [implementation status](docs/TECHNICAL_STACK.md).

## Run collection and analysis

From PowerShell at the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m velib_lab.collector --once
.\.venv\Scripts\python.exe -m velib_lab.audit --input-dir data/raw --output-dir data/processed
```

The collector stores exact discovery and status bodies under `data/raw/`, and station information separately with hourly refresh under `data/reference/`. The audit writes local `capture_summary.csv`, `station_snapshots.csv`, and `audit_report.json` under `data/processed/`. Raw and processed data are Git-ignored. See the [operations guide](docs/OPERATIONS.md) for the bounded 24-hour pilot command and full file definitions.

The source and documentation are published in the [public GitHub repository](https://github.com/abrahambenveniste/velib-service-balance-lab). The [work log](docs/WORKLOG.md) records local tool versions, exact commands, sample windows, validation steps and limitations. Raw snapshots and station-level outputs remain local.

## Important limitations

Station inventories are snapshots, not trip records. Changes can reflect customer rides, operator rebalancing, maintenance or feed corrections. They do not identify origins/destinations or operator van routes. We will label observations, derived measures and intervention assumptions separately.

The data listing identifies the feed with ODbL terms. Preserve source attribution and review share-alike requirements before distributing derived databases; see [data sources and terms](docs/DATA_AUDIT.md).

