import os
import time
import shutil
import pytest
import pandas as pd
import numpy as np
from fastapi.testclient import TestClient

from app.main import app
from app.services.data_manager import data_manager
from app.services.database import (
    save_dataset_metadata,
    save_cleaning_report,
    delete_dataset_metadata
)

client = TestClient(app)

def generate_synthetic_dataset(n_samples: int = 200, fraud_ratio: float = 0.1) -> pd.DataFrame:
    """
    Generates a synthetic dataset matching Kaggle Credit Card columns.
    """
    np.random.seed(42)
    n_fraud = int(n_samples * fraud_ratio)
    n_legit = n_samples - n_fraud
    
    classes = np.array([0] * n_legit + [1] * n_fraud)
    amounts = np.random.exponential(scale=50, size=n_samples)
    times = np.random.uniform(0, 86400, size=n_samples)
    
    features = {}
    for i in range(1, 29):
        features[f"V{i}"] = np.random.normal(loc=0.0, scale=1.0, size=n_samples)
        
    df = pd.DataFrame(features)
    df["Time"] = times
    df["Amount"] = amounts
    df["Class"] = classes
    
    df = df.sample(frac=1.0, random_state=42).reset_index(drop=True)
    return df


def test_train_endpoints_validation():
    """
    Verifies that start training validates dataset existence and cleaning report requirements.
    """
    # 1. Non-existent dataset
    response = client.post("/train/non_existent_dataset_id")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

    # 2. Uncleaned dataset (has metadata but no cleaning report)
    dataset_id = "uncleaned_test_dataset"
    df = generate_synthetic_dataset(n_samples=50)
    
    try:
        save_dataset_metadata(dataset_id, "mock_raw.csv", 50, "valid")
        data_manager.register_dataset(dataset_id, df)
        
        response = client.post(f"/train/{dataset_id}")
        assert response.status_code == 400
        assert "has not been cleaned" in response.json()["detail"].lower()
    finally:
        delete_dataset_metadata(dataset_id)
        data_manager.delete_dataset(dataset_id)


def test_train_pipeline_success():
    """
    Tests POST /train/{dataset_id} execution and status polling GET /train/status/{job_id}.
    Verifies metric calculation correctness and best model selection.
    """
    dataset_id = "test_train_dataset"
    df = generate_synthetic_dataset(n_samples=250, fraud_ratio=0.1) # 25 fraud, 225 legit
    
    # Setup test dataset files & metadata
    os.makedirs("data/cleaned", exist_ok=True)
    cleaned_path = f"data/cleaned/{dataset_id}.csv"
    df.to_csv(cleaned_path, index=False)
    
    save_dataset_metadata(dataset_id, "mock.csv", len(df), "valid")
    save_cleaning_report(
        dataset_id=dataset_id,
        rows_before=len(df),
        rows_after=len(df),
        duplicates_removed=0,
        missing_value_summary={},
        outliers_flagged=0
    )
    
    data_manager.register_dataset(dataset_id, df)
    
    job_id = None
    try:
        # 1. Initiate training
        start_response = client.post(f"/train/{dataset_id}")
        assert start_response.status_code == 202
        
        start_data = start_response.json()
        assert "job_id" in start_data
        assert start_data["status"] == "queued"
        
        job_id = start_data["job_id"]
        
        # 2. Poll progress status endpoint
        max_retries = 30
        status = "queued"
        poll_data = {}
        
        for _ in range(max_retries):
            status_response = client.get(f"/train/status/{job_id}")
            assert status_response.status_code == 200
            poll_data = status_response.json()
            status = poll_data["status"]
            
            if status in ["done", "failed"]:
                break
            time.sleep(0.5)
            
        # Assert training completed successfully
        assert status == "done"
        
        # 3. Verify metrics and best model recommendation
        assert "models" in poll_data
        models = poll_data["models"]
        
        # Verify all 3 models are present
        for name in ["logistic_regression", "random_forest", "xgboost"]:
            assert name in models
            m_metrics = models[name]
            assert "precision" in m_metrics
            assert "recall" in m_metrics
            assert "f1_score" in m_metrics
            assert "roc_auc" in m_metrics
            assert "pr_auc" in m_metrics
            assert "confusion_matrix" in m_metrics
            assert len(m_metrics["confusion_matrix"]) == 2 # 2x2
            assert os.path.exists(m_metrics["model_path"])
            assert os.path.exists(m_metrics["scaler_path"])
            
        assert "best_model" in poll_data
        best_model = poll_data["best_model"]
        assert best_model in ["logistic_regression", "random_forest", "xgboost"]
        
        # Best model should have the highest PR-AUC
        expected_best = max(models.keys(), key=lambda k: models[k]["pr_auc"])
        assert best_model == expected_best
        
        assert "recommendation_reason" in poll_data
        
        # 4. Verify artifact directory contains scaler and models
        job_dir = f"data/models/{job_id}"
        assert os.path.exists(job_dir)
        assert os.path.exists(f"{job_dir}/scaler.joblib")
        assert os.path.exists(f"{job_dir}/logistic_regression.joblib")
        assert os.path.exists(f"{job_dir}/random_forest.joblib")
        assert os.path.exists(f"{job_dir}/xgboost.joblib")
        
    finally:
        # Database & Cache cleanup
        delete_dataset_metadata(dataset_id)
        data_manager.delete_dataset(dataset_id)
        
        # Artifact file & directory cleanups
        if job_id:
            job_dir = f"data/models/{job_id}"
            if os.path.exists(job_dir):
                shutil.rmtree(job_dir)
        if os.path.exists(cleaned_path):
            os.remove(cleaned_path)
