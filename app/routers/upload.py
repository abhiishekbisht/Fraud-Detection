from fastapi import APIRouter, UploadFile, File, HTTPException
import uuid
import os
import sqlite3
import pandas as pd
from typing import Dict, Any, List

from app.services.database import save_dataset_metadata, get_db_connection, init_db
from app.services.data_manager import data_manager

router = APIRouter(tags=["upload"])

REQUIRED_COLUMNS = ["Time", "Amount"] + [f"V{i}" for i in range(1, 29)] + ["Class"]
MAX_FILE_SIZE = 200 * 1024 * 1024  # 200MB
CHUNK_SIZE = 1024 * 1024  # 1MB

@router.get("/upload/cleaned-datasets")
@router.get("/cleaned-datasets")
def get_cleaned_datasets() -> List[Dict[str, Any]]:
    """
    Returns list of available datasets with human-readable labels and original filenames.
    """
    db_datasets: Dict[str, Dict[str, Any]] = {}
    try:
        init_db()
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            rows = cursor.execute("SELECT id, filename, row_count FROM datasets ORDER BY upload_time DESC").fetchall()
            for r in rows:
                db_datasets[r["id"]] = {
                    "id": f"{r['id']}.csv",
                    "filename": r["filename"],
                    "row_count": r["row_count"],
                    "label": f"{r['filename']} ({r['row_count']:,} rows)"
                }
    except Exception:
        pass

    results = []
    seen_ids = set()
    for folder in ["data/cleaned", "data/raw"]:
        if os.path.exists(folder):
            for f in os.listdir(folder):
                if f.endswith(".csv") and f not in seen_ids:
                    seen_ids.add(f)
                    base_id = f.replace(".csv", "")
                    if base_id in db_datasets:
                        results.append(db_datasets[base_id])
                    else:
                        results.append({
                            "id": f,
                            "filename": f,
                            "row_count": 0,
                            "label": f
                        })
    return results

@router.post("/upload")
@router.post("/upload/")
@router.post("/")
async def upload_dataset(file: UploadFile = File(...)):
    """
    Uploads a CSV dataset, validates schema, saves to disk, and registers metadata.
    """
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. Only CSV files are accepted."
        )

    dataset_id = str(uuid.uuid4())
    raw_dir = "data/raw"
    cleaned_dir = "data/cleaned"
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(cleaned_dir, exist_ok=True)
    
    dest_path = os.path.join(raw_dir, f"{dataset_id}.csv")
    cleaned_path = os.path.join(cleaned_dir, f"{dataset_id}.csv")

    total_size = 0
    try:
        with open(dest_path, "wb") as f:
            while True:
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > MAX_FILE_SIZE:
                    f.close()
                    if os.path.exists(dest_path):
                        os.remove(dest_path)
                    raise HTTPException(
                        status_code=400,
                        detail="File size exceeds maximum limit of 200MB."
                    )
                f.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        if os.path.exists(dest_path):
            os.remove(dest_path)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to write file: {str(e)}"
        )

    try:
        df = pd.read_csv(dest_path, on_bad_lines="error")
    except Exception as e:
        if os.path.exists(dest_path):
            os.remove(dest_path)
        raise HTTPException(
            status_code=400,
            detail=f"Failed to parse CSV: {str(e)}"
        )

    # Schema Validation
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        if os.path.exists(dest_path):
            os.remove(dest_path)
        raise HTTPException(
            status_code=400,
            detail=f"Schema validation failed. Missing required columns: {', '.join(missing_cols)}"
        )

    # Save cleaned copy automatically for immediate EDA/training
    try:
        df.to_csv(cleaned_path, index=False)
    except Exception:
        pass

    row_count = len(df)
    col_count = len(df.columns)

    try:
        save_dataset_metadata(dataset_id, file.filename, row_count, "valid")
    except Exception:
        pass

    data_manager.register_dataset(dataset_id, df)

    return {
        "dataset_id": dataset_id,
        "rows": row_count,
        "row_count": row_count,
        "columns": list(df.columns),
        "filename": file.filename,
        "validation_status": "valid"
    }
