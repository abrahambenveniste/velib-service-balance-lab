"""Audit captured GBFS snapshots and produce a tidy station-time CSV."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def iso_utc(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


def stations_from(payload: dict[str, Any], label: str) -> list[dict[str, Any]]:
    data = payload.get("data")
    stations = data.get("stations") if isinstance(data, dict) else None
    if not isinstance(stations, list) or any(not isinstance(row, dict) for row in stations):
        raise ValueError(f"{label} does not contain a list of station objects")
    return stations


def station_key(value: Any) -> str | None:
    if isinstance(value, bool) or value is None:
        return None
    return str(value)


def valid_count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def parse_type_breakdown(value: Any) -> tuple[dict[str, int], bool]:
    """Accept both the observed array-of-single-key objects and object forms."""
    entries: list[tuple[Any, Any]] = []
    if isinstance(value, dict):
        entries = list(value.items())
    elif isinstance(value, list):
        for item in value:
            if not isinstance(item, dict):
                return {}, False
            entries.extend(item.items())
    else:
        return {}, False

    result: dict[str, int] = {}
    for raw_name, count in entries:
        if not isinstance(raw_name, str) or not valid_count(count):
            return {}, False
        result[raw_name] = result.get(raw_name, 0) + count
    return result, True


def percentile_nearest_rank(values: list[float], percentile: int) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(percentile * len(ordered) / 100))
    return round(ordered[rank - 1], 1)


def resolve_station_information(
    capture_dir: Path, capture: dict[str, Any]
) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    metadata = capture.get("feeds", {}).get("station_information", {})
    source = metadata.get("source_path")
    if isinstance(source, str):
        source_path = Path(source)
        if not source_path.is_absolute():
            source_path = PROJECT_ROOT / source_path
    else:
        # Early captures stored station_information.json in each capture folder.
        source_path = capture_dir / "station_information.json"
    info_payload = read_json(source_path)
    info_stations = stations_from(info_payload, "station_information")
    return source_path, info_payload, {"metadata": metadata, "stations": info_stations}


def bool_false(value: Any) -> bool:
    return value is False or (isinstance(value, int) and not isinstance(value, bool) and value == 0)


def bool_true(value: Any) -> bool:
    return value is True or (isinstance(value, int) and not isinstance(value, bool) and value == 1)


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        mode="w", encoding="utf-8", newline="", dir=path.parent, delete=False
    ) as handle:
        temp_path = Path(handle.name)
        handle.write(content)
    temp_path.replace(path)


def atomic_write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        mode="w", encoding="utf-8", newline="", dir=path.parent, delete=False
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        temp_path = Path(handle.name)
    temp_path.replace(path)


def analyze_capture(capture_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    capture_dir = capture_path.parent
    capture = read_json(capture_path)
    feeds = capture.get("feeds", {})
    status_metadata = feeds.get("station_status", {})
    discovery_metadata = feeds.get("gbfs", {})
    status_path = capture_dir / "station_status.json"
    status_body = status_path.read_bytes()
    status_payload = json.loads(status_body)
    if not isinstance(status_payload, dict):
        raise ValueError(f"station_status is not a JSON object: {status_path}")
    status_stations = stations_from(status_payload, "station_status")

    discovery_path = capture_dir / "gbfs.json"
    discovery_payload = read_json(discovery_path)
    observed_discovery_hash = hashlib.sha256(discovery_path.read_bytes()).hexdigest()
    discovery_hash_ok = observed_discovery_hash == discovery_metadata.get("body_sha256")
    source_path, info_payload, info = resolve_station_information(capture_dir, capture)
    info_metadata = info["metadata"]
    info_stations = info["stations"]

    observed_status_hash = hashlib.sha256(status_body).hexdigest()
    expected_status_hash = status_metadata.get("body_sha256")
    status_hash_ok = observed_status_hash == expected_status_hash
    info_hash_ok: bool | None = None
    if info_metadata.get("body_sha256"):
        info_hash_ok = hashlib.sha256(source_path.read_bytes()).hexdigest() == info_metadata[
            "body_sha256"
        ]

    status_ids = [station_key(row.get("station_id")) for row in status_stations]
    info_ids = [station_key(row.get("station_id")) for row in info_stations]
    status_id_set = {value for value in status_ids if value is not None}
    info_id_set = {value for value in info_ids if value is not None}
    status_by_id = {
        station_key(row.get("station_id")): row
        for row in status_stations
        if station_key(row.get("station_id")) is not None
    }
    info_by_id = {
        station_key(row.get("station_id")): row
        for row in info_stations
        if station_key(row.get("station_id")) is not None
    }

    retrieved_at = parse_time(status_metadata.get("retrieved_at_utc"))
    info_retrieved_at = parse_time(info_metadata.get("retrieved_at_utc"))
    info_age = (
        round((retrieved_at - info_retrieved_at).total_seconds(), 1)
        if retrieved_at and info_retrieved_at
        else None
    )

    fields: set[str] = set()
    info_fields: set[str] = set()
    rows_out: list[dict[str, Any]] = []
    report_ages: list[float] = []
    total_bikes = total_docks = mechanical = ebike = other_bikes = 0
    zero_bikes = zero_docks = 0
    false_renting = false_returning = false_installed = 0
    invalid_counts = type_total_mismatches = invalid_flags = 0
    bike_alias_mismatches = dock_alias_mismatches = 0
    missing_invalid_reported = future_reported = 0
    invalid_coordinates = invalid_capacity = 0
    distinct_reported: set[int] = set()
    for station in status_stations:
        fields.update(station.keys())
    for station in info_stations:
        info_fields.update(station.keys())

    for station in status_stations:
        sid = station_key(station.get("station_id"))
        info_row = info_by_id.get(sid, {})
        bikes = station.get("num_bikes_available")
        docks = station.get("num_docks_available")
        if valid_count(bikes):
            total_bikes += bikes
            zero_bikes += bikes == 0
        else:
            invalid_counts += 1
        if valid_count(docks):
            total_docks += docks
            zero_docks += docks == 0
        else:
            invalid_counts += 1

        breakdown, breakdown_valid = parse_type_breakdown(
            station.get("num_bikes_available_types")
        )
        if breakdown_valid:
            mechanical += breakdown.get("mechanical", 0)
            ebike += breakdown.get("ebike", 0)
            other_bikes += sum(
                count for name, count in breakdown.items() if name not in {"mechanical", "ebike"}
            )
            if valid_count(bikes) and sum(breakdown.values()) != bikes:
                type_total_mismatches += 1
        else:
            invalid_counts += 1

        if "numBikesAvailable" in station and bikes != station.get("numBikesAvailable"):
            bike_alias_mismatches += 1
        if "numDocksAvailable" in station and docks != station.get("numDocksAvailable"):
            dock_alias_mismatches += 1
        false_renting += bool_false(station.get("is_renting"))
        false_returning += bool_false(station.get("is_returning"))
        false_installed += bool_false(station.get("is_installed"))
        for flag in ("is_installed", "is_renting", "is_returning"):
            value = station.get(flag)
            invalid_flags += not (
                isinstance(value, bool)
                or (isinstance(value, int) and not isinstance(value, bool) and value in (0, 1))
            )

        reported = station.get("last_reported")
        report_time: datetime | None = None
        age_seconds: float | None = None
        if isinstance(reported, int) and not isinstance(reported, bool) and reported >= 0:
            distinct_reported.add(reported)
            try:
                report_time = datetime.fromtimestamp(reported, timezone.utc)
                if retrieved_at:
                    age_seconds = round((retrieved_at - report_time).total_seconds(), 1)
                    report_ages.append(age_seconds)
                    future_reported += age_seconds < 0
            except (OverflowError, OSError, ValueError):
                missing_invalid_reported += 1
        else:
            missing_invalid_reported += 1

        lat = info_row.get("lat")
        lon = info_row.get("lon")
        coord_ok = (
            isinstance(lat, (int, float))
            and not isinstance(lat, bool)
            and math.isfinite(lat)
            and -90 <= lat <= 90
            and isinstance(lon, (int, float))
            and not isinstance(lon, bool)
            and math.isfinite(lon)
            and -180 <= lon <= 180
        )
        invalid_coordinates += not coord_ok
        capacity = info_row.get("capacity")
        invalid_capacity += not valid_count(capacity)
        rows_out.append(
            {
                "capture_id": capture.get("capture_id"),
                "status_retrieved_at_utc": iso_utc(retrieved_at),
                "station_id": sid,
                "station_code": station.get("stationCode", info_row.get("stationCode")),
                "station_name": info_row.get("name"),
                "latitude": lat,
                "longitude": lon,
                "capacity": capacity,
                "mechanical_available": breakdown.get("mechanical") if breakdown_valid else None,
                "ebike_available": breakdown.get("ebike") if breakdown_valid else None,
                "other_bikes_available": sum(
                    count for name, count in breakdown.items() if name not in {"mechanical", "ebike"}
                ) if breakdown_valid else None,
                "bike_type_breakdown_json": json.dumps(
                    breakdown, sort_keys=True, separators=(",", ":")
                ) if breakdown_valid else None,
                "num_bikes_available": bikes,
                "num_docks_available": docks,
                "is_installed": station.get("is_installed"),
                "is_renting": station.get("is_renting"),
                "is_returning": station.get("is_returning"),
                "last_reported_epoch": reported if isinstance(reported, int) and not isinstance(reported, bool) else None,
                "last_reported_at_utc": iso_utc(report_time),
                "report_age_seconds": age_seconds,
                "station_information_source": source_path.relative_to(PROJECT_ROOT).as_posix()
                if source_path.is_relative_to(PROJECT_ROOT)
                else source_path.as_posix(),
            }
        )

    status_last_updated = status_payload.get("last_updated")
    discovery_languages = discovery_payload.get("data")
    top_level_feeds: list[dict[str, Any]] = []
    if isinstance(discovery_languages, dict):
        for language in discovery_languages.values():
            if isinstance(language, dict) and isinstance(language.get("feeds"), list):
                top_level_feeds = language["feeds"]
                break
    summary = {
        "capture_id": capture.get("capture_id"),
        "capture_started_at_utc": capture.get("capture_started_at_utc"),
        "status_retrieved_at_utc": iso_utc(retrieved_at),
        "interval_seconds_from_previous": None,
        "station_information_source": rows_out[0]["station_information_source"] if rows_out else None,
        "station_information_retrieved_at_utc": info_metadata.get("retrieved_at_utc"),
        "station_information_age_seconds": info_age,
        "station_information_record_count": len(info_stations),
        "station_information_http_status": info_metadata.get("http_status"),
        "station_information_sha256_ok": info_hash_ok,
        "discovery_body_sha256": observed_discovery_hash,
        "discovery_body_sha256_ok": discovery_hash_ok,
        "discovery_ttl_seconds": capture.get("discovery_ttl_seconds"),
        "discovery_http_status": discovery_metadata.get("http_status"),
        "discovery_top_level_version": discovery_payload.get("version"),
        "advertised_feed_names": ",".join(
            str(feed.get("name")) for feed in top_level_feeds if isinstance(feed, dict)
        ),
        "status_http_status": status_metadata.get("http_status"),
        "status_ttl_seconds": status_payload.get("ttl"),
        "status_last_updated": status_last_updated,
        "status_cache_control": status_metadata.get("cache_control"),
        "status_age_header": status_metadata.get("age"),
        "status_etag": status_metadata.get("etag"),
        "status_body_bytes": len(status_body),
        "status_body_sha256": observed_status_hash,
        "status_body_sha256_ok": status_hash_ok,
        "station_count": len(status_stations),
        "unique_station_id_count": len(status_id_set),
        "duplicate_station_id_count": len(status_stations) - len(status_id_set),
        "invalid_status_station_id_count": sum(value is None for value in status_ids),
        "duplicate_station_information_id_count": len(info_stations) - len(info_id_set),
        "invalid_station_information_id_count": sum(value is None for value in info_ids),
        "status_without_station_information_count": len(status_id_set - info_id_set),
        "station_information_without_status_count": len(info_id_set - status_id_set),
        "mechanical_available_total": mechanical,
        "ebike_available_total": ebike,
        "other_bikes_available_total": other_bikes,
        "num_bikes_available_total": total_bikes,
        "num_docks_available_total": total_docks,
        "zero_bike_station_count": zero_bikes,
        "zero_dock_station_count": zero_docks,
        "is_renting_false_count": false_renting,
        "is_returning_false_count": false_returning,
        "is_installed_false_count": false_installed,
        "invalid_operating_flag_field_count": invalid_flags,
        "invalid_or_negative_count_field_count": invalid_counts,
        "bike_type_total_mismatch_station_count": type_total_mismatches,
        "bike_alias_mismatch_station_count": bike_alias_mismatches,
        "dock_alias_mismatch_station_count": dock_alias_mismatches,
        "missing_or_invalid_last_reported_count": missing_invalid_reported,
        "future_last_reported_count": future_reported,
        "last_reported_distinct_timestamp_count": len(distinct_reported),
        "last_reported_age_min_seconds": round(min(report_ages), 1) if report_ages else None,
        "last_reported_age_p50_seconds": percentile_nearest_rank(report_ages, 50),
        "last_reported_age_p90_seconds": percentile_nearest_rank(report_ages, 90),
        "last_reported_age_p95_seconds": percentile_nearest_rank(report_ages, 95),
        "last_reported_age_p99_seconds": percentile_nearest_rank(report_ages, 99),
        "last_reported_age_max_seconds": round(max(report_ages), 1) if report_ages else None,
        "last_reported_older_than_5m_count": sum(age > 300 for age in report_ages),
        "last_reported_older_than_15m_count": sum(age > 900 for age in report_ages),
        "last_reported_older_than_1h_count": sum(age > 3600 for age in report_ages),
        "last_reported_older_than_24h_count": sum(age > 86400 for age in report_ages),
        "invalid_station_coordinate_count": invalid_coordinates,
        "invalid_station_capacity_count": invalid_capacity,
        "status_field_names": sorted(fields),
        "station_information_field_names": sorted(info_fields),
    }
    context = {
        "capture": capture,
        "stations_by_id": status_by_id,
        "status_hash": observed_status_hash,
        "status_id_set": status_id_set,
    }
    return summary, rows_out, context


def add_sequential_comparisons(
    summaries: list[dict[str, Any]], contexts: list[dict[str, Any]]
) -> None:
    for index, summary in enumerate(summaries):
        if index == 0:
            summary.update(
                {
                    "inventory_changed_station_count_from_previous": None,
                    "last_reported_changed_station_count_from_previous": None,
                    "inventory_and_timestamp_both_changed_station_count_from_previous": None,
                    "station_flag_changed_station_count_from_previous": None,
                    "status_body_same_as_previous": None,
                }
            )
            continue
        previous = summaries[index - 1]
        prior_context = contexts[index - 1]
        current_context = contexts[index]
        prior_time = parse_time(previous.get("status_retrieved_at_utc"))
        current_time = parse_time(summary.get("status_retrieved_at_utc"))
        if prior_time and current_time:
            summary["interval_seconds_from_previous"] = round(
                (current_time - prior_time).total_seconds(), 1
            )
        prior = prior_context["stations_by_id"]
        current = current_context["stations_by_id"]
        common = set(prior) & set(current)
        inventory_changed = 0
        timestamps_changed = 0
        both_changed = 0
        flags_changed = 0
        for key in common:
            old, new = prior[key], current[key]
            old_inventory = (old.get("num_bikes_available"), old.get("num_docks_available"))
            new_inventory = (new.get("num_bikes_available"), new.get("num_docks_available"))
            inventory_diff = old_inventory != new_inventory
            timestamp_diff = old.get("last_reported") != new.get("last_reported")
            flag_diff = any(
                old.get(flag) != new.get(flag)
                for flag in ("is_installed", "is_renting", "is_returning")
            )
            inventory_changed += inventory_diff
            timestamps_changed += timestamp_diff
            both_changed += inventory_diff and timestamp_diff
            flags_changed += flag_diff
        summary.update(
            {
                "inventory_changed_station_count_from_previous": inventory_changed,
                "last_reported_changed_station_count_from_previous": timestamps_changed,
                "inventory_and_timestamp_both_changed_station_count_from_previous": both_changed,
                "station_flag_changed_station_count_from_previous": flags_changed,
                "status_body_same_as_previous": prior_context["status_hash"]
                == current_context["status_hash"],
            }
        )


def run_audit(input_dir: Path, output_dir: Path) -> dict[str, Any]:
    capture_paths = sorted(input_dir.rglob("capture.json"))
    if not capture_paths:
        raise FileNotFoundError(f"No capture.json files found below {input_dir}")

    analyzed = [analyze_capture(path) for path in capture_paths]
    analyzed.sort(key=lambda item: item[0].get("status_retrieved_at_utc") or "")
    summaries = [item[0] for item in analyzed]
    station_rows = [row for item in analyzed for row in item[1]]
    contexts = [item[2] for item in analyzed]
    add_sequential_comparisons(summaries, contexts)

    all_status_hashes_ok = all(row["status_body_sha256_ok"] for row in summaries)
    all_discovery_hashes_ok = all(row["discovery_body_sha256_ok"] for row in summaries)
    info_hash_results = [row["station_information_sha256_ok"] for row in summaries]
    all_info_hashes_ok = all(value is True for value in info_hash_results)
    all_ids_unique = all(row["duplicate_station_id_count"] == 0 for row in summaries)
    all_ids_valid = all(
        row["invalid_status_station_id_count"] == 0
        and row["duplicate_station_information_id_count"] == 0
        and row["invalid_station_information_id_count"] == 0
        for row in summaries
    )
    all_ids_match = all(
        row["status_without_station_information_count"] == 0
        and row["station_information_without_status_count"] == 0
        for row in summaries
    )
    all_type_totals_reconcile = all(
        row["bike_type_total_mismatch_station_count"] == 0 for row in summaries
    )
    all_aliases_reconcile = all(
        row["bike_alias_mismatch_station_count"] == 0
        and row["dock_alias_mismatch_station_count"] == 0
        for row in summaries
    )
    all_counts_valid = all(
        row["invalid_or_negative_count_field_count"] == 0 for row in summaries
    )
    all_flags_valid = all(row["invalid_operating_flag_field_count"] == 0 for row in summaries)

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
            "+00:00", "Z"
        ),
        "command": "python -m velib_lab.audit --input-dir data/raw --output-dir data/processed",
        "input_directory": input_dir.as_posix(),
        "output_directory": output_dir.as_posix(),
        "capture_count": len(summaries),
        "first_status_retrieved_at_utc": summaries[0]["status_retrieved_at_utc"],
        "last_status_retrieved_at_utc": summaries[-1]["status_retrieved_at_utc"],
        "distinct_status_payload_hashes": len({row["status_body_sha256"] for row in summaries}),
        "validation": {
            "all_status_body_hashes_match_capture_metadata": all_status_hashes_ok,
            "all_discovery_body_hashes_match_capture_metadata": all_discovery_hashes_ok,
            "all_station_information_hashes_match_metadata": all_info_hashes_ok,
            "all_station_ids_unique_within_snapshot": all_ids_unique,
            "all_station_ids_valid_and_information_ids_unique": all_ids_valid,
            "all_status_ids_join_to_station_information_and_back": all_ids_match,
            "all_bike_type_totals_match_total_bikes": all_type_totals_reconcile,
            "all_camel_case_count_aliases_match_snake_case": all_aliases_reconcile,
            "no_invalid_or_negative_bike_or_dock_counts": all_counts_valid,
            "all_operating_flags_are_boolean_or_zero_one": all_flags_valid,
        },
        "status_field_names_union": sorted(
            {name for row in summaries for name in row["status_field_names"]}
        ),
        "station_information_field_names_union": sorted(
            {name for row in summaries for name in row["station_information_field_names"]}
        ),
        "captures": summaries,
    }

    summary_fields = [
        key for key in summaries[0]
        if key not in {"status_field_names", "station_information_field_names"}
    ]
    station_fields = [
        "capture_id", "status_retrieved_at_utc", "station_id", "station_code",
        "station_name", "latitude", "longitude", "capacity", "mechanical_available",
        "ebike_available", "other_bikes_available", "bike_type_breakdown_json",
        "num_bikes_available", "num_docks_available", "is_installed", "is_renting",
        "is_returning", "last_reported_epoch", "last_reported_at_utc",
        "report_age_seconds", "station_information_source",
    ]
    atomic_write_csv(output_dir / "capture_summary.csv", summaries, summary_fields)
    atomic_write_csv(output_dir / "station_snapshots.csv", station_rows, station_fields)
    atomic_write_text(
        output_dir / "audit_report.json",
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate captured Vélib GBFS snapshots and write local analysis files."
    )
    parser.add_argument("--input-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed"))
    args = parser.parse_args()
    report = run_audit(args.input_dir, args.output_dir)
    print(
        f"Audited {report['capture_count']} captures; "
        f"{report['distinct_status_payload_hashes']} distinct status payloads."
    )
    print(f"Station-time rows: {report['capture_count'] and sum(row['station_count'] for row in report['captures']):,}")
    print(f"Outputs: {args.output_dir / 'capture_summary.csv'}")
    print(f"         {args.output_dir / 'station_snapshots.csv'}")
    print(f"         {args.output_dir / 'audit_report.json'}")


if __name__ == "__main__":
    main()

