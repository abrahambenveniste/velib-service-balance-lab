# Project design (provisional)

## User problem

Bike-share access is a network service. A user may find a bike at one point in the day and no bike or return dock later. Riders need reliable access; planners and operators need a clear view of when and where the service is failing.

The basic product of forecasting bike availability at arrival already exists for Vélib. This project will focus on network service reliability and operational allocation, where public snapshots can support a careful first analysis.

## Research question

**How are bike and dock stockouts distributed across stations, time, and neighbourhoods, and can constrained rebalancing priorities reduce those gaps without worsening service in less busy areas?**

## Intended outputs

### Phase 1: measurement

- Station-time counts for mechanical bikes, e-bikes, and available docks.
- Separately measure intervals with no usable bike, no return dock, station closed/not renting, or stale/missing feed data.
- Summarize frequency, duration, time-of-day, and persistence of stockout intervals.
- Aggregate to neighbourhood views only after selecting a consistent IRIS geography and testing catchment sensitivity.

### Phase 2: policy experiment

Evaluate simple priority rules such as moving bikes from stations with sustained surplus toward stations with sustained shortages, subject to declared cargo and travel-time limits. Compare rules on chronological replay and report the number of simulated shortage intervals avoided, the distribution of service across areas, and sensitivity to assumptions.

This is a simulation, not evidence of real operator savings. Public station counts do not reveal individual trips, operator truck movements, staffing, depot constraints, or maintenance actions. If those data are unavailable, every demand and rebalancing assumption must be visible and the result described as a counterfactual experiment.

## Metrics to define before analysis

- **Bike availability:** proportion of valid station-time intervals with at least one available mechanical bike; report e-bikes separately.
- **Dock availability:** proportion of valid intervals with at least one available return dock.
- **Gap duration:** estimated time in a no-bike or no-dock state, only across consecutive observations within a declared maximum gap.
- **Network access:** station-level measures and area aggregates, with alternate spatial catchments as a sensitivity check.
- **Policy simulation:** simulated shortage intervals avoided, travel/cargo budget used, and service impact by area. No single aggregate score should hide distributional effects.

Thresholds, aggregation interval, stale-feed cutoff, and weighting rules should be chosen before seeing comparative results.

## Data limitations and interpretation

- Inventory changes are net stock changes. They do not identify customer origins/destinations or distinguish customer rides from operator actions and data corrections.
- In an initial 60.9-second comparison, reported bike/dock inventories changed at 63 stations while `last_reported` stayed unchanged at every station. Feed-level update timestamps and cache headers were absent. This is a small probe, but it means we must study the semantics and behavior of both capture time and source timestamps before deciding whether records are stale.
- Census residents are not bike-share demand. Stations can serve commuters and visitors from outside the neighbourhood containing the station.
- Missing or stale records are unknown service, not zero bikes.
- A before/after or simulated improvement is not causal evidence that a policy would work in the live system.

## Real-world validation

The first practical check is to compare measured outages against actual station experience over a few weeks. Later, show the measurement and assumptions to a local rider group, mobility researcher, or operator and record their critique. No external outreach or operational pilot has been done.

## Scope boundaries

- No duplicate live map or arrival-availability predictor.
- No claims about operator efficiency without vehicle, trip, and staffing data.
- No precise individual-level location collection. The first version can be explored by station or area without storing a rider's home/work route.
- Weather and more detailed census attributes are optional additions after the core measures are working.
