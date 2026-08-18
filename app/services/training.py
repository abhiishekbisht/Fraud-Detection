import os
import json
import logging
import joblib
import datetime
import pandas as pd
from typing import Dict, Any

from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
try:
    from xgboost import XGBClassifier
    XGBOOST_AVAILABLE = True
except Exception as e:
    XGBOOST_AVAILABLE = False
    from sklearn.ensemble import HistGradientBoostingClassifier as XGBClassifier
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    precision_recall_curve,
    auc,
    confusion_matrix
)

from app.services.data_manager import data_manager
from app.services.database import update_job_status, save_trained_model
from app.ml.preprocessing import preprocess_dataset

logger = logging.getLogger("training")

def evaluate_model(model: Any, X_test: pd.DataFrame, y_test: pd.Series) -> Dict[str, Any]:
    """
    Evaluates a trained classifier on the test set and calculates metrics.
    """
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]
    
    prec = precision_score(y_test, y_pred, zero_division=0)
    rec = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    roc_auc = roc_auc_score(y_test, y_prob)
    
    # Calculate Precision-Recall Area Under Curve
    precisions, recalls, _ = precision_recall_curve(y_test, y_prob)
    pr_auc = auc(recalls, precisions)
    
    # Calculate confusion matrix
    cm = confusion_matrix(y_test, y_pred)
    if cm.shape == (2, 2):
        tn, fp, fn, tp = cm.ravel()
    else:
        tn, fp, fn, tp = int(cm[0, 0]), 0, 0, 0
        
    return {
        "precision": float(prec),
        "recall": float(rec),
        "f1_score": float(f1),
        "roc_auc": float(roc_auc),
        "pr_auc": float(pr_auc),
        "confusion_matrix": [[int(tn), int(fp)], [int(fn), int(tp)]]
    }

def train_models_task(job_id: str, dataset_id: str, session_id: str = "global") -> None:
    """
    Background worker function that trains Logistic Regression, Random Forest, 
    and XGBoost classifiers. Resamples the training data using SMOTE, scales 
    features, logs status updates, and stores evaluation outputs.
    Saves a companion metadata.json containing feature engineering parameters.
    """
    try:
        # 1. Update job status in database to 'running'
        update_job_status(job_id, "running")
        logger.info(f"Starting training job {job_id} on dataset {dataset_id} for session {session_id}")

        # 2. Retrieve dataset from data manager
        df = data_manager.get_dataset(dataset_id)

        # 3. Create job output directories
        job_dir = os.path.join("data", "models", job_id)
        os.makedirs(job_dir, exist_ok=True)
        scaler_path = os.path.join(job_dir, "scaler.joblib")

        # Save feature engineering metadata (mean amount, IQR outlier bounds)
        mean_amt = 0.0
        lower_bound = 0.0
        upper_bound = 0.0
        if "Amount" in df.columns:
            mean_amt = float(df["Amount"].fillna(0).mean())
            q1 = df["Amount"].quantile(0.25)
            q3 = df["Amount"].quantile(0.75)
            iqr = q3 - q1
            lower_bound = float(q1 - 1.5 * iqr)
            upper_bound = float(q3 + 1.5 * iqr)
            
        metadata = {
            "mean_amount": mean_amt,
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
            "session_id": session_id,
            "dataset_id": dataset_id,
            "created_at": datetime.datetime.now(datetime.UTC).isoformat()
        }
        with open(os.path.join(job_dir, "metadata.json"), "w") as f:
            json.dump(metadata, f, indent=2)

        # 4. Perform preprocessing (Splitting, Scaling, Resampling)
        X_train_res, y_train_res, X_test_scaled, y_test = preprocess_dataset(
            df=df,
            dataset_id=dataset_id,
            target_col="Class",
            scaler_path=scaler_path
        )

        # 5. Define classifiers
        if XGBOOST_AVAILABLE:
            models_dict = {
                "logistic_regression": LogisticRegression(max_iter=1000, random_state=42),
                "random_forest": RandomForestClassifier(random_state=42, n_jobs=-1),
                "xgboost": XGBClassifier(use_label_encoder=False, eval_metric="logloss", random_state=42, n_jobs=-1)
            }
        else:
            models_dict = {
                "logistic_regression": LogisticRegression(max_iter=1000, random_state=42),
                "random_forest": RandomForestClassifier(random_state=42, n_jobs=-1),
                "xgboost": XGBClassifier(random_state=42)
            }

        # 6. Train and evaluate each model
        for model_name, model in models_dict.items():
            logger.info(f"Training {model_name} for job {job_id}...")
            # Fit model on resampled training split
            model.fit(X_train_res, y_train_res)

            # Evaluate model on untouched rescaled test split
            metrics = evaluate_model(model, X_test_scaled, y_test)

            # Save model artifact
            model_path = os.path.join(job_dir, f"{model_name}.joblib")
            joblib.dump(model, model_path)

            # Log metrics and paths into SQLite database
            save_trained_model(
                job_id=job_id,
                dataset_id=dataset_id,
                name=model_name,
                metrics=metrics,
                model_path=model_path,
                scaler_path=scaler_path,
                session_id=session_id
            )

        # 7. Update status to 'done' on success
        update_job_status(job_id, "done")
        logger.info(f"Training job {job_id} completed successfully.")

    except Exception as e:
        logger.error(f"Training job {job_id} failed: {str(e)}", exc_info=True)
        update_job_status(job_id, "failed", error_message=str(e))
