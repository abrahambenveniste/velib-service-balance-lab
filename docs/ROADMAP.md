# Roadmap

## Completed

- [x] Verify the public GBFS discovery, station-information and station-status feeds respond without a key.
- [x] Implement raw snapshot collection with UTC request times, body hashes, HTTP metadata and station-information reference reuse.
- [x] Capture six live status observations and compare changes in inventory, source timestamps and station flags.
- [x] Implement an offline audit that validates hashes, unique station IDs, metadata joins, count ranges, type sums, aliases, coordinates and capacity.
- [x] Produce a normalized local station-time CSV, capture-level CSV and JSON audit report; keep all generated data Git-ignored.
- [x] Document actual versus planned languages, APIs, tools, fields, commands, decisions and limitations in the [work log](WORKLOG.md), [data dictionary](DATA_DICTIONARY.md), [operations guide](OPERATIONS.md), and [data audit](DATA_AUDIT.md).
- [x] Create the public repository `abrahambenveniste/velib-service-balance-lab` and publish the code and methodology.
- [x] Identify existing availability prediction and map projects; retain the network service-balance scope.
- [x] Identify downloadable IRIS population and boundary files for a later optional area analysis.

## Current milestone

1. **Complete the replacement 24-hour pilot.** It started at 2026-10-20 23:25:43 UTC using five-minute status polling, daily station-information refresh and run-specific logs. Two captures succeeded by 23:30:45 UTC, 300.9 seconds apart; coverage is not complete yet. On this Windows setup, one launch appears as a parent/child Python process tree, so monitor the tree rather than treating both entries as independent collectors.
2. **Review freshness and operational gaps.** Compare status body hashes, retrieval intervals, source report ages, station coverage and errors. Preserve stale report ages as diagnostics until timestamp semantics are confirmed.
3. **Collect a multi-week sample.** Keep it local, record missed polls/outages/schema changes, and avoid treating repeated or stale payloads as fresh observations.

## Next milestones

4. **Freeze service definitions before estimating rates.** Define usable mechanical/e-bike availability, return-dock availability, station operating state, missing/stale handling and the maximum polling gap allowed when estimating a duration.
5. **Publish a rider reliability baseline.** Report observation coverage and uncertainty with station-level no-bike/no-dock measures. Do not convert a single snapshot's zero counts into reliability or demand.
6. **Add neighbourhood context if useful.** Align IRIS boundary and population vintages; compare point-in-polygon assignment with small walking catchments; state that residents are only a rough exposure denominator.
7. **Validate both audiences.** Ask riders and mobility planners what would help them decide and where the measure might mislead; document feedback before designing a dashboard.
8. **Decide if a policy simulation is supportable.** Define cargo/time constraints and demand assumptions. If assumptions dominate, keep the work descriptive until operator data or expert feedback is available.
9. **Write a public research note and CV bullet from measured results.** State sample period, coverage, limitations and actual outcomes. Do not claim savings or service improvements that are only simulated.

## Decision log

- **2026-10-20** — Direct public GBFS discovery and station feeds responded without an API key; no dependable official history was found, so prospective collection is necessary.
- **2026-10-20** — Two observations 60.9 seconds apart showed inventory changes at 63 stations while `last_reported` did not change. Preserve both clocks.
- **2026-10-20** — A later comparison showed inventory changes at 343 stations and report timestamps at 77; newest report time lagged retrieval by about 55 minutes. This justified a longer freshness probe, not a stale cutoff.
- **2026-10-21** — The six-snapshot baseline spanning under 22 minutes had 1,517 unique station IDs per snapshot and complete metadata joins. Hashes, counts, bike-type sums and aliases reconciled. Its final five-minute pair had inventory changes at 253 stations and report-time changes at 58; the second sample's report-age median was about 11 minutes.
- **2026-10-21** — The public portal labels the feed GBFS 1.0 and says updates are each minute; discovery advertised TTL 3,600 seconds. Feed-level `last_updated` and observed cache headers were absent. Current GBFS v3 latency notes are only a diagnostic comparator for this legacy feed.
- **2026-10-21** — The first 24-hour pilot was interrupted after two five-minute-cadence captures. The Windows parent/child process pair was initially misread as two independent runs; stopping the child ended the worker tree. Keep the original logs and captures as an incomplete run.
- **2026-10-21** — A replacement pilot started at 23:25:43 UTC; captures completed near 23:25:45 and 23:30:45 UTC, with the process tree present and stderr empty at 23:31:03 UTC. The first post-restart capture followed the prior snapshot by 706.7 seconds; the next was 300.9 seconds later.
- **2026-10-21** — The audit and field dictionary were added. The current eight-capture audit produces 12,136 local station-time rows, a capture summary CSV and a JSON integrity report, all ignored by Git. State-transition counters distinguish new/recovered/persistent zero-bike and zero-dock observations without estimating duration.

