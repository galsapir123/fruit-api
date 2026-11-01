"""Export real MongoDB documents as portable Extended JSON."""

import os
from pathlib import Path

from bson import json_util
from pymongo import MongoClient

destination = Path(__file__).resolve().parents[1] / "database" / "logs.json"
destination.parent.mkdir(exist_ok=True)
with MongoClient(os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017")) as mongo:
    records = list(mongo.logs_db.logs.find().sort("_id", 1))
destination.write_text(json_util.dumps(records, indent=2) + "\n", encoding="utf-8")
print(f"Exported {len(records)} real log records to {destination}")
