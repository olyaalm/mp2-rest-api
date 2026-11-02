import pandas as pd
import pytest
import logging

import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from main import storage
from src import log_requests


def test_health_check(client):
    """The health route returns status and a request ID."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "1.0.0"}
    assert response.headers["X-Request-ID"]


def test_upload_and_retrieve_sample_data(client, uploaded_dataset_id):
    """Uploading the fixture returns metadata and retrieval returns its rows."""
    metadata = client.get(f"/datasets/{uploaded_dataset_id}")

    assert metadata.status_code == 200
    assert metadata.json()["id"] == uploaded_dataset_id
    assert metadata.json()["total_rows"] == 6
    assert len(metadata.json()["data"]) == 6

    # Confirm that the retrieval limit caps the returned records.
    limited = client.get(f"/datasets/{uploaded_dataset_id}?limit=2")
    assert limited.status_code == 200
    assert len(limited.json()["data"]) == 2


def test_process_dataset_and_retrieve_cleaned_rows(
    client, uploaded_dataset_id, processing_body
):
    """Validation removes invalid values and processing removes duplicates."""
    response = client.post(
        f"/datasets/{uploaded_dataset_id}/process",
        json=processing_body,
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": uploaded_dataset_id,
        "validation_rows_removed": 1,
        "cleaning_report": {
            "rows_before": 5,
            "rows_after": 3,
            "rows_removed": 2,
            "columns_before": 2,
            "columns_after": 2,
            "columns_removed": 0,
        },
    }

    # Confirm that later retrieval returns the newly stored clean data.
    retrieved = client.get(f"/datasets/{uploaded_dataset_id}")
    assert retrieved.status_code == 200
    assert retrieved.json()["total_rows"] == 3
    assert [row["student_id"] for row in retrieved.json()["data"]] == [1, 2, 5]


def test_missing_dataset_returns_not_found(client):
    """A dataset ID that has not been uploaded returns a 404 response."""
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
    """Unsupported filenames and unreadable CSV bytes are rejected."""
    response = client.post(
        "/upload",
        files={"file": (filename, contents, "text/csv")},
    )

    assert response.status_code == 400
    assert response.headers["X-Request-ID"]


def test_process_rejects_unknown_numeric_column_without_changing_data(
    client, uploaded_dataset_id, processing_body
):
    """A missing numeric column returns 400 and preserves the original upload."""
    before = client.get(f"/datasets/{uploaded_dataset_id}").json()
    processing_body["validation"]["numeric_columns"] = ["missing_score"]

    response = client.post(
        f"/datasets/{uploaded_dataset_id}/process",
        json=processing_body,
    )

    assert response.status_code == 400
    assert "missing_score" in response.json()["detail"]
    assert client.get(f"/datasets/{uploaded_dataset_id}").json() == before


def test_process_rejects_invalid_outlier_settings_without_changing_data(
    client, uploaded_dataset_id, processing_body
):
    """An MP1 processing error returns 400 before storage is updated."""
    before = client.get(f"/datasets/{uploaded_dataset_id}").json()
    processing_body["processing"]["outliers"] = {
        "enabled": True,
        "columns": ["score"],
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
    """Storage protects its saved DataFrame from edits to input and output copies."""
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
    """The retrieval endpoint validates its positive row limit."""
    response = client.get("/datasets/1?limit=0")

    assert response.status_code == 422
    assert response.headers["X-Request-ID"]


def test_unexpected_error_is_logged_and_hidden_from_client(caplog):
    """Unexpected endpoint errors return a generic 500 and keep a request ID."""
    test_app = FastAPI()
    test_app.middleware("http")(log_requests)

    @test_app.get("/unexpected-error")
    def raise_unexpected_error():
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