"""The three fruit endpoints required by the assignment."""

from typing import Annotated

from fastapi import APIRouter, Path, Request

from app.fruityvice import fetch_fruits

router = APIRouter(prefix="/api", tags=["Fruits"])


def result(request: Request, fruits: list[dict]) -> list[dict]:
    request.state.total_results = len(fruits)
    return fruits


@router.get("/fruits", summary="Get all fruits")
def all_fruits(request: Request) -> list[dict]:
    return result(request, fetch_fruits(request.app.state.http))


@router.get("/search/{text}", summary="Search fruit names, ignoring case")
def search_fruits(request: Request, text: str) -> list[dict]:
    fruits = fetch_fruits(request.app.state.http)
    matches = [fruit for fruit in fruits if text.casefold() in fruit["name"].casefold()]
    return result(request, matches)


@router.get("/calories/{max}", summary="Get fruits at or below a calorie limit")
def low_calorie_fruits(
    request: Request,
    max: Annotated[float, Path(allow_inf_nan=False, description="Inclusive calorie limit")],
) -> list[dict]:
    fruits = fetch_fruits(request.app.state.http)
    matches = [fruit for fruit in fruits if fruit["nutritions"]["calories"] <= max]
    return result(request, matches)
