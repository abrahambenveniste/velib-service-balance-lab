# Roadmap

## Completed in the initial feasibility pass

- [x] Verify the public GBFS discovery feed responds.
- [x] Verify live station-information and station-status feeds return records without an API key.
- [x] Implement the first snapshot collector and capture one live observation (HTTP 200; 1,517 records from both station feeds).
- [x] Capture a second live status observation one minute later and compare inventory with per-station timestamps.
- [x] Record the current fields, record count, stated refresh cadence, and GBFS TTL discrepancy.
- [x] Identify the missing historical archive requirement.
- [x] Find an existing Vélib arrival-availability predictor and narrow the project away from duplicating it.
- [x] Identify downloadable IRIS population and boundary sources for a later area analysis.
- [x] Draft the data, research, and stack documentation locally.

## Next milestones

1. **Choose repository and finalize the research question.** A dedicated public GitHub repository is recommended; the connected GitHub account currently has repositories for other projects, and the available connector cannot create a repository.
2. **Observe feed freshness.** Check repeated source timestamps and the effects of polling intervals before running a long-lived collector.
3. **Start durable snapshot capture.** Set a conservative cadence, log outages/schema changes, and keep raw data out of Git.
4. **Accumulate a useful sample.** Build several weeks of weekday/weekend and peak/off-peak observations before making reliability claims.
5. **Publish baseline service measures.** Show bike and dock access separately, identify stale data, and document spatial aggregation choices.
6. **Decide whether policy simulation is supportable.** Define cargo/time constraints and the demand assumptions. If assumptions dominate the result, keep the work descriptive until operational data or expert feedback is available.
7. **Validate usefulness with people who ride or plan mobility.** Record what they find useful, what misleads them, and what should change.
8. **Write the public research note and CV bullet from actual results.** Report sample period, coverage, limitations, and measured outcomes; do not claim savings or service improvements that were only simulated.

## Decision log

- 2026-10-21 — Direct arrival-availability predictions are already offered by PasDeVélib. The project is provisionally reframed as a network-level service-balance study with a possible constrained rebalancing simulation.
- 2026-10-21 — Current GBFS endpoints are reachable, but their historical feed was not found. Begin prospective capture before any time-series claim.
- 2026-10-21 — First end-to-end capture completed. Feed-level `last_updated` and HTTP cache headers were absent in the responses; station-level `last_reported` must be inspected to quantify source freshness.
- 2026-10-21 — Two snapshots 60.9 seconds apart showed inventory changes at 63 stations but no `last_reported` changes. Keep both clocks and investigate timestamp semantics before setting stale-data rules.
- 2026-10-21 — A dedicated GitHub repository is preferable to adding an unrelated project to the existing weather-market-making or F1 repositories.
