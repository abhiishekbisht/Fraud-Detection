import io
import os
import sqlite3
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.database import DB_PATH
from app.routers import upload

client = TestClient(app)

def create_valid_csv_bytes() -> bytes:
    """
    Creates a small, valid in-memory CSV file matching the Kaggle Credit Card Fraud dataset schema.
    """
    # Time, Amount, V1-V28, Class
    cols = ["Time", "Amount"] + [f"V{i}" for i in range(1, 29)] + ["Class"]
    data = {col: [1.0, 2.0] for col in cols}
    df = pd.DataFrame(data)
    
    # Save to buffer
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")


def create_invalid_schema_csv_bytes() -> bytes:
    """
    Creates a small, invalid in-memory CSV file missing some required columns (e.g. V1, Class).
    """
    # Missing V1 and Class
    cols = ["Time", "Amount"] + [f"V{i}" for i in range(2, 29)]
    data = {col: [1.0, 2.0] for col in cols}
    df = pd.DataFrame(data)
    
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")


def test_upload_valid_csv():
    """
    Tests uploading a valid CSV dataset. Verifies file saved, DB updated, and response payload.
    """
    csv_bytes = create_valid_csv_bytes()
    files = {"file": ("creditcard_sample.csv", csv_bytes, "text/csv")}
    
    response = client.post("/upload", files=files)
    assert response.status_code == 200
    
    data = response.json()
    assert "dataset_id" in data
    assert data["row_count"] == 2
    assert len(data["columns"]) == 31
    assert data["validation_status"] == "valid"
    
    dataset_id = data["dataset_id"]
    
    # Verify file saved on disk
    saved_path = f"data/raw/{dataset_id}.csv"
    assert os.path.exists(saved_path)
    
    # Verify metadata saved in SQLite
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT filename, row_count, status FROM datasets WHERE id = ?", (dataset_id,))
    row = cursor.fetchone()
    conn.close()
    
    assert row is not None
    assert row[0] == "creditcard_sample.csv"
    assert row[1] == 2
    assert row[2] == "valid"
    
    # Clean up test artifact
    if os.path.exists(saved_path):
        os.remove(saved_path)


def test_upload_missing_columns():
    """
    Tests uploading a CSV dataset missing required columns.
    Should return 400 listing the missing columns and clean up any written files.
    """
    csv_bytes = create_invalid_schema_csv_bytes()
    files = {"file": ("creditcard_invalid.csv", csv_bytes, "text/csv")}
    
    response = client.post("/upload", files=files)
    assert response.status_code == 400
    
    data = response.json()
    assert "missing required columns" in data["detail"].lower()
    assert "v1" in data["detail"].lower()
    assert "class" in data["detail"].lower()
    
    # Ensure no files left behind
    # Scanning data/raw/ to verify no newly created csv
    raw_dir = "data/raw"
    if os.path.exists(raw_dir):
        files_on_disk = os.listdir(raw_dir)
        # Ensure no uuid-labeled file exists for this failed upload
        for f in files_on_disk:
            assert not f.endswith(".csv") or len(f.split(".csv")[0]) != 36


def test_upload_non_csv():
    """
    Tests uploading a non-CSV file. Should return a 400 error.
    """
    files = {"file": ("document.txt", b"Hello world text payload", "text/plain")}
    response = client.post("/upload", files=files)
    assert response.status_code == 400
    assert "only csv files are accepted" in response.json()["detail"].lower()


def test_upload_malformed_csv():
    """
    Tests uploading a malformed CSV. Should return a 400 error.
    """
    # A malformed CSV with an unclosed quote that triggers a pandas ParserError
    malformed_csv = b"col1,col2\n1,\"unclosed quote"
    files = {"file": ("malformed.csv", malformed_csv, "text/csv")}
    
    response = client.post("/upload", files=files)
    assert response.status_code == 400
    assert "failed to parse csv" in response.json()["detail"].lower()


def test_upload_size_limit(monkeypatch):
    """
    Tests file size limit enforcement. Modifies MAX_FILE_SIZE limit to a small value
    and uploads a larger file to trigger size limitation error.
    """
    # Change max file size to 50 bytes for test
    monkeypatch.setattr(upload, "MAX_FILE_SIZE", 50)
    
    csv_bytes = create_valid_csv_bytes()  # This will be around ~100+ bytes
    assert len(csv_bytes) > 50
    
    files = {"file": ("too_large.csv", csv_bytes, "text/csv")}
    response = client.post("/upload", files=files)
    
    assert response.status_code == 400
    assert "file size exceeds" in response.json()["detail"].lower()
