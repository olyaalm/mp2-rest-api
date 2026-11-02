import logging

import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from main import storage
from src import log_requests


def test_health_check(client):
    """Check that health reports the service status and request ID.

    Args:
        client: The test client for the API.

    Returns:
        None: This test checks the HTTP response directly.
    """
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "1.0.0"}
    assert response.headers["X-Request-ID"]


def test_upload_and_retrieve_sample_data(client, uploaded_dataset_id):
    """Check that the uploaded sample has the expected fields and row count.

    Args:
        client: The test client for the API.
        uploaded_dataset_id: ID returned when the sample file was uploaded.

    Returns:
        None: This test checks the retrieval responses directly.
    """
    metadata = client.get(f"/datasets/{uploaded_dataset_id}")

    assert metadata.status_code == 200
    assert metadata.json()["id"] == uploaded_dataset_id
    assert metadata.json()["total_rows"] == 100
    assert len(metadata.json()["data"]) == 100
    assert list(metadata.json()["data"][0]) == [
        "record_id",
        "name",
        "rating",
        "category",
        "status",
    ]

    # Confirm that the retrieval limit caps the returned records.
    limited = client.get(f"/datasets/{uploaded_dataset_id}?limit=2")
    assert limited.status_code == 200
    assert len(limited.json()["data"]) == 2


def test_process_dataset_and_retrieve_cleaned_rows(
    client, uploaded_dataset_id, processing_body
):
    """Check validation, cleaning, reporting, and storage update end to end.

    Args:
        client: The test client for the API.
        uploaded_dataset_id: ID returned when the sample file was uploaded.
        processing_body: Validation and processing settings for the sample.

    Returns:
        None: This test checks the processing report and later retrieval.
    """
    response = client.post(
        f"/datasets/{uploaded_dataset_id}/process",
        json=processing_body,
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": uploaded_dataset_id,
        "validation_rows_removed": 2,
        "cleaning_report": {
            "rows_before": 98,
            "rows_after": 92,
            "rows_removed": 6,
            "columns_before": 5,
            "columns_after": 5,
            "columns_removed": 0,
        },
    }

    # Confirm that later retrieval returns the newly stored clean data.
    retrieved = client.get(f"/datasets/{uploaded_dataset_id}")
    assert retrieved.status_code == 200
    assert retrieved.json()["total_rows"] == 92
    assert retrieved.json()["data"][0]["record_id"] == 1
    assert all(row["rating"] < 200 and row["rating"] > -50 for row in retrieved.json()["data"])


def test_missing_dataset_returns_not_found(client):
    """Check that a dataset ID absent from storage returns HTTP 404.

    Args:
        client: The test client for the API.

    Returns:
        None: This test checks the missing-resource response.
    """
    response = client.get("/datasets/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Dataset not found."}
    assert response.headers["X-Request-ID"]


@pytest.mark.parametrize(
    ("filename", "contents"),
    [
        ("notes.txt", b"not a CSV"),
        ("empty.csv", b""),
        ("malformed.csv", b'"unclosed field'),
        ("invalid-encoding.csv", b"\xff\xfe\xff"),
    ],
)
def test_rejects_unsupported_or_unreadable_uploads(client, filename, contents):
    """Check that unsupported names and unreadable CSV contents return 400.

    Args:
        client: The test client for the API.
        filename: Name supplied for the upload.
        contents: Bytes supplied as the uploaded file contents.

    Returns:
        None: This test checks the upload error response.
    """
    response = client.post(
        "/upload",
        files={"file": (filename, contents, "text/csv")},
    )

    assert response.status_code == 400
    assert response.headers["X-Request-ID"]


def test_process_rejects_unknown_numeric_column_without_changing_data(
    client, uploaded_dataset_id, processing_body
):
    """Check bad numeric settings return 400 without replacing stored data.

    Args:
        client: The test client for the API.
        uploaded_dataset_id: ID returned when the sample file was uploaded.
        processing_body: Valid processing settings changed to include a bad column.

    Returns:
        None: This test compares the stored data before and after the error.
    """
    before = client.get(f"/datasets/{uploaded_dataset_id}").json()
    processing_body["validation"]["numeric_columns"] = ["missing_rating"]

    response = client.post(
        f"/datasets/{uploaded_dataset_id}/process",
        json=processing_body,
    )

    assert response.status_code == 400
    assert "missing_rating" in response.json()["detail"]
    assert client.get(f"/datasets/{uploaded_dataset_id}").json() == before


def test_process_rejects_invalid_outlier_settings_without_changing_data(
    client, uploaded_dataset_id, processing_body
):
    """Check unsupported outlier methods return 400 without changing the upload.

    Args:
        client: The test client for the API.
        uploaded_dataset_id: ID returned when the sample file was uploaded.
        processing_body: Valid settings changed to use an unsupported method.

    Returns:
        None: This test compares the stored data before and after the error.
    """
    before = client.get(f"/datasets/{uploaded_dataset_id}").json()
    processing_body["processing"]["outliers"] = {
        "enabled": True,
        "columns": ["rating"],
        "method": "unknown",
        "threshold": 1.5,
    }

    response = client.post(
        f"/datasets/{uploaded_dataset_id}/process",
        json=processing_body,
    )

    assert response.status_code == 400
    assert "Outlier method" in response.json()["detail"]
    assert client.get(f"/datasets/{uploaded_dataset_id}").json() == before


def test_storage_copies_data_and_updates_metadata(client):
    """Check that storage copies saved data and reports updated metadata.

    Args:
        client: The test client, which resets the shared storage for this test.

    Returns:
        None: This test checks storage methods directly.
    """
    original = pd.DataFrame({"value": [1, 2]})
    dataset_id = storage.save(original, "values.csv")
    original.loc[0, "value"] = 99

    retrieved = storage.get(dataset_id)
    assert retrieved.loc[0, "value"] == 1
    retrieved.loc[0, "value"] = 100
    assert storage.get(dataset_id).loc[0, "value"] == 1

    # Updating replaces stored data while preserving the original dataset ID.
    updated = pd.DataFrame({"new_value": [3]})
    assert storage.update(dataset_id, updated)
    assert storage.get_metadata(dataset_id) == {
        "id": dataset_id,
        "filename": "values.csv",
        "rows": 1,
        "columns": 1,
        "column_names": ["new_value"],
    }
    assert not storage.update(999, updated)


def test_invalid_limit_is_rejected(client):
    """Check that retrieval rejects a limit below one.

    Args:
        client: The test client for the API.

    Returns:
        None: This test checks the HTTP validation response.
    """
    response = client.get("/datasets/1?limit=0")

    assert response.status_code == 422
    assert response.headers["X-Request-ID"]


def test_unexpected_error_is_logged_and_hidden_from_client(caplog):
    """Check unexpected errors are logged but hidden behind a generic response.

    Args:
        caplog: Pytest's fixture for capturing application log records.

    Returns:
        None: This test checks the 500 response, request ID, and traceback log.
    """
    test_app = FastAPI()
    test_app.middleware("http")(log_requests)

    @test_app.get("/unexpected-error")
    def raise_unexpected_error():
        """Raise a test error so middleware behavior can be checked.

        Returns:
            None: The intentional exception prevents a normal return.
        """
        # This private detail should appear in server logs, not the response.
        raise RuntimeError("private internal detail")

    with caplog.at_level(logging.ERROR, logger="src.middleware"):
        with TestClient(test_app) as test_client:
            response = test_client.get("/unexpected-error")

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert response.headers["X-Request-ID"]
    assert "private internal detail" not in response.text

    # Confirm that the exception logger recorded the traceback for debugging.
    error_record = next(
        record for record in caplog.records if "Unexpected request error" in record.message
    )
    assert error_record.exc_info is not None