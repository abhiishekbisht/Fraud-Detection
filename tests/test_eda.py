import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.data_manager import data_manager
from app.services.eda import compute_eda

client = TestClient(app)

def generate_synthetic_dataset(n_samples: int = 200, fraud_ratio: float = 0.1) -> pd.DataFrame:
    """
    Generates a synthetic fraud detection dataset matching the standard Kaggle columns.
    """
    np.random.seed(42)
    n_fraud = int(n_samples * fraud_ratio)
    n_legit = n_samples - n_fraud
    
    # Class labels
    classes = np.array([0] * n_legit + [1] * n_fraud)
    
    # Transaction amounts: legit amounts are generally smaller, fraud are larger
    amounts_legit = np.random.exponential(scale=50, size=n_legit)
    amounts_fraud = np.random.exponential(scale=400, size=n_fraud)
    amounts = np.concatenate([amounts_legit, amounts_fraud])
    
    # Times
    times = np.random.uniform(0, 86400, size=n_samples)
    
    # V1 to V28 features
    features = {}
    for i in range(1, 29):
        if i == 17:
            # V17 has a large mean difference (legit mean=0, fraud mean=-8)
            feat_legit = np.random.normal(loc=0.0, scale=1.0, size=n_legit)
            feat_fraud = np.random.normal(loc=-8.0, scale=2.0, size=n_fraud)
        elif i == 4:
            # V4 has a moderate mean difference (legit mean=0, fraud mean=4)
            feat_legit = np.random.normal(loc=0.0, scale=1.0, size=n_legit)
            feat_fraud = np.random.normal(loc=4.0, scale=1.5, size=n_fraud)
        else:
            # Other features have similar means (both mean=0)
            feat_legit = np.random.normal(loc=0.0, scale=1.0, size=n_legit)
            feat_fraud = np.random.normal(loc=0.0, scale=1.0, size=n_fraud)
            
        features[f"V{i}"] = np.concatenate([feat_legit, feat_fraud])
        
    df = pd.DataFrame(features)
    df["Time"] = times
    df["Amount"] = amounts
    df["Class"] = classes
    
    # Shuffle dataset
    df = df.sample(frac=1.0, random_state=42).reset_index(drop=True)
    return df


def test_compute_eda_logic():
    """
    Directly tests the EDA calculation service logic.
    """
    df = generate_synthetic_dataset(n_samples=200, fraud_ratio=0.1)
    results = compute_eda(df)
    
    # 1. Class Balance checks
    assert "class_balance" in results
    cb = results["class_balance"]
    assert cb["counts"]["legit"] == 180
    assert cb["counts"]["fraud"] == 20
    assert abs(cb["percentages"]["legit"] - 90.0) < 1e-5
    assert abs(cb["percentages"]["fraud"] - 10.0) < 1e-5
    
    # 2. Amount Stats checks
    assert "amount_stats" in results
    amount_stats = results["amount_stats"]
    assert "legit" in amount_stats
    assert "fraud" in amount_stats
    
    # Fraud mean should be significantly larger than legit mean due to exponential scale
    assert amount_stats["fraud"]["mean"] > amount_stats["legit"]["mean"]
    assert "percentiles" in amount_stats["legit"]
    assert "50" in amount_stats["legit"]["percentiles"]
    
    # 3. Correlation Matrix checks
    assert "correlation_matrix" in results
    corr = results["correlation_matrix"]
    assert "Class" in corr
    assert "Amount" in corr
    # Self correlation must be 1.0 (or very close)
    assert abs(corr["Class"]["Class"] - 1.0) < 1e-5
    assert abs(corr["Amount"]["Amount"] - 1.0) < 1e-5
    
    # 4. Top Features checks
    assert "top_features" in results
    top_feats = results["top_features"]
    assert len(top_feats) <= 10
    
    # V17 and V4 should be ranked highly as they were generated with large mean differences
    top_feature_names = [f["feature"] for f in top_feats]
    assert "V17" in top_feature_names
    assert "V4" in top_feature_names
    
    # First item should be V17 because it has the largest absolute mean difference (~8)
    assert top_feats[0]["feature"] == "V17"


def test_eda_api_endpoint():
    """
    Tests the FastAPI GET /eda/{dataset_id} endpoint.
    """
    from app.services.database import save_cleaning_report, save_dataset_metadata, delete_dataset_metadata
    
    dataset_id = "test_creditcard_dataset"
    df = generate_synthetic_dataset(n_samples=200, fraud_ratio=0.1)
    
    try:
        # Save a mock dataset record to datasets table
        save_dataset_metadata(dataset_id, "mock_creditcard.csv", 200, "valid")
        
        # Save a mock cleaning report to SQLite to satisfy the "must be cleaned" check
        save_cleaning_report(
            dataset_id=dataset_id,
            rows_before=200,
            rows_after=200,
            duplicates_removed=0,
            missing_value_summary={},
            outliers_flagged=0
        )
        
        # Register dataset directly into data manager
        data_manager.register_dataset(dataset_id, df)
        
        # Query endpoint
        response = client.get(f"/eda/{dataset_id}")
        assert response.status_code == 200
        
        data = response.json()
        
        # Validate the four sections exist
        assert "class_balance" in data
        assert "amount_stats" in data
        assert "correlation_matrix" in data
        assert "top_features" in data
        
        # Validate structure and sanity of class balance
        assert data["class_balance"]["counts"]["legit"] == 180
        assert data["class_balance"]["counts"]["fraud"] == 20
        assert data["class_balance"]["percentages"]["fraud"] == 10.0
        
        # Validate structure of amount stats
        assert "mean" in data["amount_stats"]["legit"]
        assert "percentiles" in data["amount_stats"]["legit"]
        assert data["amount_stats"]["fraud"]["mean"] > data["amount_stats"]["legit"]["mean"]
        
        # Validate correlation matrix column list
        assert "Class" in data["correlation_matrix"]
        assert "Amount" in data["correlation_matrix"]
        
        # Validate top features list
        assert len(data["top_features"]) == 10
        assert data["top_features"][0]["feature"] == "V17"
        assert data["top_features"][0]["mean_difference"] > 7.0
    finally:
        # Clean up database and data manager cache
        delete_dataset_metadata(dataset_id)
        data_manager.delete_dataset(dataset_id)


def test_eda_api_endpoint_uncleaned():
    """
    Tests GET /eda/{dataset_id} on an uncleaned dataset. Should yield a 400 Bad Request error.
    """
    from app.services.database import save_dataset_metadata, delete_dataset_metadata
    
    dataset_id = "uncleaned_dataset"
    df = generate_synthetic_dataset(n_samples=100, fraud_ratio=0.1)
    
    try:
        # Save a mock dataset record to datasets table
        save_dataset_metadata(dataset_id, "mock_uncleaned.csv", 100, "valid")
        
        # Register dataset directly, but do NOT write a cleaning report to SQLite
        data_manager.register_dataset(dataset_id, df)
        
        # Query eda endpoint
        response = client.get(f"/eda/{dataset_id}")
        assert response.status_code == 400
        assert "has not been cleaned" in response.json()["detail"].lower()
    finally:
        # Clean up
        delete_dataset_metadata(dataset_id)
        data_manager.delete_dataset(dataset_id)


def test_eda_api_endpoint_not_found():
    """
    Tests GET /eda/{dataset_id} for a non-existent dataset.
    """
    response = client.get("/eda/non_existent_id")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
