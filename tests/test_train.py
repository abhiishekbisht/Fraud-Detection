import os
import time
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

def test_train_endpoints_validation():
    response = client.post("/train/non_existent_dataset_id")
    assert response.status_code == 202

def test_train_pipeline_success():
    start_response = client.post("/train/", json={"model": "xgboost"})
    assert start_response.status_code == 200
    start_data = start_response.json()
    assert "job_id" in start_data
    assert "metrics" in start_data
    assert start_data["metrics"]["accuracy"] > 0.9
