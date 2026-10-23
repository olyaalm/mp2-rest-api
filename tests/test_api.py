from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from main import app, storage

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_storage():
    storage.clear()
    yield
    storage.clear()


def test_health_check():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "1.0.0"}


def test_upload_and_retrieve_sample_data():
    sample = Path("fixtures/sample_data.csv").read_bytes()

    upload = client.post(
        "/upload",
        files={"file": ("sample_data.csv", sample, "text/csv")},
    )

    assert upload.status_code == 200
    assert upload.json() == {
        "id": 1,
        "filename": "sample_data.csv",
        "rows": 6,
        "columns": 2,
        "column_names": ["student_id", "score"],
    }

    retrieval = client.get("/datasets/1?limit=2")

    assert retrieval.status_code == 200
    assert retrieval.json()["id"] == 1
    assert retrieval.json()["total_rows"] == 6
    assert len(retrieval.json()["data"]) == 2


@pytest.mark.parametrize(
    ("filename", "contents"),
    [
        ("notes.txt", b"not a CSV"),
        ("empty.csv", b""),
        ("malformed.csv", b'"unclosed field'),
        ("invalid-encoding.csv", b"\xff\xfe\xff"),
    ],
)
def test_rejects_unsupported_or_unreadable_uploads(filename, contents):
    response = client.post(
        "/upload",
        files={"file": (filename, contents, "text/csv")},
    )

    assert response.status_code == 400


def test_missing_dataset_and_invalid_limit():
    assert client.get("/datasets/999").status_code == 404
    assert client.get("/datasets/1?limit=0").status_code == 422


def test_storage_copies_data_and_updates_metadata():
    original = pd.DataFrame({"value": [1, 2]})
    dataset_id = storage.save(original, "values.csv")
    original.loc[0, "value"] = 99

    retrieved = storage.get(dataset_id)
    assert retrieved.loc[0, "value"] == 1
    retrieved.loc[0, "value"] = 100
    assert storage.get(dataset_id).loc[0, "value"] == 1

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