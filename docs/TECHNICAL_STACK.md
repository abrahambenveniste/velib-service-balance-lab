# Proposed technical stack

The stack is intentionally small at first. Add a web map or hosted service only after the data audit shows that it helps answer the research question.

## Languages

| Language | Proposed use | Status |
|---|---|---|
| Python | GBFS collection, schema validation, time-series analysis, geospatial joins, and policy simulation | Core |
| SQL | Repeatable station-time aggregations and analytical queries | Core; DuckDB SQL initially |
| TypeScript | Browser interface for maps and filters | Optional, after the analysis is useful |
| HTML/CSS | Web presentation if a browser interface is built | Optional with TypeScript |

## Tools and libraries

- **HTTPX**: HTTPS requests, timeouts, and retry/backoff for public JSON feeds.
- **Pydantic**: validate feed records and keep schema changes visible.
- **DuckDB + Parquet**: local analytical storage; partition by capture date and keep raw feed captures separate from normalized tables.
- **Polars or pandas**: time-series transformations; choose one after checking the data-volume workflow.
- **GeoPandas/Shapely**: station-to-IRIS spatial joins and catchment sensitivity analysis.
- **SciPy or OR-Tools**: candidate constrained allocation/route optimization for the later simulation; use only if simple heuristics warrant it.
- **React + TypeScript + MapLibre**: candidate UI stack, not selected until a map has a specific user decision to support.
- **Git/GitHub and Markdown**: versioned code, source citations, experiment decisions, and release notes.
- **Docker**: optional reproducible local environment if it reduces setup friction.

No API key is currently needed for the direct public GBFS feeds. Do not store credentials in the repository if a later optional source requires them.

## Data flow

1. Fetch GBFS discovery and the station-information/status feeds.
2. Preserve retrieval time, source timestamps, endpoint, and a hash of each raw response.
3. Validate station IDs, count ranges, expected station coverage, and timestamp freshness.
4. Write raw snapshots locally; normalize into station-time records in Parquet.
5. Query with DuckDB; add census geometry and population in a separate, versioned enrichment step.
6. Publish aggregate measures and documented analysis. Keep raw data local unless redistribution terms are confirmed.

## Initial operations decisions

- Polling interval: start conservatively and choose after checking actual feed update behavior; the portal says one minute while the discovery document currently reports `ttl=3600`.
- Storage: local partitioned Parquet first. Estimate storage after measuring actual response sizes and choosing the capture interval.
- Hosting: undecided. Do not add a cloud database or paid host before the collector and user need are clear.
- User interface: undecided. A concise public report may be more useful than an interactive map for the first milestone.

## Reproducibility and data handling

- Store timestamps in UTC and display local Europe/Paris time explicitly.
- Keep event/source time distinct from local retrieval time.
- Preserve feed versions, schema fields, transformations, exclusions, and license attribution.
- Exclude raw snapshot archives and generated datasets from Git by default.
- Publish estimates with missingness and freshness indicators.
- Treat ODbL database-sharing requirements as a release constraint, not a footnote.
