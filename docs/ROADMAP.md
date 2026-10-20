# Roadmap

## Completed in the initial feasibility pass

- [x] Verify the public GBFS discovery feed responds.
- [x] Verify live station-information and station-status feeds return records without an API key.
- [x] Implement the first snapshot collector and capture one live observation (HTTP 200; 1,517 records from both station feeds).
- [x] Capture a second live status observation one minute later and compare inventory with per-station timestamps.
- [x] Capture a third observation and quantify changing station inventory alongside uneven report timestamps.
- [x] Record the current fields, record count, stated refresh cadence, and GBFS TTL discrepancy.
- [x] Identify the missing historical archive requirement.
- [x] Find an existing Vélib arrival-availability predictor and narrow the project away from duplicating it.
- [x] Identify downloadable IRIS population and boundary sources for a later area analysis.
- [x] Draft the data, research, and stack documentation locally.

## Next milestones

1. **Run a structured freshness pilot.** Compare repeated source timestamps and capture intervals before selecting a lasting cadence.
2. **Collect a useful sample.** Keep raw captures local, log outages/schema changes, and do not mistake repeated responses for new observations.
3. **Publish baseline service measures.** Show bike and dock access separately, identify stale data, and document spatial aggregation choices.
4. **Validate both audiences.** Get feedback from riders and people who plan or operate shared mobility; record what helps and what misleads.
5. **Decide whether policy simulation is supportable.** Define cargo/time constraints and demand assumptions. If assumptions dominate, keep the work descriptive until operational data or expert feedback is available.
6. **Write the public research note and CV bullet from actual results.** Report sample period, coverage, limitations, and measured outcomes; do not claim savings or service improvements that were only simulated.

## Decision log

- 2026-10-21 — Direct arrival-availability predictions are already offered by PasDeVélib. The project is provisionally reframed as a network-level service-balance study with a possible constrained rebalancing simulation.
- 2026-10-21 — Current GBFS endpoints are reachable, but their historical feed was not found. Begin prospective capture before any time-series claim.
- 2026-10-21 — First end-to-end capture completed. Feed-level `last_updated` and HTTP cache headers were absent in the responses; station-level `last_reported` must be inspected to quantify source freshness.
- 2026-10-21 — Two snapshots 60.9 seconds apart showed inventory changes at 63 stations but no `last_reported` changes. Keep both clocks and investigate timestamp semantics before setting stale-data rules.
- 2026-10-21 — A third snapshot 396 seconds later showed bike/dock counts change at 342 stations and `last_reported` update at 77; the newest reported time still lagged retrieval by about 55 minutes.
- 2026-10-21 — Created public repository `abrahambenveniste/velib-service-balance-lab`; published the overview, data audit, design, stack, operations, roadmap, and collector.
