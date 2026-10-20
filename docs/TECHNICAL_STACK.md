# Technical stack and implementation status

The stack is deliberately small until the collected data justifies more infrastructure. This page separates tools actually used from options that remain unimplemented.

## Implemented

| Tool / language | Use | Status and measured version |
|---|---|---|
| Python | Collection, response hashing, timestamp summaries and station-time audit/CSV normalization | Implemented; code requires Python 3.11+; local environment used Python 3.13.15 |
| HTTPX | HTTPS GET, JSON responses, redirects and request timeout | Implemented; local version 0.28.1; 20-second timeout; no explicit retry/backoff |
| Python standard library | `argparse`, `csv`, `datetime`, `hashlib`, `json`, `pathlib`, `tempfile`, time and typing | Used for collector and audit; no analytical dependency beyond HTTPX |
| PowerShell | Local environment commands, process/log management and Windows operations | PowerShell 7.6.5 on Windows 11 Pro was observed |
| Markdown | Source notes, methodology, data dictionary, work log and reproducibility instructions | Implemented under `docs/` |
| Git / GitHub | Versioned public code and documentation | Git 2.55.0.windows.5 locally; repository `abrahambenveniste/velib-service-balance-lab` is public on `main`; connected GitHub API is used to publish files |

## Data APIs used

| Source | Request pattern | Authentication | Role |
|---|---|---|---|
| Vélib GBFS discovery | HTTPS `GET` on each poll; parse advertised feed URLs | None | Discover current endpoint URLs and record TTL |
| Vélib station information | HTTPS `GET` on initial retrieval and at most every 24 hours thereafter | None | Station metadata and coordinates |
| Vélib station status | HTTPS `GET` every pilot poll (300-second interval) | None | Current bike/dock counts, flags and report times |

The direct endpoints are listed in `docs/DATA_DICTIONARY.md`; the portal listing is linked from `docs/DATA_AUDIT.md`. Source bodies are stored locally with UTC request times and SHA-256 hashes. The analyst can reproduce data-quality checks offline using `velib_lab.audit`.

## Planned, not yet used

| Tool / language | Proposed use | Entry condition |
|---|---|---|
| DuckDB SQL | Repeatable time-series queries and station-level aggregations | Once multiple weeks of snapshots exist and the audit output is stable |
| Parquet | Compressed partitioned storage for longer history | After measuring accumulated data size and confirming redistribution terms |
| Polars or pandas | Larger time-series transforms/plots | Choose one only if standard-library CSV work becomes cumbersome |
| Pydantic or JSON Schema validator | Explicit feed schema validation | Add after matching the producer's deployed legacy GBFS version and defining acceptable extensions |
| GeoPandas / Shapely | Station-to-IRIS spatial joins and catchment sensitivity | After the service measures are established and the geography vintage is aligned |
| SciPy / OR-Tools | Constrained rebalancing scenario | Only after a clear baseline, realistic constraints and the data needed to defend assumptions |
| TypeScript, React, MapLibre, HTML/CSS | User-facing map or planning view | Only if a user decision is clearer in an interface than in a report |
| Docker | Environment packaging | If local setup drift becomes a real problem |
| Open-Meteo API | Optional weather covariate | Only after the core history is stable; not called by current code |

No SQL engine, notebook framework, plotting library, database, cloud host, frontend, weather API or optimization solver is part of the implementation yet. Do not list planned tools as project experience on the CV.

## Current local data flow

1. HTTPX requests the discovery document and obtains the station feed URLs.
2. HTTPX downloads status and, when required, station information.
3. The collector parses each response before storage, retains the exact response bytes and records response metadata/hash.
4. `velib_lab.audit` re-hashes those bodies, checks IDs/joins/counts/aliases/coordinates, and writes local CSV/JSON analytical outputs.
5. Raw and processed datasets stay out of Git; source notes and methodology are published.

## Next engineering choices

- Keep request intervals conservative while measuring upstream behavior. The portal says one-minute refresh, discovery advertises TTL 3,600 seconds, and the observed `last_reported` ages are often longer.
- Add retries and structured collector logging only after the current pilot demonstrates which failures occur and how to recover without hiding gaps.
- Choose a database/storage format only after the first multi-day dataset is audited.
- Preserve the separation between observed facts, derived measures and simulation assumptions in every report.

