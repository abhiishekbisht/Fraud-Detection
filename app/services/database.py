import sqlite3
import datetime
import os
import json
from typing import Dict, Any, Optional

DB_PATH = "data/metadata.db"

def init_db():
    """
    Initializes the SQLite database. Creates the datasets and cleaning_reports tables if they do not exist.
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
