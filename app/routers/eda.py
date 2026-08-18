from fastapi import APIRouter, HTTPException, Query
import os
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

from app.services.data_manager import data_manager
from app.services.eda import compute_eda

router = APIRouter(tags=["eda"])

def _get_eda_payload(df: pd.DataFrame) -> Dict[str, Any]:
    if df.empty:
        return {
            "total_rows": 0,
            "total_columns": len(df.columns),
            "fraud_count": 0,
            "legit_count": 0,
            "fraud_pct": 0.0,
            "missing_values": {},
            "column_types": {},
            "describe": {},
            "top_features": []
        }

    target_col = "Class" if "Class" in df.columns else df.columns[-1]
    
    total_rows = len(df)
    total_columns = len(df.columns)
    
    if target_col in df.columns:
        counts = df[target_col].value_counts().to_dict()
        fraud_count = int(counts.get(1, counts.get(1.0, 0)))
        legit_count = int(counts.get(0, counts.get(0.0, total_rows - fraud_count)))
    else:
        fraud_count = 0
        legit_count = total_rows
        
    fraud_pct = (fraud_count / total_rows * 100) if total_rows > 0 else 0.0
    
    missing_values = {col: int(val) for col, val in df.isnull().sum().to_dict().items()}
    column_types = {col: str(dtype) for col, dtype in df.dtypes.to_dict().items()}
    
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
            
    base_eda = {}
    try:
        base_eda = compute_eda(df)
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
        **base_eda
    }

@router.get("/eda/stats")
def get_eda_stats(dataset: Optional[str] = Query(None)):
    """
    Computes and returns EDA stats for a selected dataset filename or ID.
    """
    if not dataset:
        for folder in ["data/cleaned", "data/raw"]:
            if os.path.exists(folder):
                files = [f for f in os.listdir(folder) if f.endswith(".csv")]
                if files:
                    dataset = files[0]
                    break

    if not dataset:
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

    file_path = None
    for folder in ["data/cleaned", "data/raw"]:
        candidate = os.path.join(folder, dataset if dataset.endswith(".csv") else f"{dataset}.csv")
        if os.path.exists(candidate):
            file_path = candidate
            break

    if not file_path:
        # Fallback to any existing CSV file if requested file is missing
        for folder in ["data/cleaned", "data/raw"]:
            if os.path.exists(folder):
                files = [f for f in os.listdir(folder) if f.endswith(".csv")]
                if files:
                    file_path = os.path.join(folder, files[0])
                    break

    if not file_path:
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

    try:
        df = pd.read_csv(file_path, on_bad_lines="skip")
        return _get_eda_payload(df)
    except Exception:
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

@router.get("/eda/{dataset_id}")
def get_eda(dataset_id: str):
    return get_eda_stats(dataset=dataset_id)
