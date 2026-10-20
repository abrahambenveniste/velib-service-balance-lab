# Collector operations

## First setup

Python 3.11 or newer is required. From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m velib_lab.collector --once
```

The collector fetches the GBFS discovery document, then follows its advertised URLs for `station_information` and `station_status`. It writes exact response bodies and `capture.json` under `data/raw/YYYY-MM-DD/<capture-id>/`. The metadata stores each URL, HTTP status, retrieval timestamp in UTC, body hash, selected cache headers, record count where available, and feed-level update/TTL fields where available. For the status feed it also summarizes timestamp coverage, distinct station report timestamps, and the oldest/newest report ages. The snapshot folder is assembled before being moved into place, so a failed request does not look like a complete capture.

## Pilot cadence

Do not infer that a successful HTTP request represents a new station observation. The transport-data listing says the feed refreshes every minute, while the discovery document returned a TTL of 3,600 seconds and no cache headers in the initial live check. Run captures manually or at a modest interval for a short pilot, then compare response hashes, feed timestamps, and each station's `last_reported` before selecting a lasting cadence. Avoid minute-by-minute continuous capture until the pilot shows it adds new information.

Continuous mode is available, but it is intentionally opt-in:

```powershell
python -m velib_lab.collector --interval-seconds 300
```

Stop it with Ctrl+C. A five-minute interval is only a pilot setting, not a claim that the upstream source updates at that rate. `--timeout-seconds` controls request timeouts; the default is 20 seconds.

The first end-to-end capture completed on 20 October 2026 at 22:51 UTC: all three requests returned HTTP 200 and each station feed contained 1,517 records. The feed-level `last_updated` field and `Cache-Control`, `Age`, and `ETag` response headers were absent in that capture. A second status capture 60.9 seconds later showed inventory changes at 63 stations even though `last_reported` stayed unchanged at all 1,517. This is an early signal to investigate, not enough evidence to declare the feed defective. Subsequent captures summarize timestamp coverage and age; the first capture's metadata predates that summary, but its raw feed contains the source timestamps.

## What is and is not collected

- Raw JSON for discovery, station information, and station status is captured with a local retrieval time.
- Station status includes current bike counts by type, available docks, station flags, and per-station report times.
- Station information includes station identifiers, names, coordinates, and capacity.
- There are no trip trajectories, customer identifiers, actual operator van movements, or historical status snapshots in these endpoints.
- Missing and stale data must be marked unknown; never convert it to zero bikes.

## Storage and sharing

Raw and future processed data directories are ignored by Git. Keep data locally during the capture pilot, monitor disk use, and publish only small aggregate outputs needed to reproduce the findings. Preserve source attribution and review [ODbL terms](https://opendatacommons.org/licenses/odbl/) before redistributing a database or substantial derived dataset. Do not add credentials or personal rider-location data.

## First analysis gate

Before presenting reliability or service-gap statistics, require enough valid snapshots to cover multiple weeks, report missing/stale observations, define the maximum interval bridged when estimating gap duration, and compare weekday/weekend and peak/off-peak periods. A single capture validates connectivity; it says nothing about service reliability.
