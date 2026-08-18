from fastapi import APIRouter, HTTPException
import os
import pandas as pd
from typing import Dict, Any

from app.services.database import get_cleaning_report, save_cleaning_report
from app.services.cleaning import clean_dataset
from app.services.data_manager import data_manager

router = APIRouter(tags=["cleaning"])

@router.get("/clean/{dataset_id}")
def clean_and_report_dataset(dataset_id: str):
    """
    Cleans a dataset by its ID if not already cleaned, and returns the cleaning report.
    Loads the cleaned version in memory for subsequent operations.
    """
    # 1. Check if the cleaning report already exists in SQLite
    try:
        existing_report = get_cleaning_report(dataset_id)
        if existing_report is not None:
            # Load cleaned dataset into memory cache if not already cached
            cleaned_path = f"data/cleaned/{dataset_id}.csv"
            if os.path.exists(cleaned_path):
                try:
                    df = pd.read_csv(cleaned_path)
                    data_manager.register_dataset(dataset_id, df)
                except Exception:
                    pass  # Fail silently to let get_dataset fallback handle it later
            return existing_report
    except Exception as e:
        # SQLite error, log or proceed to normal workflow
        pass

    # 2. Check if the raw dataset file exists
    raw_path = f"data/raw/{dataset_id}.csv"
    if not os.path.exists(raw_path):
        raise HTTPException(
            status_code=404,
            detail=f"Dataset with ID '{dataset_id}' not found in raw storage."
        )

    # 3. Perform the cleaning process
    try:
        report = clean_dataset(dataset_id)
    except FileNotFoundError as fnf_err:
        raise HTTPException(status_code=404, detail=str(fnf_err))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error executing data cleaning service: {str(e)}"
        )

    # 4. Save the cleaning report in SQLite database
    try:
        save_cleaning_report(
            dataset_id=dataset_id,
            rows_before=report["rows_before"],
            rows_after=report["rows_after"],
            duplicates_removed=report["duplicates_removed"],
            missing_value_summary=report["missing_value_summary"],
            outliers_flagged=report["outliers_flagged"]
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Dataset cleaned but failed to persist cleaning report: {str(e)}"
        )

    # 5. Load the cleaned DataFrame into the memory data_manager
    cleaned_path = f"data/cleaned/{dataset_id}.csv"
    try:
        df_cleaned = pd.read_csv(cleaned_path)
        data_manager.register_dataset(dataset_id, df_cleaned)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Dataset cleaned but failed to load into memory: {str(e)}"
        )

    # 6. Retrieve the fully stored report (including database timestamp)
    stored_report = get_cleaning_report(dataset_id)
    if stored_report is None:
        # Fallback return in case fetch fails
        return {
            "dataset_id": dataset_id,
            **report,
            "cleaned_at": None
        }
        
    return stored_report
