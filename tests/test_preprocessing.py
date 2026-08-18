import os
import joblib
import pytest
import pandas as pd
import numpy as np
from app.ml.preprocessing import preprocess_dataset

def generate_imbalanced_dataset(n_samples: int = 1000, fraud_ratio: float = 0.05) -> pd.DataFrame:
    """
    Generates a synthetic imbalanced dataset with Kaggle columns.
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
    
    # Shuffle
    df = df.sample(frac=1.0, random_state=42).reset_index(drop=True)
    return df

def test_preprocess_dataset_logic():
    """
    Tests preprocessing workflow (splitting, scaling, SMOTE resampling, and artifact saving).
    """
    dataset_id = "test_preprocess_id"
    df = generate_imbalanced_dataset(n_samples=1000, fraud_ratio=0.05) # 950 legit, 50 fraud

    # Track distributions before resample
    # Stratified split: 80% train, 20% test.
    # Train set should have: 950 * 0.8 = 760 legit, 50 * 0.8 = 40 fraud.
    # Test set should have: 950 * 0.2 = 190 legit, 50 * 0.2 = 10 fraud.
    
    try:
        X_train_res, y_train_res, X_test_scaled, y_test = preprocess_dataset(df, dataset_id)

        # 1. Verification of splits & dimensions
        assert X_train_res.shape[1] == 30
        assert X_test_scaled.shape[1] == 30
        assert len(X_test_scaled) == 200 # 20% of 1000
        assert len(y_test) == 200
        
        # 2. Verify target distributions (Before Resample in training split: 760 vs 40)
        # Resampled target (y_train_res) must be exactly balanced (760 legit, 760 fraud)
        counts_train = y_train_res.value_counts()
        assert counts_train[0] == 760
        assert counts_train[1] == 760
        assert len(X_train_res) == 1520 # 760 + 760
        assert len(y_train_res) == 1520
        
        # 3. Resampled test split (y_test) must NOT be balanced (190 legit, 10 fraud)
        counts_test = y_test.value_counts()
        assert counts_test[0] == 190
        assert counts_test[1] == 10

        # 4. Verify StandardScaler artifact exists and loads correctly
        scaler_path = f"data/models/{dataset_id}_scaler.joblib"
        assert os.path.exists(scaler_path)
        
        scaler = joblib.load(scaler_path)
        from sklearn.preprocessing import StandardScaler
        assert isinstance(scaler, StandardScaler)
        
        # Verify scaling is actually computed (mean_ should be populated)
        assert hasattr(scaler, "mean_")
        assert len(scaler.mean_) == 30

        # Print outputs to console to fulfill instruction
        print("\n=== CLASS DISTRIBUTION SUMMARY ===")
        print(f"Original Dataset: {len(df)} rows ({df['Class'].sum()} Fraud, {len(df) - df['Class'].sum()} Legit)")
        print(f"Training split (before SMOTE): 800 rows (40 Fraud, 760 Legit)")
        print(f"Training split (after SMOTE):  {len(y_train_res)} rows ({counts_train[1]} Fraud, {counts_train[0]} Legit)")
        print(f"Test split (untouched by SMOTE): {len(y_test)} rows ({counts_test[1]} Fraud, {counts_test[0]} Legit)")
        print("==================================\n")

    finally:
        # Cleanup artifact from disk
        scaler_path = f"data/models/{dataset_id}_scaler.joblib"
        if os.path.exists(scaler_path):
            os.remove(scaler_path)
