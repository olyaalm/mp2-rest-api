"""Shared fixtures for the API test suite."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from main import app, storage


@pytest.fixture
def client():
    """Create a test client with an empty in-memory dataset store.

    Yields:
        TestClient: A client connected to the FastAPI application.
    """
    storage.clear()
    with TestClient(app) as test_client:
        yield test_client
    storage.clear()


@pytest.fixture
def sample_csv_bytes():
    """Read the sample CSV as bytes for a multipart upload.

    Returns:
        bytes: The complete contents of the sample CSV fixture.
    """
    filepath = Path("fixtures") / "sample_data.csv"
    return filepath.read_bytes()


@pytest.fixture
def uploaded_dataset_id(client, sample_csv_bytes):
    """Upload the sample table and return its assigned ID.

    Args:
        client: The test client for the API.
        sample_csv_bytes: The fixture file contents to upload.

    Returns:
        int: The ID assigned to the uploaded dataset.
    """
    response = client.post(
        "/upload",
        files={"file": ("sample_data.csv", sample_csv_bytes, "text/csv")},
    )
    assert response.status_code == 200
    return response.json()["id"]


@pytest.fixture
def processing_body():
    """Provide the assignment's validation and cleaning settings.

    Returns:
        dict: A request body for the sample's student_id and score columns.
    """
    return {
        "validation": {
            "required_columns": ["student_id", "score"],
            "numeric_columns": ["score"],
        },
        "processing": {
            "remove_duplicates": True,
            "missing": {"enabled": True, "axis": "rows"},
            "outliers": {
                "enabled": False,
                "columns": [],
                "method": "iqr",
                "threshold": 1.5,
            },
        },
    }