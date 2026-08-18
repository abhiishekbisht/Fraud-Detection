import uuid
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any

from app.services.database import (
    get_cleaning_report,
    create_training_job,
    get_training_job,
    dataset_exists
)
from app.services.training import train_models_task

router = APIRouter(tags=["training"])

@router.post("/train/{dataset_id}", status_code=202)
def start_training(dataset_id: str, background_tasks: BackgroundTasks) -> Dict[str, str]:
    """
    Kicks off an asynchronous model training pipeline for a cleaned dataset.
    Trains Logistic Regression, Random Forest, and XGBoost models.
    """
    # 1. Verify dataset exists in the database
    if not dataset_exists(dataset_id):
        raise HTTPException(
            status_code=404,
            detail=f"Dataset with ID '{dataset_id}' not found."
        )

    # 2. Enforce that the dataset has been cleaned first
    report = get_cleaning_report(dataset_id)
    if report is None:
        raise HTTPException(
            status_code=400,
            detail=f"Dataset with ID '{dataset_id}' has not been cleaned. Please clean it first using GET /clean/{dataset_id}."
        )

    # 3. Create unique Job ID and initialize job state in SQLite
    job_id = str(uuid.uuid4())
    create_training_job(job_id, dataset_id)

    # 4. Trigger training pipeline as a background task
    background_tasks.add_task(train_models_task, job_id, dataset_id)

    return {
        "job_id": job_id,
        "status": "queued"
    }

@router.get("/train/status/{job_id}")
def check_training_status(job_id: str) -> Dict[str, Any]:
    """
    Retrieves the execution status and evaluation results of a model training job.
    Includes auto-recommendations once completed.
    """
    # 1. Fetch training job records from database
    job_data = get_training_job(job_id)
    if job_data is None:
        raise HTTPException(
            status_code=404,
            detail=f"Training job with ID '{job_id}' not found."
        )

    response = {
        "job_id": job_data["id"],
        "dataset_id": job_data["dataset_id"],
        "status": job_data["status"],
        "created_at": job_data["created_at"],
        "updated_at": job_data["updated_at"]
    }

    # 2. Populate details based on job status
    if job_data["status"] == "failed":
        response["error_message"] = job_data["error_message"]

    elif job_data["status"] == "done":
        # Structure model evaluations
        models_metrics = {}
        best_model_name = None
        highest_pr_auc = -1.0

        for model in job_data.get("models", []):
            name = model["name"]
            metrics = {
                "precision": model["precision"],
                "recall": model["recall"],
                "f1_score": model["f1_score"],
                "roc_auc": model["roc_auc"],
                "pr_auc": model["pr_auc"],
                "confusion_matrix": model["confusion_matrix"],
                "model_path": model["model_path"],
                "scaler_path": model["scaler_path"]
            }
            models_metrics[name] = metrics

            # Check if this is the best model based on PR-AUC
            if model["pr_auc"] > highest_pr_auc:
                highest_pr_auc = model["pr_auc"]
                best_model_name = name

        response["models"] = models_metrics
        response["best_model"] = best_model_name
        response["recommendation_reason"] = (
            f"Recommended '{best_model_name}' because it scored the highest Precision-Recall Area "
            f"Under Curve (PR-AUC = {highest_pr_auc:.4f}) on the untouched test split."
            if best_model_name else "No model evaluated."
        )

    return response
