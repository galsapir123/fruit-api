"""Small, explicit application settings."""

import os

MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017")
DATABASE_NAME = "logs_db"
COLLECTION_NAME = "logs"
FRUITS_URL = "https://www.fruityvice.com/api/fruit/all"
