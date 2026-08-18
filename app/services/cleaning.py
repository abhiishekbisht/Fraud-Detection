import pandas as pd
import numpy as np
import os
from typing import Dict, Any

from app.routers.upload import REQUIRED_COLUMNS

def clean_dataset(dataset_id: str) -> Dict[str, Any]:
    """
    Loads raw CSV, cleans it, performs advanced feature engineering,
    saves it to data/cleaned/, and returns a cleaning report.
    
    Cleaning & Feature Engineering steps:
    1. Report missing value percentages per column (calculated on raw).
    2. Drop exact duplicate rows.
    3. Coerce standard numeric columns to float.
    4. Calculate Amount outlier flag using IQR bounds.
    5. Advanced Feature Engineering:
       - HourOfDay = (Time // 3600) % 24
       - Hour_Sin = sin(2 * pi * HourOfDay / 24)
       - Hour_Cos = cos(2 * pi * HourOfDay / 24)
       - LogAmount = log1p(Amount)
       - Amount_to_Mean_Ratio = Amount / (mean(Amount) + 1e-5)
       - Amount_outlier = outlier_mask.astype(int)
    6. Save cleaned CSV.
    """
    raw_path = f"data/raw/{dataset_id}.csv"
    cleaned_dir = "data/cleaned"
    cleaned_path = f"{cleaned_dir}/{dataset_id}.csv"
    
    if not os.path.exists(raw_path):
        raise FileNotFoundError(f"Raw dataset file not found at {raw_path}")
        
    df = pd.read_csv(raw_path)
    rows_before = len(df)
    
    # 1. Missing values summary
    missing_value_summary = (df.isnull().mean() * 100).to_dict()
    missing_value_summary = {str(k): float(round(v, 4)) for k, v in missing_value_summary.items()}
    
    # 2. Drop duplicates
    duplicates_removed = int(df.duplicated().sum())
    df = df.drop_duplicates().reset_index(drop=True)
    
    # 3. Coerce standard types first
    for col in REQUIRED_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            if col in ["Class", "Time"]:
                try:
                    df[col] = df[col].astype("Int64")
                except Exception:
                    pass

    # 4. Amount Outlier Flagging using IQR
    outliers_flagged = 0
    outlier_mask = pd.Series([False] * len(df))
    if "Amount" in df.columns:
        q1 = df["Amount"].quantile(0.25)
        q3 = df["Amount"].quantile(0.75)
        iqr = q3 - q1
        
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        outlier_mask = (df["Amount"] < lower_bound) | (df["Amount"] > upper_bound)
        outliers_flagged = int(outlier_mask.sum())
    
    # 5. Advanced Feature Engineering (Industry level)
    # A. Cyclical time encoding
    df["HourOfDay"] = ((df["Time"].fillna(0).astype(float) // 3600) % 24).astype(float)
    df["Hour_Sin"] = np.sin(2 * np.pi * df["HourOfDay"] / 24.0).astype(float)
    df["Hour_Cos"] = np.cos(2 * np.pi * df["HourOfDay"] / 24.0).astype(float)
    
    # B. Normalized/log transformed amount
    df["LogAmount"] = np.log1p(df["Amount"].fillna(0).astype(float)).astype(float)
    
    # C. Transaction velocity/ratio feature
    mean_amt = df["Amount"].fillna(0).astype(float).mean()
    df["Amount_to_Mean_Ratio"] = (df["Amount"].fillna(0).astype(float) / (mean_amt + 1e-5)).astype(float)
    
    # D. Binary outlier column
    df["Amount_outlier"] = outlier_mask.astype(int)

    # 6. Save cleaned file to data/cleaned/
    os.makedirs(cleaned_dir, exist_ok=True)
    df.to_csv(cleaned_path, index=False)
    
    rows_after = len(df)
    
    return {
        "rows_before": rows_before,
        "rows_after": rows_after,
        "duplicates_removed": duplicates_removed,
        "missing_value_summary": missing_value_summary,
        "outliers_flagged": outliers_flagged
    }
