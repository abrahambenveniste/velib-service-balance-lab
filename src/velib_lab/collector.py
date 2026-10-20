"""Capture raw Vélib GBFS snapshots with enough metadata to audit freshness."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import httpx


DISCOVERY_URL = (
    "https://velib-metropole-opendata.smovengo.cloud/"
    "opendata/Velib_Metropole/gbfs.json"
)
USER_AGENT = "velib-service-balance-lab/0.1 (+https://github.com/)"
REQUIRED_FEEDS = ("station_information", "station_status")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(value: datetime) -> str:
    return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def fetch_json(client: httpx.Client, url: str) -> tuple[bytes, dict[str, Any]]:
    response = client.get(url)
    response.raise_for_status()
    body = response.content
    # Parse before persisting so an HTML error page or malformed JSON is not
    # mistaken for a valid feed capture.
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object from {url}")
    headers = response.headers
    return body, {
        "url": url,
        "http_status": response.status_code,
        "retrieved_at_utc": iso_utc(utc_now()),
        "body_sha256": hashlib.sha256(body).hexdigest(),
        "content_type": headers.get("content-type"),
        "cache_control": headers.get("cache-control"),
        "age": headers.get("age"),
        "etag": headers.get("etag"),
        "payload": payload,
    }


def advertised_feeds(discovery: dict[str, Any]) -> tuple[int | None, dict[str, str]]:
    ttl = discovery.get("ttl")
    languages = discovery.get("data")
    if not isinstance(languages, dict) or not languages:
        raise ValueError("GBFS discovery response has no language/feed data")

    feeds_by_name: dict[str, str] = {}
    for language in languages.values():
        if not isinstance(language, dict):
            continue
        feeds = language.get("feeds", [])
        if not isinstance(feeds, list):
            continue
        for feed in feeds:
            if isinstance(feed, dict) and feed.get("name") and feed.get("url"):
                feeds_by_name[str(feed["name"])] = str(feed["url"])
        if all(name in feeds_by_name for name in REQUIRED_FEEDS):
            break

    missing = [name for name in REQUIRED_FEEDS if name not in feeds_by_name]
    if missing:
        raise ValueError(f"Discovery feed is missing required feeds: {', '.join(missing)}")
    return (int(ttl) if isinstance(ttl, int) else None), feeds_by_name


def station_record_count(payload: dict[str, Any]) -> int | None:
    data = payload.get("data")
    stations = data.get("stations") if isinstance(data, dict) else None
    return len(stations) if isinstance(stations, list) else None


def station_timestamp_summary(
    payload: dict[str, Any], retrieved_at: datetime
) -> dict[str, Any]:
    data = payload.get("data")
    stations = data.get("stations") if isinstance(data, dict) else None
    if not isinstance(stations, list):
        return {"timestamp_count": 0, "timestamp_missing_or_invalid": None}

    timestamps = [
        station["last_reported"]
        for station in stations
        if isinstance(station, dict)
        and isinstance(station.get("last_reported"), int)
        and not isinstance(station.get("last_reported"), bool)
    ]
    if not timestamps:
        return {
            "timestamp_count": 0,
            "timestamp_missing_or_invalid": len(stations),
            "oldest_reported_at_utc": None,
            "newest_reported_at_utc": None,
            "oldest_report_age_seconds": None,
            "newest_report_age_seconds": None,
            "distinct_report_timestamps": 0,
        }

    oldest = min(timestamps)
    newest = max(timestamps)
    oldest_at = datetime.fromtimestamp(oldest, tz=timezone.utc)
    newest_at = datetime.fromtimestamp(newest, tz=timezone.utc)
    return {
        "timestamp_count": len(timestamps),
        "timestamp_missing_or_invalid": len(stations) - len(timestamps),
        "oldest_reported_at_utc": iso_utc(oldest_at),
        "newest_reported_at_utc": iso_utc(newest_at),
        "oldest_report_age_seconds": round((retrieved_at - oldest_at).total_seconds(), 1),
        "newest_report_age_seconds": round((retrieved_at - newest_at).total_seconds(), 1),
        "distinct_report_timestamps": len(set(timestamps)),
    }


def capture_once(output_dir: Path, timeout_seconds: float) -> Path:
    started = utc_now()
    capture_id = started.strftime("%Y%m%dT%H%M%S") + f"{started.microsecond:06d}Z"
    requests: dict[str, dict[str, Any]] = {}
    raw: dict[str, bytes] = {}

    with httpx.Client(
        timeout=httpx.Timeout(timeout_seconds),
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    ) as client:
        body, discovery_request = fetch_json(client, DISCOVERY_URL)
        discovery_payload = discovery_request.pop("payload")
        raw["gbfs.json"] = body
        requests["gbfs"] = discovery_request
        ttl, feeds = advertised_feeds(discovery_payload)

        for feed_name in REQUIRED_FEEDS:
            body, request = fetch_json(client, feeds[feed_name])
            payload = request.pop("payload")
            raw[f"{feed_name}.json"] = body
            feed_metadata = {
                **request,
                "record_count": station_record_count(payload),
                "feed_last_updated": payload.get("last_updated"),
                "feed_ttl": payload.get("ttl"),
            }
            if feed_name == "station_status":
                retrieved_at = datetime.fromisoformat(
                    request["retrieved_at_utc"].replace("Z", "+00:00")
                )
                feed_metadata["station_report_timestamps"] = station_timestamp_summary(
                    payload, retrieved_at
                )
            requests[feed_name] = feed_metadata

    finished = utc_now()
    metadata = {
        "capture_id": capture_id,
        "collector_version": "0.1.0",
        "capture_started_at_utc": iso_utc(started),
        "capture_finished_at_utc": iso_utc(finished),
        "discovery_ttl_seconds": ttl,
        "feeds": requests,
        "notes": [
            "Raw feed bodies are preserved; record counts are descriptive only.",
            "A captured snapshot is not a trip record and cannot identify why inventory changed.",
        ],
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    final_dir = output_dir / started.strftime("%Y-%m-%d") / capture_id
    final_dir.parent.mkdir(parents=True, exist_ok=True)
    if final_dir.exists():
        raise FileExistsError(f"Capture directory already exists: {final_dir}")
    with TemporaryDirectory(prefix=f".{capture_id}-", dir=final_dir.parent) as temp_name:
        temp_dir = Path(temp_name)
        for filename, body in raw.items():
            (temp_dir / filename).write_bytes(body)
        (temp_dir / "capture.json").write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        temp_dir.replace(final_dir)
    return final_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture Vélib station-information and station-status GBFS feeds."
    )
    parser.add_argument("--output-dir", type=Path, default=Path("data/raw"))
    parser.add_argument(
        "--once", action="store_true", help="capture once, then exit (recommended initially)"
    )
    parser.add_argument(
        "--interval-seconds",
        type=float,
        default=300,
        help="pause between captures in continuous mode (default: 300)",
    )
    parser.add_argument("--timeout-seconds", type=float, default=20)
    args = parser.parse_args()
    if args.interval_seconds <= 0 or args.timeout_seconds <= 0:
        parser.error("interval and timeout must be positive")
    return args


def main() -> None:
    args = parse_args()
    while True:
        path = capture_once(args.output_dir, args.timeout_seconds)
        print(path.as_posix(), flush=True)
        if args.once:
            return
        time.sleep(args.interval_seconds)


if __name__ == "__main__":
    main()
