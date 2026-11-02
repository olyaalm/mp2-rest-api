# MP2 REST API

This project exposes the MP1 data-validation and cleaning pipeline through a FastAPI application. A client can upload a CSV, retrieve its rows, or validate and process it with request settings. Uploaded datasets are kept in memory, so they are cleared when the application restarts.

## Project Structure

- `main.py` defines the HTTP routes and connects them to storage and the pipeline.
- `src/models.py` defines the request and response data models.
- `src/storage.py` stores DataFrames and returns copies so callers cannot accidentally edit stored data.
- `src/middleware.py` assigns request IDs and logs each request's method, path, status, and duration.
- `data_pipeline/` contains the reusable MP1 loader, validator, processor, output, and utility modules.
- `fixtures/sample_data.csv` is the small dataset used by the automated tests.
- `tests/` contains API tests and fixtures.

## Run the API

From the project directory, activate the virtual environment and start the server:

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn main:app --reload
```

Open `http://127.0.0.1:8000/docs` to try the endpoints interactively.

## Endpoints

### `GET /health`

Returns the application status and version.

### `POST /upload`

Upload a `.csv` file as multipart form data. The response includes its assigned ID, filename, row and column counts, and column names. Non-CSV files and unreadable CSV files return `400`.

### `GET /datasets/{dataset_id}?limit=100`

Returns up to `limit` rows from an uploaded dataset. The limit must be at least one. An unknown ID returns `404`.

### `POST /datasets/{dataset_id}/process`

Validate and clean a stored dataset. Validation removes rows with invalid values in configured numeric columns. Processing can remove duplicates, rows or columns with missing values, and outliers. The response reports validation removals separately from the cleaning report. The stored dataset is replaced only if every step succeeds.

Example request:

```json
{
  "validation": {
    "required_columns": ["student_id", "score"],
    "numeric_columns": ["score"]
  },
  "processing": {
    "remove_duplicates": true,
    "missing": {"enabled": true, "axis": "rows"},
    "outliers": {
      "enabled": false,
      "columns": [],
      "method": "iqr",
      "threshold": 1.5
    }
  }
}
```

The outlier method can be `iqr` or `zscore`. Invalid processing settings or missing configured numeric columns return `400`; a dataset ID that does not exist returns `404`.

Every response includes an `X-Request-ID` header. The same ID appears in the server's request log, making it easier to match a client response to its log entry.

## Tests

Run the API test suite from the project directory:

```powershell
.\.venv\Scripts\python.exe -m pytest tests -v
```

The tests cover upload and retrieval, successful processing, error handling, storage-copy behavior, and request IDs.