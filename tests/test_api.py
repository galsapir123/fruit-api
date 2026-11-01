"""Deterministic checks; no live service or database is needed for these tests."""

from copy import deepcopy
from datetime import datetime
from unittest.mock import MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient
from pymongo.errors import AutoReconnect

from app import main

FRUITS = [
    {"name": "Apple", "id": 1, "nutritions": {"calories": 52}, "extra": "preserved"},
    {"name": "Pineapple", "id": 2, "nutritions": {"calories": 50}},
    {"name": "GreenApple", "id": 3, "nutritions": {"calories": 21}},
    {"name": "Lime", "id": 4, "nutritions": {"calories": 25}},
]


@pytest.fixture
def api(monkeypatch):
    logs = []
    database = MagicMock()
    database.list_collection_names.return_value = ["logs"]
    collection = database.__getitem__.return_value
    collection.insert_one.side_effect = lambda entry: logs.append(deepcopy(entry))
    mongo = MagicMock()
    mongo.__enter__.return_value = mongo
    mongo.__getitem__.return_value = database
    monkeypatch.setattr(main, "MongoClient", lambda *args, **kwargs: mongo)
    upstream = MagicMock(return_value=httpx.Response(200, json=FRUITS))
    real_client = httpx.Client
    monkeypatch.setattr(
        main.httpx,
        "Client",
        lambda **kwargs: real_client(transport=httpx.MockTransport(upstream)),
    )
    with TestClient(main.app) as client:
        yield client, logs, upstream, collection


@pytest.mark.parametrize(
    "route,expected",
    [
        ("/api/fruits", FRUITS),
        ("/api/search/app", FRUITS[:3]),
        ("/api/search/aPp", FRUITS[:3]),
        ("/api/search/LIME", FRUITS[3:]),
        ("/api/search/no-such-fruit", []),
        ("/api/calories/25", FRUITS[2:]),
        ("/api/calories/24.9", FRUITS[2:3]),
        ("/api/calories/-1", []),
        ("/api/calories/1000", FRUITS),
    ],
)
def test_routes_and_logs(api, route, expected):
    client, logs, upstream, _ = api
    response = client.get(route)
    assert response.status_code == 200
    assert response.json() == expected
    assert upstream.call_count == 1
    assert str(upstream.call_args.args[0].url) == main.httpx.URL(
        "https://www.fruityvice.com/api/fruit/all"
    )
    assert len(logs) == 1
    assert logs[0] == {
        "method": "GET",
        "route": route,
        "total_results": len(expected),
        "client_ip": "testclient",
        "created_at": logs[0]["created_at"],
    }
    assert isinstance(logs[0]["created_at"], datetime)
    assert logs[0]["created_at"].utcoffset().total_seconds() == 0


def test_each_request_fetches_fresh_data(api):
    client, logs, upstream, _ = api
    client.get("/api/fruits")
    upstream.return_value = httpx.Response(200, json=[])
    assert client.get("/api/fruits").json() == []
    assert upstream.call_count == 2
    assert [entry["total_results"] for entry in logs] == [4, 0]


@pytest.mark.parametrize("limit", ["hello", "NaN", "inf", "-inf"])
def test_invalid_calorie_limit_is_logged(api, limit):
    client, logs, upstream, _ = api
    assert client.get(f"/api/calories/{limit}").status_code == 422
    assert logs[0]["total_results"] == 0
    upstream.assert_not_called()


@pytest.mark.parametrize(
    "upstream_response",
    [
        httpx.Response(500),
        httpx.Response(200, text="not JSON"),
        httpx.Response(200, json={}),
        httpx.Response(200, json=[{"name": "Broken"}]),
    ],
)
def test_upstream_errors_are_logged(api, upstream_response):
    client, logs, upstream, _ = api
    upstream.return_value = upstream_response
    assert client.get("/api/fruits").status_code == 502
    assert logs[0]["total_results"] == 0


def test_upstream_timeout(api):
    client, logs, upstream, _ = api
    upstream.side_effect = httpx.ReadTimeout("timeout")
    assert client.get("/api/fruits").status_code == 504
    assert logs[0]["total_results"] == 0


@pytest.mark.parametrize(
    "method,route,status",
    [
        ("GET", "/missing", 404),
        ("POST", "/api/fruits", 405),
        ("GET", "/docs", 200),
        ("GET", "/api/search/Lime?example=1", 200),
    ],
)
def test_every_request_is_logged(api, method, route, status):
    client, logs, _, _ = api
    assert client.request(method, route).status_code == status
    assert logs[0]["method"] == method
    assert logs[0]["route"] == route


def test_database_failure_is_not_silently_ignored(api):
    client, _, _, collection = api
    collection.insert_one.side_effect = AutoReconnect("database unavailable")
    assert client.get("/api/fruits").status_code == 503


def test_unexpected_error_is_logged(api):
    client, logs, upstream, _ = api
    upstream.side_effect = RuntimeError("unexpected")
    assert client.get("/api/fruits").status_code == 500
    assert logs[0]["total_results"] == 0
