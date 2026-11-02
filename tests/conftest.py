"""Shared fixtures for the API test suite."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from main import app, storage


@pytest.fixture
def client():
    """Give each test a clean in-memory store and a running test client."""
    storage.clear()
    with TestClient(app) as test_client:
        yield test_client
    storage.clear()


@pytest.fixture
def sample_csv_bytes():
    """Read the course CSV fixture as bytes, as a file upload would arrive."""
    filepath = Path("fixtures") / "sample_data.csv"
    return filepath.read_bytes()


@pytest.fixture
def uploaded_dataset_id(client, sample_csv_bytes):
    """Upload the sample table and share its assigned ID with a test."""
    response = client.post(
        "/upload",
        files={"file": ("sample_data.csv", sample_csv_bytes, "text/csv")},
    )
    assert response.status_code == 200
    return response.json()["id"]


@pytest.fixture
def processing_body():
    """Provide valid settings for the sample fixture's columns."""
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