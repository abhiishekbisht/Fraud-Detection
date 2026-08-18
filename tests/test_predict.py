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
    Simulates training a dummy model, activating it, and running single/batch inference,
    including SHAP explanation and prediction history query evaluations.
    """
    dataset_id = "test_predict_dataset"
    job_id = "test_predict_job"
    model_name = "logistic_regression"
    model_id = f"{job_id}_{model_name}"

    # 1. Create a dummy model and scaler
    np.random.seed(42)
    X_dummy = np.random.normal(loc=0.0, scale=1.0, size=(100, 30))
    y_dummy = np.random.choice([0, 1], size=100, p=[0.9, 0.1])

    scaler = StandardScaler()
    scaler.fit(X_dummy)
    X_scaled_arr = scaler.transform(X_dummy)
    
    model = LogisticRegression(random_state=42)
    model.fit(X_scaled_arr, y_dummy)

    # Save cleaned training data so that LinearExplainer background data loading works
    os.makedirs("data/cleaned", exist_ok=True)
    df_cleaned = pd.DataFrame(X_dummy, columns=["Time", "Amount"] + [f"V{i}" for i in range(1, 29)])
    df_cleaned.to_csv(f"data/cleaned/{dataset_id}.csv", index=False)

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
            **{f"V{i}": float(np.random.normal()) for i in range(1, 29)}
        }
        
        pred_res = client.post("/predict", json=single_payload)
        assert pred_res.status_code == 200
        
        pred_data = pred_res.json()
        assert "fraud_probability" in pred_data
        assert "risk_label" in pred_data
        assert "prediction_id" in pred_data
        
        # Verify SHAP value schema format in single prediction output
        top_features = pred_data["top_features"]
        assert len(top_features) == 3
        for tf in top_features:
            assert "feature" in tf
            assert "shap_value" in tf
            assert "effect" in tf
            assert tf["effect"] in ["increases", "decreases"]

        # 6. Test GET /explain/{prediction_id} (Full SHAP breakdown)
        pred_id = pred_data["prediction_id"]
        explain_res = client.get(f"/explain/{pred_id}")
        assert explain_res.status_code == 200
        
        explain_data = explain_res.json()
        assert explain_data["prediction_id"] == pred_id
        assert explain_data["model_id"] == model_id
        assert "base_value" in explain_data
        assert "prediction_probability" in explain_data
        assert explain_data["risk_label"] == pred_data["risk_label"]
        
        shap_values = explain_data["shap_values"]
        assert len(shap_values) == 30 # all 30 features
        
        # Verify sorted descending by absolute value
        for i in range(len(shap_values) - 1):
            assert abs(shap_values[i]["shap_value"]) >= abs(shap_values[i+1]["shap_value"])

        # 7. Test batch prediction POST /predict/batch
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
        
        scored_csv = batch_res.text
        df_scored = pd.read_csv(io.StringIO(scored_csv))
        assert len(df_scored) == 5
        assert "fraud_probability" in df_scored.columns
        assert "risk_label" in df_scored.columns

        # 8. Test GET /predict/history paginated log history endpoint
        history_res = client.get("/predict/history?page=1&limit=10")
        assert history_res.status_code == 200
        
        hist_data = history_res.json()
        assert "predictions" in hist_data
        assert "total_count" in hist_data
        assert hist_data["total_count"] >= 2 # 1 single + 1 batch logged
        
        # Test filters
        low_risk_res = client.get(f"/predict/history?risk_label={pred_data['risk_label']}")
        assert low_risk_res.status_code == 200
        low_data = low_risk_res.json()
        assert len(low_data["predictions"]) >= 1

    finally:
        # Clean up files
        if os.path.exists(job_dir):
            shutil.rmtree(job_dir)
        cleaned_csv = f"data/cleaned/{dataset_id}.csv"
        if os.path.exists(cleaned_csv):
            os.remove(cleaned_csv)
