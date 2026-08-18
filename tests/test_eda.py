import os
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

def test_eda_api_endpoint():
    response = client.get("/api/eda/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_rows" in data
    assert "fraud_count" in data
    assert "legit_count" in data

def test_eda_api_endpoint_uncleaned():
    response = client.get("/api/eda/stats?dataset=uncleaned_mock.csv")
    assert response.status_code == 200
    data = response.json()
    assert "total_rows" in data

def test_eda_api_endpoint_not_found():
    response = client.get("/api/eda/stats?dataset=non_existent_dataset.csv")
    assert response.status_code == 200
    data = response.json()
    assert "total_rows" in data
