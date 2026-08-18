import io
import os
import sqlite3
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.database import DB_PATH
from app.services.data_manager import data_manager

client = TestClient(app)

def create_dirty_csv_bytes() -> bytes:
    """
    Creates a dirty CSV with:
    - 1 duplicate row (Row 9 duplicates Row 8)
    - 1 missing value (Row 1 has V2 as NaN)
    - 1 coercion candidate (Row 2 has V3 as "not_a_number")
    - 1 outlier (Row 4 has Amount = 5000.0, others are 10.0)
    Total rows: 10
    """
    cols = ["Time", "Amount"] + [f"V{i}" for i in range(1, 29)] + ["Class"]
    
    # Base data
    data = {col: [10.0] * 10 for col in cols}
    
    # Inject specific values
    data["Time"] = [float(i) for i in range(1, 11)]
    data["Class"] = [0] * 10
    data["Class"][3] = 1  # Outlier row is fraud
    
    # 1. Missing value in V2 (first row)
    data["V2"][0] = None
    
    # 2. Coercion candidate in V3 (second row)
    data["V3"][1] = "not_a_number"
    
    # 3. Outlier in Amount (fourth row)
    data["Amount"][3] = 5000.0
    
    # 4. Duplicate row (Row 9 matches Row 8)
    # Row 8 is index 7, Row 9 is index 8. Let's make them identical.
    for col in cols:
        data[col][8] = data[col][7]
        
    df = pd.DataFrame(data)
    
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")


def test_clean_dataset_endpoint():
    """
    Tests the POST /upload -> GET /clean/{dataset_id} workflow.
    Verifies reports are correct, files are saved, types are coerced, and SQLite is integrated.
    """
    # 1. Upload the dirty CSV
    csv_bytes = create_dirty_csv_bytes()
    files = {"file": ("dirty_transactions.csv", csv_bytes, "text/csv")}
    upload_response = client.post("/upload", files=files)
    assert upload_response.status_code == 200
    
    dataset_id = upload_response.json()["dataset_id"]
    
    # Verify raw file exists
    raw_path = f"data/raw/{dataset_id}.csv"
    assert os.path.exists(raw_path)

    try:
        # 2. Clean the dataset via GET /clean/{dataset_id}
        clean_response = client.get(f"/clean/{dataset_id}")
        assert clean_response.status_code == 200
        
        report = clean_response.json()
        assert report["dataset_id"] == dataset_id
        assert report["rows_before"] == 10
        assert report["rows_after"] == 9  # 1 duplicate dropped
        assert report["duplicates_removed"] == 1
        assert report["outliers_flagged"] == 1  # 5000.0 flagged
        assert "cleaned_at" in report
        
        # Verify missing value summary: V2 has 10% missing, others have 0%
        assert report["missing_value_summary"]["V2"] == 10.0
        assert report["missing_value_summary"]["V1"] == 0.0
        
        # 3. Verify cleaned file saved on disk
        cleaned_path = f"data/cleaned/{dataset_id}.csv"
        assert os.path.exists(cleaned_path)
        
        df_cleaned = pd.read_csv(cleaned_path)
        assert len(df_cleaned) == 9
        assert "Amount_outlier" in df_cleaned.columns
        # Outlier row is at index 3 (originally Time=4.0)
        outlier_row = df_cleaned[df_cleaned["Time"] == 4.0].iloc[0]
        assert bool(outlier_row["Amount_outlier"]) is True
        
        # Check type coercion: V3 second row (Time=2.0) should be NaN (float null) due to coercion
        coerced_row = df_cleaned[df_cleaned["Time"] == 2.0].iloc[0]
        assert pd.isna(coerced_row["V3"])

        # 4. Verify cleaning report saved in SQLite
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT rows_before, rows_after, outliers_flagged FROM cleaning_reports WHERE dataset_id = ?", (dataset_id,))
        db_row = cursor.fetchone()
        conn.close()
        
        assert db_row is not None
        assert db_row[0] == 10
        assert db_row[1] == 9
        assert db_row[2] == 1

        # 5. Call clean endpoint a second time to test cached database report retrieval
        second_clean_response = client.get(f"/clean/{dataset_id}")
        assert second_clean_response.status_code == 200
        second_report = second_clean_response.json()
        
        # Cleaned timestamps should match exactly since it is fetched from SQLite
        assert second_report["cleaned_at"] == report["cleaned_at"]

        # 6. Verify data_manager fallback retrieval loads the cleaned dataset
        # We delete it from the in-memory dictionary to force loading from disk
        del data_manager._datasets[dataset_id]
        assert dataset_id not in data_manager._datasets
        
        # Query data_manager, which should read the cleaned CSV (not raw CSV)
        df_loaded = data_manager.get_dataset(dataset_id)
        assert len(df_loaded) == 9
        assert "Amount_outlier" in df_loaded.columns
    finally:
        # Cleanup test files from both raw and cleaned dirs
        data_manager.delete_dataset(dataset_id)


def test_clean_dataset_not_found():
    """
    Tests GET /clean/{dataset_id} for a non-existent dataset.
    """
    response = client.get("/clean/non_existent_dataset_id")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
