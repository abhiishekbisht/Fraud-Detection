import os
import io
import shutil
import sqlite3
import joblib
import pytest
import pandas as pd
import numpy as np
from fastapi.testclient import TestClient
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from app.main import app
from app.services.database import (
    save_dataset_metadata,
    create_training_job,
    save_trained_model,
    delete_dataset_metadata,
    DB_PATH
)

client = TestClient(app)

@pytest.fixture(autouse=True)
def clean_db_before_and_after():
    """
    Cleans up any potential stale records before and after predict tests.
    """
    delete_dataset_metadata("test_predict_dataset")
    yield
    delete_dataset_metadata("test_predict_dataset")


def test_predict_no_active_model():
    """
    Asserts endpoints return 400 when no model has been activated.
    """
    # 1. Single prediction
    payload = {
        "Time": 0.0, "Amount": 100.0,
        **{f"V{i}": 0.0 for i in range(1, 29)}
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 400
    assert "no active model" in response.json()["detail"].lower()

    # 2. Batch prediction
    csv_data = "Time,Amount," + ",".join([f"V{i}" for i in range(1, 29)]) + "\n0.0,10.0," + ",".join(["0.0"]*28)
    files = {"file": ("test.csv", csv_data.encode("utf-8"), "text/csv")}
    batch_response = client.post("/predict/batch", files=files)
    assert batch_response.status_code == 400
    assert "no active model" in batch_response.json()["detail"].lower()


def test_prediction_pipeline_success():
    """
    Simulates training a dummy model, activating it, and running single/batch inference.
    """
    dataset_id = "test_predict_dataset"
    job_id = "test_predict_job"
    model_name = "logistic_regression"
    model_id = f"{job_id}_{model_name}"

    # 1. Create a dummy model and scaler
    np.random.seed(42)
    X_dummy = np.random.normal(loc=0.0, scale=1.0, size=(100, 30))
    # Target Class: mostly 0 (legit), a few 1s (fraud)
    y_dummy = np.random.choice([0, 1], size=100, p=[0.9, 0.1])

    scaler = StandardScaler()
    X_scaled = scaler.fit(X_dummy) # Fit scaler
    X_scaled_arr = scaler.transform(X_dummy)
    
    model = LogisticRegression(random_state=42)
    model.fit(X_scaled_arr, y_dummy)

    # 2. Write model artifacts to disk under job_id folder
    job_dir = f"data/models/{job_id}"
    os.makedirs(job_dir, exist_ok=True)
    scaler_path = f"{job_dir}/scaler.joblib"
    model_path = f"{job_dir}/{model_name}.joblib"
    
    joblib.dump(scaler, scaler_path)
    joblib.dump(model, model_path)

    # 3. Save SQLite database records
    save_dataset_metadata(dataset_id, "mock.csv", 100, "valid")
    create_training_job(job_id, dataset_id)
    
    metrics = {
        "precision": 1.0, "recall": 0.8, "f1_score": 0.88,
        "roc_auc": 0.95, "pr_auc": 0.92, "confusion_matrix": [[90, 0], [2, 8]]
    }
    save_trained_model(job_id, dataset_id, model_name, metrics, model_path, scaler_path)

    try:
        # 4. Activate the dummy model
        act_res = client.post(f"/models/{model_id}/activate")
        assert act_res.status_code == 200

        # 5. Test single prediction POST /predict
        single_payload = {
            "Time": 1.0,
            "Amount": 50.0,
            # Assign features so that it yields valid float transformations
            **{f"V{i}": float(np.random.normal()) for i in range(1, 29)}
        }
        
        pred_res = client.post("/predict", json=single_payload)
        assert pred_res.status_code == 200
        
        pred_data = pred_res.json()
        assert "fraud_probability" in pred_data
        assert "risk_label" in pred_data
        assert pred_data["risk_label"] in ["Low", "Medium", "High"]
        assert "prediction_id" in pred_data
        assert len(pred_data["top_features"]) > 0

        # 6. Verify predictions log table in SQLite for the single prediction
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, model_id, prediction_type, input_summary, output FROM predictions WHERE prediction_type = 'single'")
        db_row = cursor.fetchone()
        conn.close()
        
        assert db_row is not None
        assert db_row[0] == pred_data["prediction_id"]
        assert db_row[1] == model_id
        assert "Amount" in db_row[3] # input summary has amount
        assert "fraud_probability" in db_row[4] # output has probability

        # 7. Test batch prediction POST /predict/batch
        # Generate 5 transaction rows matching standard features
        df_batch = pd.DataFrame(
            np.random.normal(size=(5, 30)),
            columns=["Time", "Amount"] + [f"V{i}" for i in range(1, 29)]
        )
        
        csv_buffer = io.StringIO()
        df_batch.to_csv(csv_buffer, index=False)
        csv_bytes = csv_buffer.getvalue().encode("utf-8")
        
        files = {"file": ("batch_transactions.csv", csv_bytes, "text/csv")}
        batch_res = client.post("/predict/batch", files=files)
        assert batch_res.status_code == 200
        assert batch_res.headers["Content-Disposition"].startswith("attachment; filename=")
        
        scored_csv = batch_res.text
        df_scored = pd.read_csv(io.StringIO(scored_csv))
        
        # Verify columns added
        assert len(df_scored) == 5
        assert "fraud_probability" in df_scored.columns
        assert "risk_label" in df_scored.columns
        assert df_scored["risk_label"].isin(["Low", "Medium", "High"]).all()

        # 8. Verify predictions log table in SQLite for the batch run
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT model_id, input_summary, output FROM predictions WHERE prediction_type = 'batch'")
        db_batch_row = cursor.fetchone()
        conn.close()
        
        assert db_batch_row is not None
        assert db_batch_row[0] == model_id
        assert "batch_transactions.csv" in db_batch_row[1]
        assert "processed_rows" in db_batch_row[2]

    finally:
        # Clean up files
        if os.path.exists(job_dir):
            shutil.rmtree(job_dir)
