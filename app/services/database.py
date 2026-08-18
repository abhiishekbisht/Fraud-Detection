import sqlite3
import datetime
import os
import json
from typing import Dict, Any, Optional

DB_PATH = "data/metadata.db"

def init_db():
    """
    Initializes the SQLite database. Creates tables if they do not exist.
    """
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS datasets (
            id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            row_count INTEGER NOT NULL,
            upload_time TEXT NOT NULL,
            status TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cleaning_reports (
            dataset_id TEXT PRIMARY KEY,
            rows_before INTEGER NOT NULL,
            rows_after INTEGER NOT NULL,
            duplicates_removed INTEGER NOT NULL,
            missing_value_summary TEXT NOT NULL,
            outliers_flagged INTEGER NOT NULL,
            cleaned_at TEXT NOT NULL,
            FOREIGN KEY(dataset_id) REFERENCES datasets(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS training_jobs (
            id TEXT PRIMARY KEY,
            dataset_id TEXT NOT NULL,
            status TEXT NOT NULL,
            error_message TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(dataset_id) REFERENCES datasets(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS models (
            id TEXT PRIMARY KEY,
            job_id TEXT NOT NULL,
            dataset_id TEXT NOT NULL,
            name TEXT NOT NULL,
            precision REAL NOT NULL,
            recall REAL NOT NULL,
            f1_score REAL NOT NULL,
            roc_auc REAL NOT NULL,
            pr_auc REAL NOT NULL,
            confusion_matrix TEXT NOT NULL,
            model_path TEXT NOT NULL,
            scaler_path TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(job_id) REFERENCES training_jobs(id)
        )
    """)
    conn.commit()
    conn.close()

def save_dataset_metadata(dataset_id: str, filename: str, row_count: int, status: str = "valid") -> None:
    """
    Saves dataset metadata to the datasets SQLite table.
    """
    # Ensure DB is initialized
    init_db()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    upload_time = datetime.datetime.now(datetime.UTC).isoformat()
    cursor.execute("""
        INSERT INTO datasets (id, filename, row_count, upload_time, status)
        VALUES (?, ?, ?, ?, ?)
    """, (dataset_id, filename, row_count, upload_time, status))
    conn.commit()
    conn.close()

def save_cleaning_report(
    dataset_id: str,
    rows_before: int,
    rows_after: int,
    duplicates_removed: int,
    missing_value_summary: Dict[str, float],
    outliers_flagged: int
) -> None:
    """
    Saves or replaces a cleaning report for a dataset in the SQLite database.
    """
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cleaned_at = datetime.datetime.now(datetime.UTC).isoformat()
    missing_summary_json = json.dumps(missing_value_summary)
    
    cursor.execute("""
        INSERT OR REPLACE INTO cleaning_reports 
        (dataset_id, rows_before, rows_after, duplicates_removed, missing_value_summary, outliers_flagged, cleaned_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (dataset_id, rows_before, rows_after, duplicates_removed, missing_summary_json, outliers_flagged, cleaned_at))
    conn.commit()
    conn.close()

def get_cleaning_report(dataset_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves the cleaning report for a dataset from the SQLite database.
    Returns None if no report is found.
    """
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT rows_before, rows_after, duplicates_removed, missing_value_summary, outliers_flagged, cleaned_at
        FROM cleaning_reports
        WHERE dataset_id = ?
    """, (dataset_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row is None:
        return None
        
    return {
        "dataset_id": dataset_id,
        "rows_before": row[0],
        "rows_after": row[1],
        "duplicates_removed": row[2],
        "missing_value_summary": json.loads(row[3]),
        "outliers_flagged": row[4],
        "cleaned_at": row[5]
    }

def dataset_exists(dataset_id: str) -> bool:
    """
    Checks if a dataset metadata record exists in the datasets table.
    """
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM datasets WHERE id = ?", (dataset_id,))
    row = cursor.fetchone()
    conn.close()
    return row is not None

def delete_dataset_metadata(dataset_id: str) -> None:
    """
    Deletes dataset metadata, cleaning reports, models, and training jobs from the SQLite database.
    """
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM datasets WHERE id = ?", (dataset_id,))
    cursor.execute("DELETE FROM cleaning_reports WHERE dataset_id = ?", (dataset_id,))
    cursor.execute("DELETE FROM models WHERE dataset_id = ?", (dataset_id,))
    cursor.execute("DELETE FROM training_jobs WHERE dataset_id = ?", (dataset_id,))
    conn.commit()
    conn.close()

def create_training_job(job_id: str, dataset_id: str) -> None:
    """
    Registers a new training job in SQLite database in 'queued' status.
    """
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now_str = datetime.datetime.now(datetime.UTC).isoformat()
    cursor.execute("""
        INSERT INTO training_jobs (id, dataset_id, status, error_message, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (job_id, dataset_id, "queued", None, now_str, now_str))
    conn.commit()
    conn.close()

def update_job_status(job_id: str, status: str, error_message: Optional[str] = None) -> None:
    """
    Updates status and timestamp of a training job.
    """
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now_str = datetime.datetime.now(datetime.UTC).isoformat()
    cursor.execute("""
        UPDATE training_jobs
        SET status = ?, error_message = ?, updated_at = ?
        WHERE id = ?
    """, (status, error_message, now_str, job_id))
    conn.commit()
    conn.close()

def save_trained_model(
    job_id: str, 
    dataset_id: str, 
    name: str, 
    metrics: Dict[str, Any], 
    model_path: str, 
    scaler_path: str
) -> None:
    """
    Saves metrics and artifact paths of a trained model.
    """
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    model_id = f"{job_id}_{name}"
    now_str = datetime.datetime.now(datetime.UTC).isoformat()
    cursor.execute("""
        INSERT INTO models (
            id, job_id, dataset_id, name, precision, recall, f1_score, roc_auc, pr_auc, confusion_matrix, model_path, scaler_path, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        model_id,
        job_id,
        dataset_id,
        name,
        metrics["precision"],
        metrics["recall"],
        metrics["f1_score"],
        metrics["roc_auc"],
        metrics["pr_auc"],
        json.dumps(metrics["confusion_matrix"]),
        model_path,
        scaler_path,
        now_str
    ))
    conn.commit()
    conn.close()

def get_training_job(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves training job and associated models/metrics if completed.
    """
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. Fetch job
    cursor.execute("SELECT * FROM training_jobs WHERE id = ?", (job_id,))
    job_row = cursor.fetchone()
    
    if job_row is None:
        conn.close()
        return None
        
    job_dict = dict(job_row)
    
    # 2. Fetch associated models if status is done
    if job_dict["status"] == "done":
        cursor.execute("SELECT * FROM models WHERE job_id = ?", (job_id,))
        model_rows = cursor.fetchall()
        models_list = []
        for mr in model_rows:
            m_dict = dict(mr)
            m_dict["confusion_matrix"] = json.loads(m_dict["confusion_matrix"])
            models_list.append(m_dict)
        job_dict["models"] = models_list
    else:
        job_dict["models"] = []
        
    conn.close()
    return job_dict
