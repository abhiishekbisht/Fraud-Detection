from fastapi import APIRouter, HTTPException, Query, Header
import os
import pandas as pd
import numpy as np
import sqlite3
from typing import Dict, Any, Optional

from app.services.data_manager import data_manager
from app.services.eda import compute_eda
from app.services.database import get_db_connection, init_db

router = APIRouter(tags=["eda"])

def _default_sample_eda_payload() -> Dict[str, Any]:
    return {
        "total_rows": 284807,
        "total_columns": 31,
        "fraud_count": 492,
        "legit_count": 284315,
        "fraud_pct": 0.172,
        "missing_values": {
            "Time": 0, "Amount": 0, "Class": 0,
            **{f"V{i}": 0 for i in range(1, 29)}
        },
        "column_types": {
            "Time": "float64", "Amount": "float64", "Class": "int64",
            **{f"V{i}": "float64" for i in range(1, 29)}
        },
        "describe": {
            "Time": {"mean": 94813.86, "std": 47488.15, "min": 0.0, "max": 172792.0},
            "Amount": {"mean": 88.34, "std": 250.12, "min": 0.0, "max": 25691.16},
            "Class": {"mean": 0.0017, "std": 0.0415, "min": 0.0, "max": 1.0},
            "V14": {"mean": 0.0, "std": 0.958, "min": -19.21, "max": 10.52},
            "V17": {"mean": 0.0, "std": 0.849, "min": -25.16, "max": 9.25},
            "V12": {"mean": 0.0, "std": 0.999, "min": -18.68, "max": 7.84},
            "V10": {"mean": 0.0, "std": 0.988, "min": -24.59, "max": 23.74},
            "V11": {"mean": 0.0, "std": 1.02, "min": -4.79, "max": 12.02},
            "V4": {"mean": 0.0, "std": 1.01, "min": -5.41, "max": 16.87},
            "V2": {"mean": 0.0, "std": 1.65, "min": -56.41, "max": 22.06},
            "V7": {"mean": 0.0, "std": 1.23, "min": -43.56, "max": 34.30},
        },
        "top_features": [
            {"feature": "V14", "mean_legit": 0.012, "mean_fraud": -6.973, "mean_difference": 6.985},
            {"feature": "V17", "mean_legit": 0.011, "mean_fraud": -6.298, "mean_difference": 6.309},
            {"feature": "V12", "mean_legit": 0.009, "mean_fraud": -6.26, "mean_difference": 6.269},
            {"feature": "V10", "mean_legit": 0.006, "mean_fraud": -5.67, "mean_difference": 5.676},
            {"feature": "V11", "mean_legit": -0.005, "mean_fraud": 4.771, "mean_difference": 4.776},
            {"feature": "V4", "mean_legit": -0.007, "mean_fraud": 4.572, "mean_difference": 4.579},
            {"feature": "V2", "mean_legit": -0.005, "mean_fraud": 3.624, "mean_difference": 3.629},
            {"feature": "V7", "mean_legit": 0.004, "mean_fraud": -5.568, "mean_difference": 5.572},
        ]
    }

def _detect_target_col(df: pd.DataFrame) -> str:
    possible = ["class", "isfraud", "is_fraud", "target", "label", "fraud", "is_anomaly", "anomaly"]
    for col in df.columns:
        if str(col).lower() in possible:
            return col
    return df.columns[-1]

def _get_eda_payload(df: pd.DataFrame) -> Dict[str, Any]:
    if df.empty:
        return _default_sample_eda_payload()

    target_col = _detect_target_col(df)
    
    total_rows = len(df)
    total_columns = len(df.columns)
    
    fraud_count = 0
    legit_count = total_rows
    if target_col in df.columns:
        try:
            target_s = df[target_col]
            if not pd.api.types.is_numeric_dtype(target_s):
                target_s = target_s.astype(str).str.lower().isin(["1", "true", "fraud", "yes"]).astype(int)
            counts = target_s.value_counts().to_dict()
            fraud_count = int(counts.get(1, counts.get(1.0, 0)))
            legit_count = int(counts.get(0, counts.get(0.0, total_rows - fraud_count)))
        except Exception:
            fraud_count = 0
            legit_count = total_rows

    fraud_pct = (fraud_count / total_rows * 100) if total_rows > 0 else 0.0
    
    missing_values = {str(col): int(val) for col, val in df.isnull().sum().to_dict().items()}
    column_types = {str(col): str(dtype) for col, dtype in df.dtypes.to_dict().items()}
    
    numeric_df = df.select_dtypes(include=[np.number])
    describe = {}
    if not numeric_df.empty:
        desc_df = numeric_df.describe().T
        for col, row in desc_df.iterrows():
            describe[str(col)] = {
                "mean": float(row["mean"]) if pd.notna(row["mean"]) else 0.0,
                "std": float(row["std"]) if pd.notna(row["std"]) else 0.0,
                "min": float(row["min"]) if pd.notna(row["min"]) else 0.0,
                "max": float(row["max"]) if pd.notna(row["max"]) else 0.0,
            }

    # Calculate top discriminative features dynamically for any dataset
    top_features = []
    numeric_cols = [c for c in numeric_df.columns if c != target_col]
    if len(numeric_cols) > 0 and total_rows > 1:
        try:
            target_s = df[target_col]
            if not pd.api.types.is_numeric_dtype(target_s):
                target_s = target_s.astype(str).str.lower().isin(["1", "true", "fraud", "yes"]).astype(int)
            
            legit_mask = (target_s == 0)
            fraud_mask = (target_s == 1)

            diffs = []
            for col in numeric_cols:
                m_legit = float(df.loc[legit_mask, col].mean()) if legit_mask.any() else 0.0
                m_fraud = float(df.loc[fraud_mask, col].mean()) if fraud_mask.any() else 0.0
                m_diff = abs(m_fraud - m_legit)
                if pd.notna(m_diff):
                    diffs.append({
                        "feature": str(col),
                        "mean_legit": float(m_legit) if pd.notna(m_legit) else 0.0,
                        "mean_fraud": float(m_fraud) if pd.notna(m_fraud) else 0.0,
                        "mean_difference": float(m_diff)
                    })
            diffs.sort(key=lambda x: x["mean_difference"], reverse=True)
            top_features = diffs[:10]
        except Exception:
            pass

    return {
        "total_rows": total_rows,
        "total_columns": total_columns,
        "fraud_count": fraud_count,
        "legit_count": legit_count,
        "fraud_pct": float(fraud_pct),
        "missing_values": missing_values,
        "column_types": column_types,
        "describe": describe,
        "top_features": top_features
    }

def _empty_eda_payload() -> Dict[str, Any]:
    return {
        "total_rows": 0,
        "total_columns": 0,
        "fraud_count": 0,
        "legit_count": 0,
        "fraud_pct": 0.0,
        "missing_values": {},
        "column_types": {},
        "describe": {},
        "top_features": []
    }

@router.get("/eda/stats")
def get_eda_stats(
    dataset: Optional[str] = Query(None),
    x_session_id: Optional[str] = Header("global", alias="X-Session-ID")
):
    """
    Computes and returns EDA stats for a selected dataset belonging to the current session.
    Falls back to sample dataset stats if sample requested or in global session without dataset.
    """
    session_id = x_session_id or "global"
    
    if dataset and "sample" in str(dataset).lower():
        return _default_sample_eda_payload()

    clean_id = dataset.replace(".csv", "") if dataset else ""
    target_id = clean_id
    if dataset:
        try:
            init_db()
            with get_db_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                row = cursor.execute(
                    "SELECT id FROM datasets WHERE (id = ? OR filename = ? OR id = ? OR filename = ?) AND (session_id = ? OR session_id = 'global')",
                    (dataset, dataset, clean_id, f"{clean_id}.csv", session_id)
                ).fetchone()
                if row:
                    target_id = row["id"]
        except Exception:
            pass

    file_path = None
    if target_id:
        for folder in ["data/cleaned", "data/raw"]:
            candidate = os.path.join(folder, f"{target_id}.csv")
            if os.path.exists(candidate):
                file_path = candidate
                break

    if file_path:
        try:
            df = pd.read_csv(file_path, on_bad_lines="skip")
            return _get_eda_payload(df)
        except Exception:
            pass

    if session_id == "global" and not dataset:
        return _default_sample_eda_payload()

    return _empty_eda_payload()

@router.get("/eda/{dataset_id}")
def get_eda(dataset_id: str, x_session_id: Optional[str] = Header("global", alias="X-Session-ID")):
    return get_eda_stats(dataset=dataset_id, x_session_id=x_session_id)

