"""Fetch fresh fruit data without changing the upstream objects."""

import math

import httpx
from fastapi import HTTPException

from app.config import FRUITS_URL


def fetch_fruits(client: httpx.Client) -> list[dict]:
    """Each invocation makes one request to Fruityvice; nothing is cached."""
    try:
        response = client.get(FRUITS_URL)
        response.raise_for_status()
        fruits = response.json()
    except httpx.TimeoutException as exc:
        raise HTTPException(504, "Fruityvice timed out. Please try again.") from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(502, "Could not retrieve valid data from Fruityvice.") from exc

    # Validate only what the routes need, preserving every original field.
    if not isinstance(fruits, list) or not all(is_valid_fruit(fruit) for fruit in fruits):
        raise HTTPException(502, "Fruityvice returned an unexpected data format.")
    return fruits


def is_valid_fruit(fruit: object) -> bool:
    if not isinstance(fruit, dict) or not isinstance(fruit.get("name"), str):
        return False
    nutritions = fruit.get("nutritions")
    if not isinstance(nutritions, dict):
        return False
    calories = nutritions.get("calories")
    return (
        isinstance(calories, (int, float))
        and not isinstance(calories, bool)
        and math.isfinite(calories)
    )
