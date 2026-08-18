import pandas as pd
import numpy as np
import os
from typing import Dict, Any

from app.routers.upload import REQUIRED_COLUMNS

def clean_dataset(dataset_id: str) -> Dict[str, Any]:
    """
    Loads raw CSV, cleans it, saves it to data/cleaned/, and returns a cleaning report.
    
    Cleaning steps:
    1. Report missing value percentages per column (calculated on the raw dataset).
    2. Drop exact duplicates.
    3. Flag outliers in 'Amount' using IQR (adding 'Amount_outlier' column).
    4. Coerce types of standard numeric columns.
    5. Save the cleaned CSV.
    """
    raw_path = f"data/raw/{dataset_id}.csv"
    cleaned_dir = "data/cleaned"
    cleaned_path = f"{cleaned_dir}/{dataset_id}.csv"
    
    if not os.path.exists(raw_path):
        raise FileNotFoundError(f"Raw dataset file not found at {raw_path}")
        
    df = pd.read_csv(raw_path)
    rows_before = len(df)
    
    # 1. Missing values summary (percentage of nulls per column in the raw data)
    missing_value_summary = (df.isnull().mean() * 100).to_dict()
    # Make keys strings and round values for cleanliness
    missing_value_summary = {str(k): float(round(v, 4)) for k, v in missing_value_summary.items()}
    
    # 2. Drop exact duplicates
    duplicates_removed = int(df.duplicated().sum())
    df = df.drop_duplicates().reset_index(drop=True)
    
    # 3. Flag outliers in 'Amount' using IQR
    outliers_flagged = 0
    if "Amount" in df.columns:
        # Coerce Amount to numeric to prevent issues
        df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")
        
        # Calculate IQR
        q1 = df["Amount"].quantile(0.25)
        q3 = df["Amount"].quantile(0.75)
        iqr = q3 - q1
        
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        # Create Boolean mask
        outlier_mask = (df["Amount"] < lower_bound) | (df["Amount"] > upper_bound)
        outliers_flagged = int(outlier_mask.sum())
        
        # Flag outliers (True/False)
        df["Amount_outlier"] = outlier_mask
    else:
        df["Amount_outlier"] = False

    # 4. Coerce types for all standard schema columns
    for col in REQUIRED_COLUMNS:
        if col in df.columns:
            # We coerce to numeric, turning non-parseable values to NaN
            df[col] = pd.to_numeric(df[col], errors="coerce")
            
            # If the column is 'Class' or 'Time', let's convert to Int64 (nullable int) if clean
            if col in ["Class", "Time"]:
                try:
                    df[col] = df[col].astype("Int64")
                except Exception:
                    pass

    # 5. Save cleaned file to data/cleaned/
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
