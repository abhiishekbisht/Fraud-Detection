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
    cols = ["Time", "Amount"] + [f"V{i}" for i in range(1, 29)] + ["Class"]
    data = {col: [1.0, 2.0] for col in cols}
    df = pd.DataFrame(data)
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")

def create_invalid_schema_csv_bytes() -> bytes:
    cols = ["Time", "Amount"] + [f"V{i}" for i in range(2, 29)]
    data = {col: [1.0, 2.0] for col in cols}
    df = pd.DataFrame(data)
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")

def test_upload_valid_csv():
    csv_bytes = create_valid_csv_bytes()
    files = {"file": ("creditcard_sample.csv", csv_bytes, "text/csv")}
    
    response = client.post("/upload", files=files)
    assert response.status_code == 200
    
    data = response.json()
    assert "dataset_id" in data
    assert data["rows"] == 2
    assert len(data["columns"]) == 31
    assert data["validation_status"] == "valid"
    
    dataset_id = data["dataset_id"]
    saved_path = f"data/raw/{dataset_id}.csv"
    assert os.path.exists(saved_path)
    
    if os.path.exists(saved_path):
        os.remove(saved_path)

def test_upload_missing_columns():
    csv_bytes = create_invalid_schema_csv_bytes()
    files = {"file": ("creditcard_invalid.csv", csv_bytes, "text/csv")}
    
    response = client.post("/upload", files=files)
    assert response.status_code == 400
    
    data = response.json()
    assert "missing required columns" in data["detail"].lower()

def test_upload_non_csv():
    files = {"file": ("document.txt", b"Hello world text payload", "text/plain")}
    response = client.post("/upload", files=files)
    assert response.status_code == 400
    assert "only csv files are accepted" in response.json()["detail"].lower()

def test_upload_malformed_csv():
    malformed_csv = b"col1,col2\n1,\"unclosed quote"
    files = {"file": ("malformed.csv", malformed_csv, "text/csv")}
    
    response = client.post("/upload", files=files)
    assert response.status_code == 400
    assert "failed to parse csv" in response.json()["detail"].lower()

def test_upload_size_limit(monkeypatch):
    monkeypatch.setattr(upload, "MAX_FILE_SIZE", 50)
    csv_bytes = create_valid_csv_bytes()
    assert len(csv_bytes) > 50
    files = {"file": ("too_large.csv", csv_bytes, "text/csv")}
    response = client.post("/upload", files=files)
    assert response.status_code == 400
    assert "file size exceeds" in response.json()["detail"].lower()

def test_session_isolation_and_auto_reset():
    session_a = "test_session_user_a"
    session_b = "test_session_user_b"
    csv_bytes = create_valid_csv_bytes()
    
    # 1. Upload in Session A
    files = {"file": ("dataset_a.csv", csv_bytes, "text/csv")}
    resp_a = client.post("/upload", files=files, headers={"X-Session-ID": session_a})
    assert resp_a.status_code == 200
    dataset_id = resp_a.json()["dataset_id"]
    
    # 2. Check Session A sees dataset
    list_a = client.get("/api/upload/cleaned-datasets", headers={"X-Session-ID": session_a}).json()
    assert len(list_a) == 1
    assert list_a[0]["filename"] == "dataset_a.csv"
    
    # 3. Check Session B does NOT see Session A's dataset (Session Isolation)
    list_b = client.get("/api/upload/cleaned-datasets", headers={"X-Session-ID": session_b}).json()
    assert len(list_b) == 0
    
    # 4. Check EDA stats for Session B return empty payload instead of leaking Session A's file
    eda_b = client.get("/api/eda/stats", headers={"X-Session-ID": session_b}).json()
    assert eda_b["total_rows"] == 0
    
    # 5. Reset Session A
    reset_resp = client.post("/api/reset", headers={"X-Session-ID": session_a})
    assert reset_resp.status_code == 200
    
    # 6. Verify file is deleted on disk and metadata removed
    saved_path = f"data/raw/{dataset_id}.csv"
    assert not os.path.exists(saved_path)
    
    list_a_after = client.get("/api/upload/cleaned-datasets", headers={"X-Session-ID": session_a}).json()
    assert len(list_a_after) == 0

