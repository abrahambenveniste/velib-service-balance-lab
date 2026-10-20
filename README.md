# Vélib Service Balance Lab

An applied data and systems project to measure where and when Vélib stations fail to provide a usable bike or dock, then evaluate transparent ways of prioritizing rebalancing. The intended audience is riders and people planning or operating shared-mobility services.

## Research question

How are bike and dock stockouts distributed across stations, time, and neighbourhoods, and which constrained rebalancing priorities could improve service without concentrating it only in the busiest areas?

## Why this scope

The basic rider-facing idea—predicting whether a Vélib station will have a bike or dock on arrival—already exists in [PasDeVélib](https://pasdevelib.app/paris), which also describes a trip planner and reliability statistics. This project will study network-level service balance and rebalancing decisions instead of recreating that product.

## Feasibility checked 21 October 2026

- The operator's public GBFS discovery feed and its `station_information` and `station_status` endpoints responded to live requests without an API key.
- The live metadata and status feeds each returned 1,517 station records in this check. Status records include mechanical/e-bike counts, free docks, operating flags, and per-station report timestamps.
- The new Python collector completed an end-to-end capture: HTTP 200 from all three feeds and 1,517 records from each station feed. Its raw capture is local and Git-ignored.
- A short three-capture probe found changing inventory but uneven, often old `last_reported` timestamps; see the data audit before interpreting freshness.
- The public data portal says the feeds are refreshed each minute. The GBFS discovery response currently advertises `ttl=3600`; we will measure source timestamps and avoid assuming that every poll contains a new observation.
- No dependable historical snapshot archive is documented in the feed. The project needs to collect and retain its own history before making claims about patterns or policy impact.
- The data portal currently shows data-quality warnings. Ingestion will record stale timestamps, missing stations, schema changes, and malformed counts rather than silently treating them as zero.

See [the data audit](docs/DATA_AUDIT.md), [research design](docs/PROJECT_DESIGN.md), [technical stack](docs/TECHNICAL_STACK.md), and [roadmap](docs/ROADMAP.md).

## Project stages

1. **Collection (implemented; pilot underway):** a documented collector preserves public GBFS snapshots and freshness metadata.
2. **Rider reliability:** measure no-bike, no-dock, station-closed, and unknown/stale intervals separately.
3. **Planning view:** show where and when service gaps recur, including area-level distribution and uncertainty.
4. **Policy experiment (later):** simulate constrained rebalancing priorities with visible assumptions. Do not present this as operational savings without operator trip and vehicle data.

## Languages and tools

- **Python + HTTPX** are implemented for fetching the public feeds, retaining raw responses, and writing capture metadata. See [collection operations](docs/OPERATIONS.md).
- **SQL with DuckDB** is planned for repeatable analytical queries over snapshots; not implemented yet.
- **TypeScript** is optional for a web interface if a map helps answer a user question; React and MapLibre are candidates, not fixed choices.
- **Git and GitHub** will hold code, source notes, and reproducible project decisions. Raw data is excluded from Git.

## Run the collector

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m velib_lab.collector --once
```

Each capture stores the exact discovery and status responses below `data/raw/`; station information is stored separately and refreshed every 24 hours. Raw and reference data are ignored by Git. See the [operations guide](docs/OPERATIONS.md) for the bounded pilot command.

The source and documentation are published in the dedicated [public GitHub repository](https://github.com/abrahambenveniste/velib-service-balance-lab). Raw snapshots remain local and Git-ignored.

## Important limitations

Station inventories are snapshots, not trip records. Changes can reflect customer rides, operator rebalancing, maintenance, or feed corrections. They do not identify origin-destination demand or the operator's actual van routes. We will report observed service gaps directly and label any intervention simulation assumptions clearly.

The Vélib status feed is published under ODbL terms. We will preserve attribution and review share-alike requirements before distributing derived databases. See [data sources and terms](docs/DATA_AUDIT.md).
