import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.database import (
    save_dataset_metadata,
    create_training_job,
    save_trained_model,
    delete_dataset_metadata,
    get_active_model
)

client = TestClient(app)

def test_models_endpoints_workflow():
    """
    Tests GET /models (listing & sorting) and POST /models/{model_id}/activate workflows.
    """
    dataset_id = "test_models_dataset"
    job_id = "test_models_job"
    
    # 1. Setup mock records in SQLite
    save_dataset_metadata(dataset_id, "mock_data.csv", 500, "valid")
    create_training_job(job_id, dataset_id)
    
    # Insert 3 models with different PR-AUC values to test sorting
    # Model IDs will be test_models_job_lr, test_models_job_rf, and test_models_job_xgb
    metrics_lr = {
        "precision": 0.82, "recall": 0.80, "f1_score": 0.81, 
        "roc_auc": 0.88, "pr_auc": 0.85, "confusion_matrix": [[40, 5], [2, 10]]
    }
    metrics_rf = {
        "precision": 0.94, "recall": 0.90, "f1_score": 0.92, 
        "roc_auc": 0.97, "pr_auc": 0.95, "confusion_matrix": [[42, 3], [1, 11]]
    }
    metrics_xgb = {
        "precision": 0.75, "recall": 0.70, "f1_score": 0.72, 
        "roc_auc": 0.81, "pr_auc": 0.75, "confusion_matrix": [[38, 7], [3, 9]]
    }
    
    try:
        save_trained_model(job_id, dataset_id, "lr", metrics_lr, "data/models/lr.joblib", "data/models/scaler.joblib")
        save_trained_model(job_id, dataset_id, "rf", metrics_rf, "data/models/rf.joblib", "data/models/scaler.joblib")
        save_trained_model(job_id, dataset_id, "xgb", metrics_xgb, "data/models/xgb.joblib", "data/models/scaler.joblib")
        
        # 2. Test GET /models returns list sorted by PR-AUC descending
        response = client.get("/models")
        assert response.status_code == 200
        
        models = response.json()
        
        # Filter models to only include our test job models
        test_models = [m for m in models if m["job_id"] == job_id]
        assert len(test_models) == 3
        
        # Verify PR-AUC descending order (0.95 -> 0.85 -> 0.75)
        assert test_models[0]["name"] == "rf"
        assert test_models[0]["pr_auc"] == 0.95
        assert test_models[0]["is_active"] is False
        
        assert test_models[1]["name"] == "lr"
        assert test_models[1]["pr_auc"] == 0.85
        assert test_models[1]["is_active"] is False
        
        assert test_models[2]["name"] == "xgb"
        assert test_models[2]["pr_auc"] == 0.75
        assert test_models[2]["is_active"] is False
        
        # 3. Verify POST /models/{model_id}/activate marks it active
        best_model_id = f"{job_id}_rf"
        activate_response = client.post(f"/models/{best_model_id}/activate")
        assert activate_response.status_code == 200
        
        act_data = activate_response.json()
        assert act_data["is_active"] is True
        assert act_data["model_id"] == best_model_id
        
        # 4. Verify get_active_model() returns the active model run
        active_model = get_active_model()
        assert active_model is not None
        assert active_model["model_id"] == best_model_id
        assert active_model["is_active"] is True
        
        # 5. Query GET /models again to verify is_active states updated correctly
        response = client.get("/models")
        models = response.json()
        test_models = [m for m in models if m["job_id"] == job_id]
        
        # rf should now be active, others inactive
        rf_model = next(m for m in test_models if m["name"] == "rf")
        assert rf_model["is_active"] is True
        
        lr_model = next(m for m in test_models if m["name"] == "lr")
        assert lr_model["is_active"] is False
        
        xgb_model = next(m for m in test_models if m["name"] == "xgb")
        assert xgb_model["is_active"] is False
        
        # 6. Activating non-existent model returns 404
        bad_response = client.post("/models/invalid_model_run_id/activate")
        assert bad_response.status_code == 404
        assert "not found" in bad_response.json()["detail"].lower()

    finally:
        # Cleanup SQLite
        delete_dataset_metadata(dataset_id)
