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
- The public data portal says the feeds are refreshed each minute. The GBFS discovery response currently advertises `ttl=3600`; we will measure source timestamps and avoid assuming that every poll contains a new observation.
- No dependable historical snapshot archive is documented in the feed. The project needs to collect and retain its own history before making claims about patterns or policy impact.
- The data portal currently shows data-quality warnings. Ingestion will record stale timestamps, missing stations, schema changes, and malformed counts rather than silently treating them as zero.

See [the data audit](docs/DATA_AUDIT.md), [research design](docs/PROJECT_DESIGN.md), [technical stack](docs/TECHNICAL_STACK.md), and [roadmap](docs/ROADMAP.md).

## Proposed first deliverable

1. A durable, documented collector for the public GBFS feeds.
2. A station-time reliability dataset that distinguishes “no usable bike,” “no free dock,” and “station/feed unavailable.”
3. A public-facing map or report showing the frequency and duration of service gaps by time and area.
4. A later, explicitly assumption-based rebalancing-policy simulation. It will not be presented as a real operational savings estimate without operator trip and vehicle data.

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

The first capture is written below `data/raw/` with the exact feed responses and a metadata file. Raw snapshots are ignored by Git. Start with single captures; use the [operations guide](docs/OPERATIONS.md) before enabling continuous polling.

The working directory currently has no GitHub remote. The connected GitHub account has separate weather-market-making and F1 repositories; this project should have a dedicated repository rather than being mixed into either. The GitHub connector can write files to an existing repository but does not expose repository creation.

## Important limitations

Station inventories are snapshots, not trip records. Changes can reflect customer rides, operator rebalancing, maintenance, or feed corrections. They do not identify origin-destination demand or the operator's actual van routes. We will report observed service gaps directly and label any intervention simulation assumptions clearly.

The Vélib status feed is published under ODbL terms. We will preserve attribution and review share-alike requirements before distributing derived databases. See [data sources and terms](docs/DATA_AUDIT.md).

