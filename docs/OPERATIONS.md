# Collection and analysis operations

## Environment and setup

Python 3.11 or newer is required. This working environment used Python 3.13.15, HTTPX 0.28.1, Windows 11 and PowerShell 7.6.5 on 21 October 2026. The project declares only HTTPX as a runtime dependency; analysis currently uses the Python standard library. From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m velib_lab.collector --once
```

No API key or credential is used. The collector uses HTTPX with a 20-second request timeout, follows redirects, and sends JSON accept and project user-agent headers. It has no explicit retry/backoff yet: a failed HTTP or JSON request raises an error and the failed cycle is not written as a complete capture.

## Capture process and files

Each capture makes requests in this order:

1. `GET` the GBFS discovery URL.
2. Select the advertised English feed URLs for `station_information` and `station_status`.
3. Reuse a local station-information body if its recorded URL matches and it was retrieved less than one hour ago; otherwise fetch and store a new version. The one-hour maximum matches the observed station-information `ttl=3600`.
4. `GET` the current station-status feed.
5. Write exact response bodies and `capture.json` into a temporary directory, then atomically move it into the dated capture directory.

Current layout:

```text
data/
  raw/YYYY-MM-DD/<capture-id>/
    gbfs.json
    station_status.json
    capture.json
  reference/station_information/
    <retrieval-time>.json
    <retrieval-time>.metadata.json
  processed/
    capture_summary.csv
    station_snapshots.csv
    audit_report.json
  logs/
    collector-pilot-*.stdout.log
    collector-pilot-*.stderr.log
```

The first three older captures contain a full `station_information.json` beside the other raw bodies. After daily reference storage was implemented, captures reference a shared file in `data/reference/`. `capture.json` records capture start/finish, collector version, feed URL, HTTP status, UTC retrieval time, response SHA-256, selected response headers, TTL, station counts and report-time summary. `station_status.json` remains one raw body per poll. The station-information reference metadata records its source URL, body hash, retrieval time and record count.

All `data/raw/`, `data/reference/`, `data/processed/` and `data/logs/` paths are excluded by `.gitignore`. Do not commit raw status archives, station-level normalized rows, local logs or secrets. Keep the public repository to code, documentation, and reviewed aggregate results.

## Pilot cadence and monitoring

The currently selected pilot command is five-minute status polling for 24 hours, with station information refreshed at most hourly:

```powershell
.\.venv\Scripts\python.exe -m velib_lab.collector --interval-seconds 300 --duration-hours 24 --station-info-refresh-hours 1
```

This cadence is an experiment setting, not a claim about the upstream update rate. The portal says one-minute updates, while discovery advertises `ttl=3600` and status report timestamps are often older. In the six-snapshot baseline, status JSON was about 464 KB per poll; 288 polls imply roughly 133.6 MB/day of status payloads before filesystem overhead.

For an attended run, keep stdout/stderr visible. For a background Windows run, write to a **run-specific** log path, record its process-tree root and UTC start time, and check the age of the latest capture as well as the process tree before treating the pilot as active. A live process alone does not prove collection is progressing.

The first 24-hour attempt ended after two captures and was incomplete. A replacement began at 2026-10-20 23:25:43 UTC. It produced captures at 23:25:45, 23:30:45 and 23:35:52 UTC, then produced no further capture until 2026-10-21 20:58:41 UTC, although its process tree was still present. The cause of this 21-hour gap is unknown. We stopped that process tree after a fresh one-off request confirmed the feed was reachable. The one-off capture at 20:58:34 UTC and the resumed replacement capture at 20:58:41 UTC had the same status-body hash; both are retained, but count as one distinct status payload. A short-lived collector launch produced a 20:58:59 UTC capture before metadata refresh was changed.

The station-information cache used by those three 20:58 captures was 21.8 hours old and contained 1,517 IDs, while status contained 1,519. A forced refresh at 20:59:44 UTC returned 1,519 information records and resolved the join for later captures. Both feeds advertise `ttl=3600`, so the collector default and active command now refresh the information snapshot hourly.

The current run started at **2026-10-21 21:00:47 UTC** using the command below. Its first two status captures, at 21:00:50.233 and 21:05:51.265 UTC, were 301.0 seconds apart and each joined 1,519 status IDs to 1,519 information IDs. At the 21:06:15 UTC audit it was active with empty stderr; if uninterrupted, its 24-hour stop time is 2026-10-22 21:00:47 UTC. Its logs are `data/logs/collector-pilot-hourly-info-20261021.stdout.log` and `.stderr.log` (ignored locally). The historical gap means this is a fresh run, not a continuation of the previous 24-hour window.

Example background launch (run once, then verify one collector launch tree and its run-specific log):

```powershell
$project = (Get-Location).Path
$python = Join-Path $project '.venv\Scripts\python.exe'
$runId = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmss'Z'")
$stdout = Join-Path $project "data\logs\collector-pilot-hourly-info-$runId.stdout.log"
$stderr = Join-Path $project "data\logs\collector-pilot-hourly-info-$runId.stderr.log"
New-Item -ItemType Directory -Force -Path (Split-Path $stdout) | Out-Null
$process = Start-Process -FilePath $python -ArgumentList @(
  '-m', 'velib_lab.collector', '--interval-seconds', '300', '--duration-hours', '24',
  '--station-info-refresh-hours', '1'
) -WorkingDirectory $project -WindowStyle Hidden -RedirectStandardOutput $stdout `
  -RedirectStandardError $stderr -PassThru
$process.Id
```

On this Windows setup a single `Start-Process` launch appeared as a parent/child pair with the same command line. Treat that as one launch tree; do not kill the child alone. If there are multiple independent launch trees, stop the unintended one and record the event. Never start a second independent run against the same output/log paths. After a run, inspect capture intervals, successful HTTP statuses, response hashes, station coverage, schema fields and source timestamp ages before using the observations.

## Reproducible local data audit

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m velib_lab.audit --input-dir data/raw --output-dir data/processed
```

The audit is implemented in `src/velib_lab/audit.py` and exposed as `velib-audit` after editable installation. It uses Python's standard library and makes no network call. For each capture it:

- re-hashes the exact status and station-information bodies;
- checks station record shape, ID uniqueness, and the two-way status/information ID join;
- checks non-negative integer bike/dock counts, type-breakdown reconciliation, count aliases, coordinates, and capacity;
- computes source-report age from `last_reported` minus status retrieval time without dropping old rows;
- records distinct timestamps, missing/future/old report counts and nearest-rank age quantiles;
- compares inventory, report timestamps, operating flags and raw response hashes with the prior capture.

Outputs are `capture_summary.csv`, `station_snapshots.csv` (one joined station-time row per station per capture), and `audit_report.json`. These are generated local files, not committed. The current data dictionary specifies fields, types and transformations. The tool does not impute missing counts, bridge stockout durations or estimate demand.

## Interpreting the data

- A successful poll is not necessarily a new upstream station observation; compare body hashes and per-station fields.
- Store/display capture retrieval time and `last_reported` separately.
- Treat missing or stale status as unknown, not as zero inventory. Keep bike stockout, dock stockout, station flags and data-quality status separate.
- A snapshot is not a trip. Inventory deltas do not reveal whether a customer rode, an operator moved a bike, maintenance removed it, or the provider corrected the feed.
- The current eight captures span under 39 minutes, including a six-capture baseline under 22 minutes and two replacement-pilot captures. They are suitable for ingestion/schema/freshness checks only. Before reliability estimates, collect multiple weeks and define missingness rules, stale cutoffs and the maximum gap bridged when computing durations.

## Storage, licensing and attribution

The public listing identifies the feed as ODbL. Keep raw and station-level transformed data local for now, attribute Vélib Métropole / Smovengo, and review share-alike requirements before distributing a derived database or substantive dataset. Do not store credentials or individual rider-location data. See [data sources and terms](DATA_AUDIT.md) and the [data dictionary](DATA_DICTIONARY.md).

