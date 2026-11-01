"""Restore the JSON export into an empty logs collection without deleting data."""

import os
from pathlib import Path

from bson import json_util
from pymongo import MongoClient

source = Path(__file__).resolve().parents[1] / "database" / "logs.json"
records = json_util.loads(source.read_text(encoding="utf-8"))
with MongoClient(os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017")) as mongo:
    logs = mongo.logs_db.logs
    if logs.count_documents({}):
        raise SystemExit("Restore stopped: logs_db.logs must be empty. Existing data was kept.")
    if records:
        logs.insert_many(records)
print(f"Imported {len(records)} log records into logs_db.logs.")
