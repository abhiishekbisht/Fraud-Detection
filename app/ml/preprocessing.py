import os
import joblib
import pandas as pd
import numpy as np
from typing import Tuple, Optional
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from imblearn.over_sampling import SMOTE

MODELS_DIR = "data/models"

def apply_auto_pca_if_needed(
    df: pd.DataFrame, 
    target_col: str = "Class", 
    dataset_id: str = "custom"
) -> Tuple[pd.DataFrame, Optional[PCA]]:
    """
    If dataset lacks V1..V28 columns, automatically applies PCA to convert raw numeric features into V1..V28.
    """
    has_v_cols = any(f"V{i}" in df.columns for i in range(1, 10))
    if has_v_cols:
        return df, None

    numeric_cols = [c for c in df.select_dtypes(include=[np.number]).columns if c != target_col and str(c).lower() not in ["time", "amount"]]
    if len(numeric_cols) < 2:
        return df, None

    n_comp = min(28, len(numeric_cols))
    X_num = df[numeric_cols].fillna(df[numeric_cols].median())
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_num)
    
    pca = PCA(n_components=n_comp, random_state=42)
    X_pca = pca.fit_transform(X_scaled)
    
    pca_cols = [f"V{i+1}" for i in range(n_comp)]
    df_pca = pd.DataFrame(X_pca, columns=pca_cols, index=df.index)
    
    for col in ["Time", "Amount", target_col]:
        if col in df.columns:
            df_pca[col] = df[col]

    os.makedirs(MODELS_DIR, exist_ok=True)
    pca_artifact_path = os.path.join(MODELS_DIR, f"{dataset_id}_pca.joblib")
    joblib.dump({"scaler": scaler, "pca": pca, "feature_cols": numeric_cols}, pca_artifact_path)

    return df_pca, pca

def preprocess_dataset(
    df: pd.DataFrame, 
    dataset_id: str, 
    target_col: str = "Class",
    scaler_path: Optional[str] = None
) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
    """
    Takes a dataset DataFrame, automatically applies PCA if raw custom features are present,
    does a stratified train/test split (80/20, stratify on target_col), scales numeric features, and
    applies SMOTE to the training set only.
    """
    # Detect target column dynamically if default target_col is not present
    possible_targets = ["class", "isfraud", "is_fraud", "target", "label", "fraud", "is_anomaly"]
    if target_col not in df.columns:
        for c in df.columns:
            if str(c).lower() in possible_targets:
                target_col = c
                break

    if target_col not in df.columns:
        target_col = df.columns[-1]

    # Auto-apply PCA transformation if raw custom feature columns exist
    df_proc, _ = apply_auto_pca_if_needed(df, target_col=target_col, dataset_id=dataset_id)

    standard_cols = ["Time", "Amount"] + [f"V{i}" for i in range(1, 29)]
    engineered_cols = ["HourOfDay", "Hour_Sin", "Hour_Cos", "LogAmount", "Amount_to_Mean_Ratio", "Amount_outlier"]
    
    all_possible = standard_cols + engineered_cols
    feature_cols = [col for col in all_possible if col in df_proc.columns]

    if not feature_cols:
        feature_cols = [col for col in df_proc.select_dtypes(include=[np.number]).columns if col != target_col]

    if not feature_cols:
        raise ValueError(f"Dataset does not contain any valid feature columns for training.")

    X = df_proc[feature_cols].copy()
    y_raw = df_proc[target_col].copy()

    # Convert y target to numeric 0/1 if categorical/boolean
    if not pd.api.types.is_numeric_dtype(y_raw):
        y = y_raw.astype(str).str.lower().isin(["1", "true", "fraud", "yes"]).astype(int)
    else:
        y = y_raw.astype(int)

    # 2. Stratified train/test split (80/20)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, stratify=y if len(y.unique()) > 1 else None, random_state=42
    )

    # 3. Scale numeric features with StandardScaler (fit only on train)
    scaler = StandardScaler()
    
    X_train_scaled_arr = scaler.fit_transform(X_train)
    X_test_scaled_arr = scaler.transform(X_test)

    X_train_scaled = pd.DataFrame(X_train_scaled_arr, columns=feature_cols, index=X_train.index)
    X_test_scaled = pd.DataFrame(X_test_scaled_arr, columns=feature_cols, index=X_test.index)

    # 4. Save fitted scaler as an artifact
    if scaler_path is None:
        os.makedirs(MODELS_DIR, exist_ok=True)
        scaler_path = os.path.join(MODELS_DIR, f"{dataset_id}_scaler.joblib")
    else:
        scaler_parent_dir = os.path.dirname(scaler_path)
        if scaler_parent_dir:
            os.makedirs(scaler_parent_dir, exist_ok=True)
            
    joblib.dump(scaler, scaler_path)

    # 5. Apply SMOTE resampler if class imbalance present
    if len(y_train.unique()) > 1 and y_train.value_counts().min() > 1:
        try:
            smote = SMOTE(random_state=42)
            X_train_res_arr, y_train_res = smote.fit_resample(X_train_scaled, y_train)
        except Exception:
            X_train_res_arr, y_train_res = X_train_scaled, y_train
    else:
        X_train_res_arr, y_train_res = X_train_scaled, y_train
    
    if isinstance(X_train_res_arr, pd.DataFrame):
        X_train_res = X_train_res_arr.copy()
        X_train_res.columns = feature_cols
    else:
        X_train_res = pd.DataFrame(X_train_res_arr, columns=feature_cols)

    return X_train_res, y_train_res, X_test_scaled, y_test
