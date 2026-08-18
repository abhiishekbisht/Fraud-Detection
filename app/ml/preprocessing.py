import os
import pandas as pd
from typing import Tuple
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from imblearn.over_sampling import SMOTE
import joblib

MODELS_DIR = "data/models"

def preprocess_dataset(
    df: pd.DataFrame, 
    dataset_id: str, 
    target_col: str = "Class"
) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
    """
    Takes a cleaned dataset DataFrame, does a stratified train/test split (80/20, stratify on target_col),
    scales numeric features with StandardScaler (fitted only on train), and
    applies SMOTE to the training set only (leaving the test set untouched).
    Saves the fitted scaler as a joblib artifact.

    Returns:
        X_train_res: Balanced, scaled training features DataFrame
        y_train_res: Balanced training target labels Series
        X_test_scaled: Scaled test features DataFrame
        y_test: Unchanged test target labels Series
    """
    # 1. Define feature columns (Time, Amount, V1-V28)
    feature_cols = ["Time", "Amount"] + [f"V{i}" for i in range(1, 29)]
    
    # Ensure all required features and target are present in the dataframe
    missing_cols = [col for col in feature_cols + [target_col] if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Dataset is missing required columns for preprocessing: {missing_cols}")

    X = df[feature_cols].copy()
    y = df[target_col].copy()

    # 2. Stratified train/test split (80/20)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, stratify=y, random_state=42
    )

    # 3. Scale numeric features with StandardScaler (fit only on train)
    scaler = StandardScaler()
    
    # fit_transform on train, transform on test
    X_train_scaled_arr = scaler.fit_transform(X_train)
    X_test_scaled_arr = scaler.transform(X_test)

    # Reconstruct DataFrames to keep column names and index structures
    X_train_scaled = pd.DataFrame(X_train_scaled_arr, columns=feature_cols, index=X_train.index)
    X_test_scaled = pd.DataFrame(X_test_scaled_arr, columns=feature_cols, index=X_test.index)

    # 4. Save fitted scaler as an artifact
    os.makedirs(MODELS_DIR, exist_ok=True)
    scaler_path = os.path.join(MODELS_DIR, f"{dataset_id}_scaler.joblib")
    joblib.dump(scaler, scaler_path)

    # 5. Apply SMOTE resampler to the training set only
    smote = SMOTE(random_state=42)
    X_train_res_arr, y_train_res = smote.fit_resample(X_train_scaled, y_train)
    
    # Ensure resampled features are returned as a DataFrame with correct columns
    X_train_res = pd.DataFrame(X_train_res_arr, columns=feature_cols)

    return X_train_res, y_train_res, X_test_scaled, y_test
