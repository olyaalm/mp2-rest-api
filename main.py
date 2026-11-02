import io
import json
import logging
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, File, HTTPException, Query, UploadFile

from data_pipeline import create_cleaning_report, process_data, validate_dataframe
from src import (
    DatasetInfo,
    DatasetStorage,
    HealthResponse,
    ProcessConfig,
    ProcessingReport,
    log_requests,
    setup_logging,
)

setup_logging(verbose=True)
logger = logging.getLogger(__name__)

app = FastAPI(title="Data Processing API", version="1.0.0")
# Add request IDs and request-level logs to every route.
app.middleware("http")(log_requests)

# Keep one storage instance so later requests can retrieve earlier uploads.
storage = DatasetStorage()


@app.get("/health", response_model=HealthResponse)
def health_check():
    """Return the API's current status and version.

    Returns:
        dict: A small JSON-compatible status response.
    """
    # Respond with a small status payload without changing server state.
    return {"status": "ok", "version": "1.0.0"}


@app.post("/upload", response_model=DatasetInfo)
async def upload_dataset(file: UploadFile = File(...)):
    """Read a CSV upload, save it in memory, and return its metadata.

    Args:
        file: CSV file sent by the client as multipart form data.

    Returns:
        DatasetInfo: The stored dataset's ID, filename, and table shape.

    Raises:
        HTTPException: If the file is not a readable CSV.
    """
    # Check the uploaded filename before reading or parsing its contents.
    filename = file.filename or ""
    extension = Path(filename).suffix.lower()
    if extension != ".csv":
        logger.warning("Unsupported file format: %s", extension)
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    # Read the upload asynchronously, then parse its bytes as a CSV table.
    contents = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(contents))
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError) as exc:
        logger.warning("Could not read uploaded CSV %s: %s", filename, exc)
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is not a readable CSV.",
        ) from exc

    # Store a protected copy and build the response from stored metadata.
    dataset_id = storage.save(df, filename)
    metadata = storage.get_metadata(dataset_id)
    logger.info(
        "Uploaded dataset: id=%s, filename=%s, rows=%s",
        dataset_id,
        filename,
        len(df),
    )
    return DatasetInfo(**metadata)


@app.get("/datasets/{dataset_id}")
def get_dataset(dataset_id: int, limit: int = Query(default=100, ge=1)):
    """Return a limited number of rows from a stored dataset.

    Args:
        dataset_id: ID assigned when the CSV was uploaded.
        limit: Maximum number of rows to include in the response.

    Returns:
        dict: Dataset ID, returned records, and total row count.

    Raises:
        HTTPException: If the dataset ID is not in storage.
    """
    # Check the ID first so a missing dataset gets a clear 404 response.
    metadata = storage.get_metadata(dataset_id)
    if metadata is None:
        logger.warning("Dataset not found: %s", dataset_id)
        raise HTTPException(status_code=404, detail="Dataset not found.")

    # Retrieve a copy, then limit how many records are returned to the client.
    df = storage.get(dataset_id)
    records = json.loads(df.head(limit).to_json(orient="records"))
    logger.info("Retrieved dataset: id=%s, returned_rows=%s", dataset_id, len(records))
    return {"id": dataset_id, "data": records, "total_rows": metadata["rows"]}


@app.post(
    "/datasets/{dataset_id}/process",
    response_model=ProcessingReport,
)
def process_dataset(dataset_id: int, config: ProcessConfig):
    """Validate and clean a stored table, then save the successful result.

    Args:
        dataset_id: ID assigned when the CSV was uploaded.
        config: Required-column, numeric-validation, and cleaning settings.

    Returns:
        ProcessingReport: Validation row removals and the cleaning summary.

    Raises:
        HTTPException: For a missing dataset or invalid processing settings.

    Notes:
        Storage is updated only after validation and cleaning both succeed.
    """
    # Retrieve a copy so failed processing cannot change the stored dataset.
    df = storage.get(dataset_id)
    if df is None:
        logger.warning("Cannot process missing dataset: id=%s", dataset_id)
        raise HTTPException(status_code=404, detail="Dataset not found.")

    # Convert nested request settings to the dictionaries expected by MP1.
    config_data = config.model_dump()
    validation_settings = config_data["validation"]
    numeric_columns = validation_settings["numeric_columns"]

    # Return a client error for configured numeric columns absent from the table.
    missing_numeric_columns = [
        column for column in numeric_columns if column not in df.columns
    ]
    if missing_numeric_columns:
        message = f"Numeric columns not found: {missing_numeric_columns}"
        logger.warning(
            "Dataset processing rejected: id=%s, %s",
            dataset_id,
            message,
        )
        raise HTTPException(status_code=400, detail=message)

    try:
        # Validate required columns and remove rows with invalid numeric values.
        rows_before_validation = len(df)
        validated = validate_dataframe(
            df,
            required_columns=validation_settings["required_columns"],
            numeric_columns=numeric_columns,
        )
        validation_rows_removed = rows_before_validation - len(validated)

        # Keep a snapshot so the report measures only the cleaning steps below.
        before_processing = validated.copy(deep=True)

        # Apply the configured duplicate, missing-value, and outlier operations.
        processed = process_data(validated, config_data)

        # Summarize changes from processing separately from validation changes.
        cleaning_report = create_cleaning_report(before_processing, processed)
    except ValueError as error:
        # Convert expected MP1 validation or setting errors into an HTTP 400.
        logger.warning(
            "Dataset processing rejected: id=%s, error=%s",
            dataset_id,
            error,
        )
        raise HTTPException(status_code=400, detail=str(error)) from error

    # Save only after every validation and processing step has succeeded.
    storage.update(dataset_id, processed)
    logger.info(
        "Processed dataset: id=%s, validation_rows_removed=%s, rows_removed=%s",
        dataset_id,
        validation_rows_removed,
        cleaning_report["rows_removed"],
    )
    return {
        "id": dataset_id,
        "validation_rows_removed": validation_rows_removed,
        "cleaning_report": cleaning_report,
    }