# Collector operations

## First setup

Python 3.11 or newer is required. From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m velib_lab.collector --once
```

Each capture fetches the GBFS discovery document and the advertised `station_status` feed, then writes their exact bodies and `capture.json` under `data/raw/YYYY-MM-DD/<capture-id>/`. The exact `station_information` body is stored separately under `data/reference/station_information/` and refreshed when it is more than 24 hours old or the advertised URL changes. Each capture records the reference path, retrieval time, hash, and station count; it does not duplicate the static metadata file. Both directories are ignored by Git. Capture metadata also stores each request's HTTP status, UTC retrieval time, hash, selected cache headers, record count, and feed TTL. Status metadata summarizes timestamp coverage, distinct station report times, and oldest/newest report ages. Capture folders are assembled before being moved into place, so a failed request does not look complete.

## Pilot cadence

Do not infer that a successful HTTP request represents a new station observation. The transport-data listing says the feed refreshes every minute, while the discovery document returned a TTL of 3,600 seconds and no cache headers in the initial live check. Run captures manually or at a modest interval for a short pilot, then compare response hashes, feed timestamps, and each station's `last_reported` before selecting a lasting cadence. Avoid minute-by-minute continuous capture until the pilot shows it adds new information.

The bounded pilot command polls status every five minutes for 24 hours and refreshes station information once per day:

```powershell
python -m velib_lab.collector --interval-seconds 300 --duration-hours 24
```

The five-minute interval is a pilot setting, not a claim that the upstream source updates at that rate. A day of status JSON is expected to use roughly 135 MB before filesystem effects; station information is stored once per refresh, not per capture. `--timeout-seconds` controls request timeouts; the default is 20 seconds. For an open-ended run, omit `--duration-hours` and stop with Ctrl+C.

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
