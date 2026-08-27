from fastapi import APIRouter, UploadFile, File, HTTPException, Header
import uuid
import os
import sqlite3
import pandas as pd
from typing import Dict, Any, List, Optional

from app.services.database import (
    save_dataset_metadata,
    get_db_connection,
    init_db,
    purge_session_data,
    purge_all_datasets
)
from app.services.data_manager import data_manager

router = APIRouter(tags=["upload"])

REQUIRED_COLUMNS = ["Time", "Amount"] + [f"V{i}" for i in range(1, 29)] + ["Class"]
MAX_FILE_SIZE = 200 * 1024 * 1024  # 200MB
CHUNK_SIZE = 1024 * 1024  # 1MB

@router.get("/upload/cleaned-datasets")
@router.get("/cleaned-datasets")
def get_cleaned_datasets(x_session_id: Optional[str] = Header("global", alias="X-Session-ID")) -> List[Dict[str, Any]]:
    """
    Returns datasets for the active session. If the user imported a dataset in this session,
    return that dataset. Otherwise, return the default sample dataset for global sessions.
    """
    session_id = x_session_id or "global"
    results = []
    seen_filenames = set()
    try:
        init_db()
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            # Fetch valid datasets uploaded in the active session
            rows = cursor.execute(
                "SELECT id, filename, row_count FROM datasets WHERE session_id = ? AND status = 'valid' ORDER BY upload_time DESC",
                (session_id,)
            ).fetchall()

            for r in rows:
                fn = r["filename"]
                if fn in ["dirty_transactions.csv", "creditcard_invalid.csv"]:
                    continue
                if fn not in seen_filenames:
                    seen_filenames.add(fn)
                    results.append({
                        "id": f"{r['id']}.csv",
                        "filename": r["filename"],
                        "row_count": r["row_count"],
                        "label": f"{r['filename']} ({r['row_count']:,} rows)"
                    })
    except Exception:
        pass

    if not results and session_id == "global":
        results.append({
            "id": "creditcard_transactions_sample.csv",
            "filename": "creditcard_transactions_sample.csv",
            "row_count": 284807,
            "label": "Credit Card Fraud Sample (284,807 rows)"
        })

    return results

@router.post("/reset")
@router.post("/upload/reset")
def reset_session_data_endpoint(x_session_id: Optional[str] = Header("global", alias="X-Session-ID")) -> Dict[str, Any]:
    """
    Purges all datasets, trained models, predictions, and physical disk files for the active session.
    """
    session_id = x_session_id or "global"
    if session_id == "all":
        deleted_ids = purge_all_datasets()
        data_manager.purge_all()
    else:
        deleted_ids = purge_session_data(session_id)
        data_manager.purge_datasets(deleted_ids)
    return {
        "status": "success",
        "message": f"Successfully purged session '{session_id}' data and physical files.",
        "purged_datasets_count": len(deleted_ids)
    }

@router.post("/upload")
@router.post("/upload/")
@router.post("/")
async def upload_dataset(
    file: UploadFile = File(...),
    x_session_id: Optional[str] = Header("global", alias="X-Session-ID")
):
    session_id = x_session_id or "global"

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

    # Flexible Schema Validation
    if len(df) == 0 or len(df.columns) < 2:
        if os.path.exists(dest_path):
            os.remove(dest_path)
        raise HTTPException(
            status_code=400,
            detail="Schema validation failed. Dataset must contain at least 1 row and at least 2 tabular columns."
        )

    # Validate target column presence (Class, isFraud, is_fraud, target, label, fraud, etc.)
    possible_target_names = ["class", "isfraud", "is_fraud", "target", "label", "fraud", "is_anomaly"]
    target_col = None
    for c in df.columns:
        if str(c).lower() in possible_target_names:
            target_col = c
            break

    if not target_col:
        if os.path.exists(dest_path):
            os.remove(dest_path)
        raise HTTPException(
            status_code=400,
            detail="Schema validation failed. Missing required columns: target column (Class, isFraud, target, label, fraud)."
        )

    # Dynamic Fraud Anomalies Count
    fraud_count = 0
    try:
        target_s = df[target_col]
        if not pd.api.types.is_numeric_dtype(target_s):
            target_s = target_s.astype(str).str.lower().isin(["1", "true", "fraud", "yes"]).astype(int)
        val_counts = target_s.value_counts().to_dict()
        fraud_count = int(val_counts.get(1, val_counts.get(1.0, 0)))
    except Exception:
        fraud_count = 0

    # Clean up any existing duplicate uploads of the exact same filename for this session
    try:
        init_db()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            old_rows = cursor.execute(
                "SELECT id FROM datasets WHERE filename = ? AND (session_id = ? OR session_id = 'global')",
                (file.filename, session_id)
            ).fetchall()
            for old_r in old_rows:
                old_id = old_r[0]
                cursor.execute("DELETE FROM datasets WHERE id = ?", (old_id,))
                cursor.execute("DELETE FROM cleaning_reports WHERE dataset_id = ?", (old_id,))
                cursor.execute("DELETE FROM models WHERE dataset_id = ?", (old_id,))
                cursor.execute("DELETE FROM training_jobs WHERE dataset_id = ?", (old_id,))
                for folder in [raw_dir, cleaned_dir]:
                    old_f = os.path.join(folder, f"{old_id}.csv")
                    if os.path.exists(old_f) and old_f != dest_path:
                        try:
                            os.remove(old_f)
                        except Exception:
                            pass
            conn.commit()
    except Exception:
        pass

    # Save cleaned copy automatically for immediate EDA/training
    try:
        df.to_csv(cleaned_path, index=False)
    except Exception:
        pass

    row_count = len(df)
    col_count = len(df.columns)

    try:
        save_dataset_metadata(dataset_id, file.filename, row_count, "valid", session_id)
    except Exception:
        pass

    data_manager.register_dataset(dataset_id, df)

    return {
        "dataset_id": dataset_id,
        "rows": row_count,
        "row_count": row_count,
        "columns": list(df.columns),
        "filename": file.filename,
        "fraudCount": fraud_count,
        "validation_status": "valid"
    }
