import sqlite3
import datetime
import os
import json
from typing import Dict, Any, Optional, List
from contextlib import contextmanager

DB_PATH = "data/metadata.db"

@contextmanager
def get_db_connection():
    """
    Context manager to safely open and close SQLite database connections,
    enforcing WAL mode and timeout settings.
    """
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """
    Initializes the SQLite database. Creates tables if they do not exist.
    """
    os.makedirs("data", exist_ok=True)
    with get_db_connection() as conn:
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
                is_active INTEGER DEFAULT 0,
                FOREIGN KEY(job_id) REFERENCES training_jobs(id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id TEXT PRIMARY KEY,
                model_id TEXT NOT NULL,
                prediction_type TEXT NOT NULL,
                input_summary TEXT NOT NULL,
                output TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY(model_id) REFERENCES models(id)
            )
        """)
        try:
            cursor.execute("ALTER TABLE models ADD COLUMN is_active INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        conn.commit()

def save_dataset_metadata(dataset_id: str, filename: str, row_count: int, status: str = "valid") -> None:
    """
    Saves dataset metadata to the datasets SQLite table.
    """
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        upload_time = datetime.datetime.now(datetime.UTC).isoformat()
        cursor.execute("""
            INSERT INTO datasets (id, filename, row_count, upload_time, status)
            VALUES (?, ?, ?, ?, ?)
        """, (dataset_id, filename, row_count, upload_time, status))
        conn.commit()

def save_cleaning_report(
    dataset_id: str,
    rows_before: int,
    rows_after: int,
    duplicates_removed: int,
    missing_value_summary: Dict[str, Any],
    outliers_flagged: int
) -> None:
    """
    Saves or replaces a cleaning report for a dataset in the SQLite database.
    """
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cleaned_at = datetime.datetime.now(datetime.UTC).isoformat()
        missing_summary_json = json.dumps(missing_value_summary)
        
        cursor.execute("""
            INSERT OR REPLACE INTO cleaning_reports (
                dataset_id, rows_before, rows_after, duplicates_removed, missing_value_summary, outliers_flagged, cleaned_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (dataset_id, rows_before, rows_after, duplicates_removed, missing_summary_json, outliers_flagged, cleaned_at))
        conn.commit()

def get_cleaning_report(dataset_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves cleaning report from SQLite.
    Returns None if no report is found.
    """
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT rows_before, rows_after, duplicates_removed, missing_value_summary, outliers_flagged, cleaned_at
            FROM cleaning_reports
            WHERE dataset_id = ?
        """, (dataset_id,))
        row = cursor.fetchone()
        
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
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM datasets WHERE id = ?", (dataset_id,))
        row = cursor.fetchone()
    return row is not None

def delete_dataset_metadata(dataset_id: str) -> None:
    """
    Deletes dataset metadata, cleaning reports, models, training jobs, and prediction history logs from the SQLite database.
    """
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM predictions WHERE model_id IN (SELECT id FROM models WHERE dataset_id = ?)", (dataset_id,))
        cursor.execute("DELETE FROM datasets WHERE id = ?", (dataset_id,))
        cursor.execute("DELETE FROM cleaning_reports WHERE dataset_id = ?", (dataset_id,))
        cursor.execute("DELETE FROM models WHERE dataset_id = ?", (dataset_id,))
        cursor.execute("DELETE FROM training_jobs WHERE dataset_id = ?", (dataset_id,))
        conn.commit()

def create_training_job(job_id: str, dataset_id: str) -> None:
    """
    Registers a new training job in SQLite database in 'queued' status.
    """
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        now_str = datetime.datetime.now(datetime.UTC).isoformat()
        cursor.execute("""
            INSERT INTO training_jobs (id, dataset_id, status, error_message, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (job_id, dataset_id, "queued", None, now_str, now_str))
        conn.commit()

def update_job_status(job_id: str, status: str, error_message: Optional[str] = None) -> None:
    """
    Updates status and timestamp of a training job.
    """
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        now_str = datetime.datetime.now(datetime.UTC).isoformat()
        cursor.execute("""
            UPDATE training_jobs 
            SET status = ?, error_message = ?, updated_at = ?
            WHERE id = ?
        """, (status, error_message, now_str, job_id))
        conn.commit()

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
    with get_db_connection() as conn:
        cursor = conn.cursor()
        model_id = f"{job_id}_{name}"
        now_str = datetime.datetime.now(datetime.UTC).isoformat()
        cursor.execute("""
            INSERT INTO models (
                id, job_id, dataset_id, name, precision, recall, f1_score, roc_auc, pr_auc, confusion_matrix, model_path, scaler_path, created_at, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            now_str,
            0
        ))
        conn.commit()

def get_training_job(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves training job and associated models/metrics if completed.
    """
    init_db()
    with get_db_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 1. Fetch job
        cursor.execute("SELECT * FROM training_jobs WHERE id = ?", (job_id,))
        job_row = cursor.fetchone()
        
        if job_row is None:
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
                m_dict["is_active"] = bool(m_dict["is_active"])
                models_list.append(m_dict)
            job_dict["models"] = models_list
        else:
            job_dict["models"] = []
            
        return job_dict

def list_all_models() -> list:
    """
    Returns all trained models sorted by pr_auc descending.
    """
    init_db()
    with get_db_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id as model_id, job_id, dataset_id, name, precision, recall, f1_score, roc_auc, pr_auc, confusion_matrix, model_path, scaler_path, created_at, is_active
            FROM models
            ORDER BY pr_auc DESC
        """)
        rows = cursor.fetchall()
        models_list = []
        for r in rows:
            m_dict = dict(r)
            m_dict["confusion_matrix"] = json.loads(m_dict["confusion_matrix"])
            m_dict["is_active"] = bool(m_dict["is_active"])
            models_list.append(m_dict)
        return models_list

def activate_model(model_id: str) -> bool:
    """
    Sets is_active=1 for the specified model_id and is_active=0 for all other models.
    Returns True if model was activated, False if model_id was not found.
    """
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Check if model exists
        cursor.execute("SELECT 1 FROM models WHERE id = ?", (model_id,))
        if cursor.fetchone() is None:
            return False
            
        # Deactivate all models
        cursor.execute("UPDATE models SET is_active = 0")
        # Activate the target model
        cursor.execute("UPDATE models SET is_active = 1 WHERE id = ?", (model_id,))
        conn.commit()
        return True

def get_active_model() -> Optional[Dict[str, Any]]:
    """
    Retrieves the currently active model run details.
    """
    init_db()
    with get_db_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id as model_id, job_id, dataset_id, name, precision, recall, f1_score, roc_auc, pr_auc, confusion_matrix, model_path, scaler_path, created_at, is_active
            FROM models
            WHERE is_active = 1
            LIMIT 1
        """)
        row = cursor.fetchone()
        
    if row is None:
        return None
    m_dict = dict(row)
    m_dict["confusion_matrix"] = json.loads(m_dict["confusion_matrix"])
    m_dict["is_active"] = bool(m_dict["is_active"])
    return m_dict

def save_prediction(
    model_id: str,
    prediction_type: str,
    input_summary: Dict[str, Any],
    output: Dict[str, Any]
) -> str:
    """
    Logs a prediction run to the SQLite predictions table.
    Returns the generated prediction_id.
    """
    import uuid
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        prediction_id = str(uuid.uuid4())
        now_str = datetime.datetime.now(datetime.UTC).isoformat()
        cursor.execute("""
            INSERT INTO predictions (id, model_id, prediction_type, input_summary, output, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            prediction_id,
            model_id,
            prediction_type,
            json.dumps(input_summary),
            json.dumps(output),
            now_str
        ))
        conn.commit()
        return prediction_id

def get_model_by_id(model_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves metadata of a specific trained model by ID.
    """
    init_db()
    with get_db_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM models WHERE id = ?", (model_id,))
        row = cursor.fetchone()
        
    if row is None:
        return None
    m_dict = dict(row)
    m_dict["confusion_matrix"] = json.loads(m_dict["confusion_matrix"])
    m_dict["is_active"] = bool(m_dict["is_active"])
    return m_dict

def get_prediction_by_id(prediction_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves prediction log details for a past prediction.
    """
    init_db()
    with get_db_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM predictions WHERE id = ?", (prediction_id,))
        row = cursor.fetchone()
        
    if row is None:
        return None
    p_dict = dict(row)
    p_dict["input_summary"] = json.loads(p_dict["input_summary"])
    p_dict["output"] = json.loads(p_dict["output"])
    return p_dict

def get_prediction_history(
    page: int = 1,
    limit: int = 10,
    risk_label: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Queries paginated prediction history from SQLite with dynamic filtering.
    """
    init_db()
    with get_db_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        where_clauses = []
        params = []
        
        if risk_label:
            where_clauses.append("json_extract(output, '$.risk_label') = ?")
            params.append(risk_label)
            
        if start_date:
            where_clauses.append("timestamp >= ?")
            params.append(start_date)
            
        if end_date:
            where_clauses.append("timestamp <= ?")
            params.append(end_date)
            
        where_str = ""
        if where_clauses:
            where_str = "WHERE " + " AND ".join(where_clauses)
            
        # Get total count
        count_query = f"SELECT COUNT(*) FROM predictions {where_str}"
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()[0]
        
        # Get paginated data
        offset = (page - 1) * limit
        data_query = f"""
            SELECT * FROM predictions
            {where_str}
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        """
        cursor.execute(data_query, params + [limit, offset])
        rows = cursor.fetchall()
        
        predictions = []
        for r in rows:
            p_dict = dict(r)
            p_dict["input_summary"] = json.loads(p_dict["input_summary"])
            p_dict["output"] = json.loads(p_dict["output"])
            predictions.append(p_dict)
            
        total_pages = (total_count + limit - 1) // limit if limit > 0 else 0
        
        return {
            "predictions": predictions,
            "total_count": total_count,
            "page": page,
            "limit": limit,
            "total_pages": total_pages
        }

def list_cleaned_datasets() -> list:
    """
    Returns all datasets that have successfully finished the cleaning stage.
    """
    init_db()
    with get_db_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT d.id, d.filename, d.row_count, c.cleaned_at
            FROM datasets d
            JOIN cleaning_reports c ON d.id = c.dataset_id
            ORDER BY c.cleaned_at DESC
        """)
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

