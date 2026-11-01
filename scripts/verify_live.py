"""Verify real HTTP responses and their persisted MongoDB logs."""

import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
from pymongo import MongoClient

BASE_URL = "http://127.0.0.1:4000"
ROOT = Path(__file__).resolve().parents[1]


def main():
    checks = []
    with (
        httpx.Client(timeout=30) as http,
        MongoClient("mongodb://127.0.0.1:27017", tz_aware=True) as mongo,
    ):
        logs = mongo.logs_db.logs
        reference_response = http.get("https://www.fruityvice.com/api/fruit/all")
        reference_response.raise_for_status()
        reference = reference_response.json()
        cases = [
            ("/api/fruits", reference),
            (
                "/api/search/app",
                [f for f in reference if "app" in f["name"].casefold()],
            ),
            (
                "/api/search/aPp",
                [f for f in reference if "app" in f["name"].casefold()],
            ),
            ("/api/search/no-such-fruit-xyz", []),
            (
                "/api/calories/25",
                [f for f in reference if f["nutritions"]["calories"] <= 25],
            ),
            (
                "/api/calories/24.9",
                [f for f in reference if f["nutritions"]["calories"] <= 24.9],
            ),
            ("/api/calories/-1", []),
        ]
        for route, expected in cases:
            started = datetime.now(timezone.utc)
            response = http.get(BASE_URL + route)
            assert response.status_code == 200, (route, response.text)
            assert response.json() == expected, route
            log = logs.find_one({"route": route, "created_at": {"$gte": started}})
            assert log is not None, route
            assert log["method"] == "GET"
            assert log["total_results"] == len(expected)
            assert log["client_ip"] == "127.0.0.1"
            assert isinstance(log["created_at"], datetime)
            checks.append(
                {
                    "route": route,
                    "status": 200,
                    "total_results": len(expected),
                    "database_log_verified": True,
                }
            )
        for route, status in [("/api/calories/invalid", 422), ("/not-found", 404)]:
            started = datetime.now(timezone.utc)
            assert http.get(BASE_URL + route).status_code == status
            log = logs.find_one({"route": route, "created_at": {"$gte": started}})
            assert log and log["total_results"] == 0
            checks.append({"route": route, "status": status, "database_log_verified": True})

    report = {
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "Live Fruityvice API and real local MongoDB",
        "checks": checks,
    }
    output = ROOT / "verification" / "live-results.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"All {len(checks)} live HTTP and database checks passed.")


if __name__ == "__main__":
    main()
