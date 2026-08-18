import io
import os
import sqlite3
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

def test_predict_single_endpoint():
    payload = {
        "Time": 0,
        "Amount": 2500,
        "V17": -3.5,
        "V14": -2.1
    }
    response = client.post("/api/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "prediction" in data
    assert "probability" in data
    assert "risk_score" in data
    assert "risk_label" in data
    assert data["risk_label"] == "High"

def test_predict_batch_endpoint():
    cols = ["Time", "Amount"] + [f"V{i}" for i in range(1, 29)]
    df = pd.DataFrame([{col: 0.0 for col in cols}])
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    
    files = {"file": ("test_batch.csv", buf.getvalue().encode("utf-8"), "text/csv")}
    response = client.post("/api/predict/batch", files=files)
    assert response.status_code == 200
    data = response.json()
    assert "filename" in data
    assert "total_rows" in data
    assert "csv_content" in data
