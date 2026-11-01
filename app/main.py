"""Application startup and request logging."""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from starlette.concurrency import run_in_threadpool

from app.config import COLLECTION_NAME, DATABASE_NAME, MONGO_URI
from app.routes import router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    with MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000, timeoutMS=5000) as mongo:
        mongo.admin.command("ping")  # Fail clearly at startup if MongoDB is unavailable.
        database = mongo[DATABASE_NAME]
        if COLLECTION_NAME not in database.list_collection_names():
            database.create_collection(COLLECTION_NAME)
        app.state.logs = database[COLLECTION_NAME]
        with httpx.Client(timeout=15.0, follow_redirects=True) as client:
            app.state.http = client
            yield


app = FastAPI(
    title="Fruit API",
    description="Fresh Fruityvice data with request logging in MongoDB.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def log_request(request: Request, call_next):
    """Log every request, including validation errors, 404s and documentation."""
    created_at = datetime.now(timezone.utc)
    request.state.total_results = 0
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("Unexpected request failure")
        response = JSONResponse(status_code=500, content={"detail": "Internal server error."})

    route = request.url.path
    if request.url.query:
        route += "?" + request.url.query
    entry = {
        "method": request.method,
        "route": route,
        "total_results": request.state.total_results if response.status_code < 400 else 0,
        "client_ip": request.client.host if request.client else "unknown",
        "created_at": created_at,
    }
    try:
        # Persist before sending the response. Never silently drop a log.
        await run_in_threadpool(request.app.state.logs.insert_one, entry)
    except PyMongoError:
        logger.exception("Could not save the request log")
        return JSONResponse(status_code=503, content={"detail": "Request logging is unavailable."})
    return response


app.include_router(router)
