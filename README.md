# Fruit API

A small Python REST API built with **FastAPI** and **MongoDB**. Every valid fruit
request fetches fresh data from [Fruityvice](https://www.fruityvice.com/api/fruit/all).
There is no frontend and no fruit cache.

## Requirements

- Python 3.11 or newer
- MongoDB Community Server (or Docker Desktop to run the included MongoDB service)
- Internet access to Fruityvice
- Postman to import and run the supplied collection

## Run on Windows

Open this folder in VS Code. In a terminal, create the Python environment **beside**
the project, so it stays out of the submission and GitHub repository:

```powershell
py -3.11 -m venv ..\fruit-api-env
..\fruit-api-env\Scripts\python.exe -m pip install -r requirements.txt
```

Start your installed MongoDB server on `127.0.0.1:27017`. Alternatively, with Docker
Desktop running, execute this command from the project folder:

```powershell
docker compose up -d
```

Then start the API:

```powershell
..\fruit-api-env\Scripts\python.exe run.py
```

The API runs at **http://localhost:4000**. Interactive API documentation is at
[http://localhost:4000/docs](http://localhost:4000/docs).
The `.vscode/launch.json` configuration also supports debugging with F5 after
selecting your Python interpreter in VS Code.

To connect to another MongoDB server, set `MONGO_URI` in the terminal before starting
the application. The database and collection names remain `logs_db` and `logs`.

## Routes

| Method | Route | Response |
| --- | --- | --- |
| GET | `/api/fruits` | The complete upstream fruit array, with all fields and ordering preserved |
| GET | `/api/search/{text}` | Fruit names containing `text`, ignoring case |
| GET | `/api/calories/{max}` | Fruits whose `nutritions.calories` is less than or equal to `max` |

Examples: `/api/search/app`, `/api/search/aPp`, `/api/calories/25`.
No matches produce `[]`. Decimal calorie limits are supported; negative limits
normally produce `[]`. Non-numeric or infinite limits return HTTP 422.
Fruityvice data can change, so the assignment's example fruit lists are not hardcoded.

Upstream errors or malformed data return HTTP 502; timeouts return 504.
If MongoDB cannot be reached at startup, the server fails to start with a clear
connection error. If writing a request log fails later, the API returns 503.
Requests cannot be persisted while the database itself is unavailable.

## Request logs

Every request is recorded in `logs_db.logs`, including empty results, invalid paths,
validation errors, unsupported methods and documentation requests.

| Field | Meaning |
| --- | --- |
| `method` | Actual HTTP method |
| `route` | Full request path with actual route parameters, plus query string if present |
| `total_results` | Number of fruit objects returned; 0 for errors or non-fruit responses |
| `client_ip` | Connected client's IP address |
| `created_at` | Request arrival time, stored as a MongoDB UTC date |

MongoDB also creates its standard `_id` field. Proxy headers are not trusted by the
provided launcher, so callers cannot change the recorded IP by supplying a header.

## Tests and Postman

Install the development requirements and run the deterministic tests:

```powershell
..\fruit-api-env\Scripts\python.exe -m pip install -r requirements-dev.txt
..\fruit-api-env\Scripts\python.exe -m pytest -q
..\fruit-api-env\Scripts\python.exe -m ruff check .
```

With the API and MongoDB running, verify live responses and their database logs:

```powershell
..\fruit-api-env\Scripts\python.exe scripts\verify_live.py
```

In Postman, import `postman/Fruit_API.postman_collection.json`. Run the complete
collection in its existing order, using the collection variable
`base_url = http://localhost:4000`. The first request supplies the reference array
for subsequent search and calorie assertions. The collection contains 10 requests
and 21 assertions. No authentication or API key is needed.

It can also be run using **Newman, Postman's official command-line collection runner**:

```powershell
npx newman run postman/Fruit_API.postman_collection.json
```

Actual live HTTP/database results and Newman execution results are saved in
`verification/`. See `verification/README.md` for the scope of the checks.

## Database exports and restoration

The submission includes exports of **real request logs**, not sample records:

- `database/logs.json`: MongoDB Extended JSON, preserving IDs and dates.
- `database/dump/logs_db/`: native `mongodump` BSON and collection metadata.

The app creates its collection automatically; importing old logs is optional for
normal operation. To import the JSON export into an **empty** `logs_db.logs`:

```powershell
..\fruit-api-env\Scripts\python.exe scripts\import_database.py
```

The importer stops if records already exist, preserving existing data. Alternatively,
with MongoDB Database Tools installed and the destination collection empty:

```powershell
mongorestore --uri mongodb://127.0.0.1:27017 --nsInclude "logs_db.*" database/dump
```

To refresh the JSON export after making more requests:

```powershell
..\fruit-api-env\Scripts\python.exe scripts\export_database.py
```

To refresh the native export:

```powershell
mongodump --uri mongodb://127.0.0.1:27017 --db logs_db --out database/dump
```

## Project layout

```text
fruit-api/
  app/                Configuration, upstream client, routes and request logging
  database/           JSON and native MongoDB exports
  postman/            Exported Postman collection
  scripts/            Live verification and database export/import
  tests/              Deterministic automated tests
  verification/       Results of executed checks
  .vscode/            VS Code debugging configuration
  compose.yaml        Optional local MongoDB container
  requirements.txt    Runtime dependencies
  requirements-dev.txt
  run.py              Server entry point (port 4000)
```

## Submission and GitHub

The course requires **one ZIP of the project**, including the database and Postman
exports, with no virtual environment folder. Upload that ZIP to the assignment tab
on the course website. The ZIP is prepared beside the project folder.

GitHub is optional in the assignment. This folder is ready to upload as a repository:
`.gitignore` excludes environments, secrets, caches and local database files, while
keeping the required database exports. No student name or credentials are required.
