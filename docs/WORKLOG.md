# Project work log

This file records acquisition, analysis, tool versions, decisions and operational incidents so that the public project can be audited and resumed without relying on chat history. Times are UTC unless labelled Europe/Paris. Raw captures and generated outputs are local and Git-ignored.

## Environment observed on 21 October 2026

| Component | Observed version / configuration | Status |
|---|---|---|
| OS and shell | Windows 11 Professionnel; PowerShell 7.6.5 | Used to set up and run the local collector |
| Python | 3.13.15 in the system and project virtual environment | Used for collection and analysis; package requires Python 3.11+ |
| HTTP client | HTTPX 0.28.1 | Used by `collector.py` for HTTPS JSON GET requests |
| Other Python dependencies | Python standard library (`argparse`, `csv`, `datetime`, `hashlib`, `json`, `pathlib`, `tempfile`) | Used by the collector/auditor; no Pandas, Polars, Pydantic, DuckDB or database used yet |
| Git | 2.55.0.windows.5 | Local working copy has no remote configured; published updates are written to the connected public repository through GitHub's contents API connector |
| GitHub | `abrahambenveniste/velib-service-balance-lab`, public, default branch `main` | Holds source code and documentation; raw and normalized data are excluded |
| External APIs | Vélib operator GBFS discovery, station information and station status | Public, HTTPS, no key; collector uses a 20-second request timeout and follows redirects |

Versions above describe this working environment at the time of the capture. Python's project constraints are the reproducible requirements; local tool versions are observations, not hard pins.

For this publication, the connected GitHub tool uses Git Data API operations: create blobs for changed files, build a tree on the current `main` tree, create one commit parented to the checked-out head, and update `main` with an expected-head check. Local `git` is not configured with a remote in this workspace; generated data remains untracked and Git-ignored.

## Reproduction commands

Run these from the repository root in PowerShell. Installation is local; do not commit `.venv` or data folders.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m velib_lab.collector --once
.\.venv\Scripts\python.exe -m velib_lab.audit --input-dir data/raw --output-dir data/processed
```

The bounded 24-hour pilot uses `--interval-seconds 300 --duration-hours 24`. The collector requests the discovery document each cycle, resolves station feed URLs from that response, refreshes station information once per 24 hours, requests station status on every cycle, and writes capture bodies plus metadata atomically. HTTP, JSON, and file operations are logged through stdout/stderr; failed requests raise an error and do not produce a completed capture directory. No explicit retry/backoff mechanism is implemented yet.

The audit reads every `capture.json` below `data/raw/`, verifies body hashes, checks station ID uniqueness and the information/status join, checks bike-type sums and aliases, validates counts and coordinates, computes report-age distributions, compares consecutive snapshots, and writes three ignored outputs under `data/processed/`. The CSV is a normalized analytical view; source JSON remains the authoritative record.

## Work completed

### 20 October 2026 — source and feasibility audit

1. Opened the official transport.data.gouv.fr Vélib listing and its operator GBFS discovery URL.
2. Requested live JSON from the discovery, `station_information`, and `station_status` feeds using Python + HTTPX; no API key was needed. Responses were HTTP 200 and the two station feeds each contained 1,517 records.
3. Inspected the actual field names, timestamp values, TTL, and HTTP headers. Discovery advertised TTL 3,600 seconds. The sampled discovery and status bodies lacked feed-level `last_updated` and `version`; sampled response headers lacked `Cache-Control`, `Age` and `ETag`.
4. Captured three early status snapshots. Inventory changed despite unchanged `last_reported` at all stations in the first one-minute comparison. A later comparison showed inventory and report times do not move in lockstep.
5. Implemented the first Python collector, then changed it to store station information once daily and reference it from subsequent captures. The first three older captures retain a per-capture information copy; later captures use `data/reference/station_information/`.
6. Documented the source, terms, scope, design and planned stack. The raw data directories are excluded through `.gitignore`.

### 20–21 October 2026 — six-snapshot baseline

Input: the six complete capture folders in `data/raw/`, with status retrieval times from **2026-10-20 22:51:59.572 UTC** through **23:13:58.382 UTC**. Total elapsed retrieval window: **21 minutes 58.8 seconds**. Status intervals were **54.9, 408.3, 518.1, 36.6 and 300.9 seconds**; the first four are setup/probe captures and the last 300.9-second interval is the intended pilot cadence.

Steps and results:

1. Inspected exact feed payloads and field unions. Status fields were `is_installed`, `is_renting`, `is_returning`, `last_reported`, `numBikesAvailable`, `numDocksAvailable`, `num_bikes_available`, `num_bikes_available_types`, `num_docks_available`, `stationCode`, `station_id` and `station_opening_hours`. Station information exposed `capacity`, `lat`, `lon`, `name`, `rental_methods`, `stationCode`, `station_id` and `station_opening_hours`.
2. Added `src/velib_lab/audit.py`, a standard-library audit and normalizer. Ran `python -m velib_lab.audit --input-dir data/raw --output-dir data/processed` against all six folders. It generated 9,102 station-time rows (1,517 × 6) plus a capture summary and JSON audit report. These outputs remain local and ignored by Git.
3. All six discovery, status and station-information body SHA-256 values matched capture metadata; all six status-body hashes were distinct. Every snapshot had 1,517 valid unique status IDs and 1,517 valid unique information IDs with a complete one-to-one join.
4. Across all 9,102 status rows, there were no negative/invalid bike or dock counts or invalid operating flags; bike type breakdowns reconciled to the total bike count, and camel-case aliases agreed with the snake-case fields. Every joined coordinate and capacity passed range/type checks.
5. At the last capture, total reported inventory was 19,773 bikes (11,735 mechanical; 8,038 e-bikes) and 28,403 available docks. There were 58 zero-bike stations and 63 zero-dock stations. These are one-time network counts, not availability rates or service-performance estimates.
6. Between the two pilot-cadence captures 300.9 seconds apart, inventory changed at 253 of 1,517 stations and `last_reported` changed at 58. All 1,517 payload report timestamps were more than five minutes old at retrieval; 179 were more than 15 minutes old, 17 more than one hour old, and 14 more than 24 hours old. Nearest-rank report-age quantiles were p50 **658.4 seconds**, p90 **923.4 seconds**, p95 **1,030.4 seconds**, and p99 **10,558.4 seconds**. The oldest value was roughly 8.9 years old. These report ages are quality diagnostics; they are not yet used to drop observations or claim that inventory itself is stale.
7. Status JSON was 463,945–463,965 bytes in this sample. At 288 five-minute polls/day, that implies approximately 133.6 MB/day of status bodies before filesystem overhead, plus small discovery/metadata files. This is an observed-size estimate, not a storage guarantee.

The six-snapshot window is too short to estimate recurring demand, reliability, seasonality or policy impact. The first audit script deliberately describes the snapshot facts and exposes data quality before modelling.

### 21 October 2026 — pilot process recovery

The first 24-hour run began at approximately **2026-10-20 23:08:49 UTC**. It produced two status snapshots five minutes apart, but did not remain active through the next process check at **23:21 UTC**. Windows showed two `python.exe` entries with the same command line in a parent/child relationship; I initially misidentified the child as an independent duplicate and stopped it, which ended the worker tree. The 24-hour pilot was therefore incomplete. Preserve its two snapshots and log as observations; do not call this a completed day.

### 20 October 2026 UTC / 21 October Europe/Paris — replacement pilot

1. Checked that no collector process remained, then launched one bounded 24-hour collector with `--interval-seconds 300 --duration-hours 24` and separate logs at `data/logs/collector-pilot-rerun.stdout.log` and `.stderr.log`.
2. The background launch appeared as one parent/child process tree (root PID 24788; worker PID 14788 at launch), not two independent collectors. Both entries had the same command line; the child PID's parent was the root PID.
3. The first replacement capture completed successfully as `20261020T232543967011Z` at about **23:25:45 UTC**: 1,517 status records, HTTP 200 and no stderr output. At the 23:26:34 UTC check, the process tree was still present.
4. Re-ran the offline audit. It now processed **seven** captures and **10,619** station-time rows. All seven discovery, status and station-information hashes matched; every status/information ID set joined one-to-one; count, type-sum, alias, flag, coordinate and capacity checks passed; seven status payload hashes were distinct.
5. This new sample arrived **706.7 seconds** after the prior capture because of the interrupted run/restart. Do not describe that pair as a five-minute interval. The earlier 300.9-second pair remains the only complete regular five-minute comparison at this point.
6. The new capture had 19,878 total reported bikes (11,772 mechanical; 8,106 e-bikes), 28,297 available docks, 59 zero-bike stations and 68 zero-dock stations. Its `last_reported` p50 age was 1,365.1 seconds; all 1,517 timestamps were older than 15 minutes, 17 older than one hour and 14 older than 24 hours. This is a different point-in-time snapshot, not a change estimate over a standard poll interval.

### 20 October 2026 UTC — five-minute follow-up

1. At **23:31:03 UTC**, verified the replacement process tree was still present and its stderr log remained empty. Stdout contained a second capture, `20261020T233045095136Z`, retrieved at about 23:30:45 UTC.
2. Its status retrieval was **300.9 seconds** after the first replacement capture. This is a second observed five-minute interval with a distinct status-body hash and 1,517 station rows.
3. Added zero-bike and zero-dock state-transition counters to `src/velib_lab/audit.py`: newly zero, recovered from zero and zero in both snapshots. These counts compare two point observations; they are not durations.
4. Re-ran the audit across **eight captures / 12,136 station-time rows**. Discovery, status and station-information hashes matched; IDs/joins, count/type totals, aliases, flags, coordinates and capacities still passed.
5. Between the two replacement captures, bikes went from 19,878 to 19,865 (11,772→11,777 mechanical; 8,106→8,088 e-bike), and available docks went from 28,297 to 28,310. Inventory changed at 220 stations; `last_reported` changed at 58; both changed at 10. Zero-bike counts were 59 in both captures: 3 newly zero, 3 recovered, 56 zero in both. Zero-dock counts were 68 then 67: 1 newly zero, 2 recovered, 66 zero in both. Net count changes do not identify individual trips or operator actions.
6. The second replacement sample's report-age p50 was **1,671.9 seconds** and p90 **1,937.9 seconds**; all 1,517 reports were over 15 minutes old, 17 over one hour and 14 over 24 hours. No timestamps were missing or future-dated.

The replacement run has two successful captures and remains active, but its 24-hour coverage is not complete. Its run-specific stdout/stderr files are under ignored `data/logs/`. Continue to record each poll, any missed interval or schema change, and the final stop time.

## Ongoing decision log

- Preserve raw response bodies locally and their SHA-256 hashes in manifests; do not upload the raw history.
- Use UTC for storage and Europe/Paris only for user-facing labels.
- Keep retrieval time separate from `last_reported`.
- Do not bridge service-gap durations across long or missing sampling intervals until a rule is predeclared.
- Do not interpret inventory deltas as trips: customer trips, operator rebalancing, maintenance and feed corrections are not distinguishable in these snapshots.
- Keep optional SQL, DuckDB, Parquet, geospatial enrichment, weather, optimization and interface work marked as planned until actually implemented.

## Session update template

For each new collection or analysis session, append: UTC start/end; commands and tool versions; source URLs and any changed endpoint; input capture IDs/time window; data-quality checks and definitions; output files; results and limitations; operational errors or restarts; repository files published. Never paste credentials or unreviewed raw rider-level data.

### 21 October 2026 UTC — resumed collection and aligned metadata refresh with feed TTL

**Tools and environment:** Windows 11, PowerShell 7.6.5, Python 3.13.15, HTTPX 0.28.1, Python standard-library JSON/CSV audit, and the connected GitHub Git Data API for publication. Local Git remains unconfigured with a remote. All captures, manifests, normalized station rows, audit outputs and run logs remain ignored locally.

**Source and commands:** used the existing official GBFS discovery URL to resolve station-information and status URLs; no credentials or new endpoints. Confirmed the live status feed with `python -m velib_lab.collector --once --output-dir data/raw`, then refreshed station information with `python -m velib_lab.collector --once --station-info-refresh-hours 1`. Audited with `python -m velib_lab.audit --input-dir data/raw --output-dir data/processed`. The active bounded command is `python -m velib_lab.collector --interval-seconds 300 --duration-hours 24 --station-info-refresh-hours 1`.

**Operational finding:** the replacement process started at **2026-10-20 23:25:43 UTC** and wrote captures through `2026-10-20T233545952014Z` (status retrieved 23:35:52.850 UTC). It remained present in the Windows process list, but no later capture appeared until 2026-10-21 20:58:41.462 UTC. A fresh one-off request at 20:58:34.229 UTC returned successfully, so the lack of captures was not a current feed-access failure. The cause of the long gap is not established. The old process tree was stopped after verifying its exact collector command line; the gap is recorded and not bridged.

**Data quality finding:** the two 20:58 captures 7.2 seconds apart had the same status-body hash. Both status payloads had 1,519 unique IDs, while the cached station-information body (retrieved 2026-10-20 23:08:20.756 UTC) had 1,517. The two unmatched status-only IDs were `27414512` (code `2017`) and `380891087` (code `4007`); both were flagged uninstalled, not renting and not returning. A third capture at 20:58:59.827 UTC also had the same 1,519/1,517 mismatch. The station-information feed advertised `ttl=3600`; a forced refresh at 20:59:44.131 UTC returned 1,519 records, after which the 21:00:50.233 UTC capture joined 1,519-to-1,519. Changed the collector default and the pilot command to an hourly station-information refresh. The full audit's historical join validation remains false due to the three pre-refresh captures. The three mismatched snapshots also lack joined coordinates/capacity for those same two IDs; later captures have zero invalid coordinate/capacity counts.

**Current sample and limits:** at 21:01:02 UTC the audit covered 14 captures / 21,248 station-time rows / 13 distinct status hashes. The latest capture reported 19,025 bikes (11,430 mechanical; 7,595 e-bikes), 29,146 docks, 61 zero-bike stations and 39 zero-dock stations. Median `last_reported` age was 3,336.2 seconds; p90 was 3,606.2 seconds; all 1,519 reports were over 15 minutes old. The 23:35:52.850 UTC to 20:58:34.229 UTC sampling gap was 76,961.4 seconds. The latest counts are a point-in-time observation and cannot be compared as a five-minute delta across that gap.

**Restart:** a fresh run began at **2026-10-21 21:00:47 UTC** (process tree root PID 25112) with 300-second status polling, a 24-hour duration, and one-hour station-information refresh. First capture: `20261021T210048814462Z`. Run logs: `data/logs/collector-pilot-hourly-info-20261021.stdout.log` and `.stderr.log`. At the time of this entry it was active, stderr was empty, and 24-hour completion was pending. Recheck the process tree and latest capture before calling it complete.

**Repository update:** publish the reviewed collector change and update `README.md`, `docs/DATA_AUDIT.md`, `docs/DATA_DICTIONARY.md`, `docs/OPERATIONS.md`, `docs/TECHNICAL_STACK.md`, and this work log together on `main` through the connected GitHub Git Data API (blobs, tree, commit, expected-head ref update). Do not publish raw captures, manifests, local logs, CSVs or station-level audit outputs.

### 21 October 2026 21:06 UTC — first regular interval after restart

Re-ran the documented standard-library audit against the 15 local capture folders. It processed **22,767 station-time rows** and found **14 distinct status hashes**. The new pilot's captures `20261021T210048814462Z` and `20261021T210550255055Z` were retrieved **301.0 seconds apart**. Both feed requests returned HTTP 200; each status/information snapshot had 1,519 unique IDs and a complete join. The second snapshot also had zero invalid coordinate/capacity counts, zero missing/future report timestamps, and a new status-body hash. The aggregate bidirectional-join flag remains false only because it includes the three earlier 1,519-to-1,517 mismatches; those two IDs have since appeared in station information.

At the second snapshot, reported inventory was 18,953 bikes (11,388 mechanical; 7,565 e-bikes) and 29,227 docks, with 61 zero-bike and 38 zero-dock stations. Median report age was **3,637.3 seconds** and p90 **3,907.3 seconds**; all 1,519 report timestamps exceeded 15 minutes, 952 exceeded one hour and 16 exceeded 24 hours. No missing or future report timestamps occurred. These are point-in-time values; do not bridge the earlier 21-hour gap to infer a five-minute change.

At **2026-10-21 21:06:15 UTC**, collector root PID 25112 and its child were present, stdout had two capture paths (88 bytes), and stderr remained empty. The run is incomplete and scheduled for 24 hours from 21:00:47 UTC if the host remains available. The audit outputs are local and ignored. The public README, data audit, operations guide and work log were updated to this checkpoint; no raw data was published.

