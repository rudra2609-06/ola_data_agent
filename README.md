# Ola Data Analyst

Ola Data Analyst is a web application that lets you upload a CSV file, ask a question about its contents in plain English, and receive a concise answer with the SQL query used to produce it. The API is built with FastAPI; LangGraph coordinates the LLM workflow, and PostgreSQL stores uploaded data and upload metadata.

## Project links

- **Deployment:** https://ola-data-agent.onrender.com
- **Video explanation:** [Watch the walkthrough](https://drive.google.com/file/d/19PhlvCMoktrnfhVOJY5bUCO8ehTGAp8L/view?usp=drive_link)

## Features

- Upload a CSV file up to 10 MB.
- Ask questions in natural language (up to 1,000 characters).
- Generate a PostgreSQL `SELECT` query using the uploaded file's schema and sample rows as context.
- Ask an LLM-based guard to judge whether the generated query is safe before execution.
- Return a short, plain-language answer and the generated SQL.
- Automatically drop expired upload tables.

## How it works

1. The browser sends the CSV to `POST /sql-analyst/upload`.
2. The API parses the CSV, creates a uniquely named table in PostgreSQL, imports the rows, and stores the table name and schema/sample context against an upload ID.
3. The browser sends the upload ID and question to `POST /sql-analyst/ask`.
4. The LangGraph agent rewrites the question, generates SQL using the supplied context, and asks an LLM safety guard to judge the SQL.
5. If the guard approves it, the query is executed and its results are summarized. Otherwise, execution is skipped and a cancellation message is returned.

Uploaded-table metadata is assigned an eight-hour expiration. The application runs cleanup at startup and schedules a daily cleanup job for 10:00 according to the host's local time; the cleanup routine drops expired upload tables.

## Technology

- Python 3.14 or newer
- FastAPI and Uvicorn (through `fastapi[standard]`)
- LangGraph and LangChain
- Google Gemini models through `langchain-google-genai`
- PostgreSQL, Psycopg 2/3, and SQLModel
- Pandas for CSV parsing
- APScheduler for expired-table cleanup
- A lightweight HTML, CSS, and JavaScript frontend served by FastAPI
- `uv` for Python dependency and environment management

## Repository layout

```text
.
├── agents/
│   └── sql_analyst_agent.py    # LangGraph question-to-SQL workflow
├── data/                       # Example CSV datasets
├── models/
│   └── schema.py               # Agent state, request, and upload metadata models
├── routers/
│   └── sql_analyst_router.py   # CSV upload and question-answer API endpoints
├── ui/
│   └── index.html              # Browser interface served at /
├── utils/
│   ├── cleanup.py              # Expired upload table cleanup
│   ├── db.py                   # PostgreSQL operations and schema context collection
│   ├── db_connection.py        # SQLModel engine and upload metadata table setup
│   └── pick_appropriate_llm.py # Gemini model selection
├── main.py                     # FastAPI app and lifecycle setup
├── pyproject.toml              # Project metadata and dependencies
├── uv.lock                     # Locked dependency versions
└── .python-version             # Preferred Python version (3.14)
```

## Example datasets

The `data/` directory contains sample files you can upload through the UI. They are **not** loaded automatically when the app starts.

| File | Example columns |
| --- | --- |
| `payments.csv` | `payment_id`, `ride_id`, `user_id`, `amount`, `payment_method`, `payment_status`, `transaction_id`, `payment_time` |
| `ratings.csv` | `rating_id`, `ride_id`, `rider_id`, `driver_id`, `rating`, `comment`, `rated_at` |
| `rides.csv` | `ride_id`, `rider_id`, `driver_id`, `requested_at`, `pickup_time`, `dropoff_time`, `distance_km`, `fare`, `surge_multiplier`, `status` |
| `users.csv` | `user_id`, `first_name`, `last_name`, `email`, `phone`, `city`, `province`, `user_type`, `signup_date`, `is_active` |
| `vehicles.csv` | `vehicle_id`, `driver_id`, `make`, `model`, `year`, `license_plate`, `color`, `is_active` |

## Run locally

### Prerequisites

- Python 3.14 or newer
- [`uv`](https://docs.astral.sh/uv/)
- A reachable PostgreSQL database and permission to create tables, insert CSV rows, and remove expired upload tables
- A Google Gemini API key with access to the models configured by the application

### Install dependencies

```bash
git clone https://github.com/rudra2609-06/ola_data_agent.git
cd ola_data_agent
uv sync
```

If Python 3.14 is not installed yet, `uv` can install it:

```bash
uv python install 3.14
uv sync
```

### Configure environment

Create a `.env` file in the project root (it is excluded from Git) and set:

```dotenv
POSTGRES_DB_URL=postgresql://db_user:db_password@db_host:5432/ola_data_agent
GOOGLE_API_KEY=your_google_gemini_api_key
```

Use the connection string for your own PostgreSQL host, database, username, and password. URL-encode special characters in credentials when required. `POSTGRES_DB_URL` is used by the app for database connections and metadata storage.

### Start the application

```bash
uv run uvicorn main:app --reload
```

Open <http://127.0.0.1:8000> for the web interface. Interactive API documentation is available at <http://127.0.0.1:8000/docs>.

## Using the application

1. Open the web interface.
2. Choose a `.csv` file or drag it onto the upload area (maximum size: 10 MB).
3. Once upload succeeds, enter a question about that file—for example, “Which month had the most rides?”.
4. Review the answer and generated SQL. The UI also lets you copy the SQL query.

Each upload receives its own upload ID and table. Use the ID returned by the upload endpoint when calling the question endpoint.

## API reference

### `POST /sql-analyst/upload`

Accepts a multipart form upload with a `file` field containing a UTF-8 CSV. The file must have a header row and be no larger than 10 MB.

Example:

```bash
curl -X POST http://127.0.0.1:8000/sql-analyst/upload \
  -F "file=@data/rides.csv"
```

On success, the API returns HTTP `202` with the original file name, generated PostgreSQL table name, and an `upload_id`. Save the `upload_id` for the next request.

### `POST /sql-analyst/ask`

Accepts a JSON request with the upload ID and a question:

```json
{
  "upload_id": "UUID-returned-by-the-upload-endpoint",
  "question": "Which month had the most rides?"
}
```

Example:

```bash
curl -X POST http://127.0.0.1:8000/sql-analyst/ask \
  -H "Content-Type: application/json" \
  -d "{\"upload_id\":\"UUID-returned-by-the-upload-endpoint\",\"question\":\"Which month had the most rides?\"}"
```

The response contains the answer and generated SQL:

```json
{
  "answer": "…",
  "sql": "SELECT …"
}
```

Questions must be between 1 and 1,000 characters. An unknown upload ID returns an error. Expired upload tables are removed by the cleanup job; see the data-handling note below for the current metadata cleanup behavior. See `/docs` for the live OpenAPI specification and response details.

## Deployment notes

- Deploy the FastAPI application and its UI together, or configure the UI to call the deployed API. The included page sends API requests to the same origin.
- Set `POSTGRES_DB_URL` and `GOOGLE_API_KEY` in the deployment platform's secret/environment-variable settings; do not commit real credentials.
- Use a persistent, reachable PostgreSQL database. The application needs permissions to create and populate upload tables, create its metadata table, and drop expired upload tables.
- Set a suitable process start command, such as `uvicorn main:app --host 0.0.0.0 --port $PORT` (adapt the port expression to your hosting platform).
- Configure platform health checks and network access so the service can reach PostgreSQL and the Google Gemini API.
- Replace the deployment and video URLs in [Project links](#project-links) after publishing your own deployment and walkthrough.

## Safety and data handling

The agent is prompted to generate read-only SQL and uses an LLM-based guard before executing it. This is a useful safeguard, but an LLM judgment is **not** a database security boundary. Do not rely on it as the only protection, and do not upload sensitive or production data to an untrusted deployment. Restrict database credentials and access appropriately, and review the generated SQL before using results for important decisions.

Uploaded CSV data is written to PostgreSQL. Temporary upload tables are intended to be dropped after eight hours by the cleanup job, which also runs at application startup. In the current implementation, metadata rows are marked as expired but their deletion is not committed by the cleanup routine, so they may remain in the metadata table. Avoid treating this temporary-table lifecycle as a substitute for backups, access controls, or a formal data-retention policy.

## Contributing

1. Create a branch for your change.
2. Make changes consistent with the existing Python and project conventions.
3. Run the application locally and verify both CSV upload and question answering against a test database.
4. Open a pull request describing the change and how it was verified.

## License

No license file is currently included in this repository. Add a license before redistributing the project if you intend to grant reuse rights.
