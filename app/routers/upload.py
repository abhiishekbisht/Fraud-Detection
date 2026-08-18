from fastapi import APIRouter, UploadFile, File, HTTPException
import uuid
import os
import pandas as pd
from typing import Dict, Any

from app.services.database import save_dataset_metadata
from app.services.data_manager import data_manager

router = APIRouter(tags=["upload"])

# Define the standard Kaggle Credit Card Fraud dataset schema
REQUIRED_COLUMNS = ["Time", "Amount"] + [f"V{i}" for i in range(1, 29)] + ["Class"]
MAX_FILE_SIZE = 200 * 1024 * 1024  # 200MB in bytes
CHUNK_SIZE = 1024 * 1024  # 1MB chunk size

@router.post("/upload")
async def upload_dataset(file: UploadFile = File(...)):
    """
    Uploads a CSV transaction dataset, validates its size and schema,
    saves it to disk, registers it in-memory, and logs metadata in SQLite.
    """
    # 1. Basic extension check
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. Only CSV files are accepted."
        )

    # 2. Generate UUID for the dataset
    dataset_id = str(uuid.uuid4())
    
    # Ensure data/raw directory exists
    raw_dir = "data/raw"
    os.makedirs(raw_dir, exist_ok=True)
    dest_path = os.path.join(raw_dir, f"{dataset_id}.csv")

    # 3. Stream and write the file to verify size limits under 200MB
    total_size = 0
    try:
        with open(dest_path, "wb") as f:
            while True:
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > MAX_FILE_SIZE:
                    # Clean up partial file and reject
                    f.close()
                    if os.path.exists(dest_path):
                        os.remove(dest_path)
                    raise HTTPException(
                        status_code=400,
                        detail=f"File size exceeds the maximum limit of 200MB (uploaded {total_size} bytes)."
                    )
                f.write(chunk)
    except HTTPException:
        # Re-raise standard size limit HTTP exception
        raise
    except Exception as e:
        # Clean up on write failure
        if os.path.exists(dest_path):
            os.remove(dest_path)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to write file to disk: {str(e)}"
        )

    # 4. Load CSV using pandas and catch malformed file errors
    try:
        df = pd.read_csv(dest_path, on_bad_lines="error")
    except Exception as e:
        if os.path.exists(dest_path):
            os.remove(dest_path)
        raise HTTPException(
            status_code=400,
            detail=f"Failed to parse CSV. Please ensure it is a valid CSV file. Error: {str(e)}"
        )

    # 5. Schema Validation
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        if os.path.exists(dest_path):
            os.remove(dest_path)
        raise HTTPException(
            status_code=400,
            detail=f"Schema validation failed. Missing required columns: {', '.join(missing_cols)}"
        )

    # 6. Save metadata in SQLite
    row_count = len(df)
    try:
        save_dataset_metadata(dataset_id, file.filename, row_count, "valid")
    except Exception as e:
        # Don't delete the saved CSV if SQLite write fails, but report internal error
        raise HTTPException(
            status_code=500,
            detail=f"Dataset saved but failed to store metadata: {str(e)}"
        )

    # 7. Register DataFrame in memory cache
    data_manager.register_dataset(dataset_id, df)

    # 8. Return response
    return {
        "dataset_id": dataset_id,
        "row_count": row_count,
        "columns": list(df.columns),
        "validation_status": "valid"
    }
