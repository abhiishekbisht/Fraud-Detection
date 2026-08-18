import io
import pandas as pd
import joblib
from fastapi import APIRouter, HTTPException, File, UploadFile
from fastapi.responses import StreamingResponse
from typing import Dict, Any

from app.models.prediction import TransactionFeatures
from app.services.database import get_active_model, save_prediction

router = APIRouter(tags=["prediction"])

# Threshold selection constants
THRESHOLD_MEDIUM = 0.10
THRESHOLD_HIGH = 0.50

def get_risk_label(probability: float) -> str:
    """
    Computes risk level based on optimized class-imbalanced thresholds.
    """
    if probability < THRESHOLD_MEDIUM:
        return "Low"
    elif probability < THRESHOLD_HIGH:
        return "Medium"
    else:
        return "High"

@router.post("/predict")
def predict_single(features: TransactionFeatures) -> Dict[str, Any]:
    """
    Evaluates a single credit card transaction for fraud risk.
    Loads the currently active model run, transforms features, and logs prediction output.
    """
    # 1. Fetch active model metadata
    active_model = get_active_model()
    if active_model is None:
        raise HTTPException(
            status_code=400,
            detail="No active model has been set. Please train and activate a model first using POST /models/{model_id}/activate."
        )

    model_id = active_model["model_id"]
    model_path = active_model["model_path"]
    scaler_path = active_model["scaler_path"]

    # 2. Load model and scaler artifacts from disk
    try:
        model = joblib.load(model_path)
        scaler = joblib.load(scaler_path)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load model artifacts: {str(e)}"
        )

    # 3. Align and scale input features (exactly in scaler's column order)
    feature_cols = ["Time", "Amount"] + [f"V{i}" for i in range(1, 29)]
    input_dict = features.dict()
    df_in = pd.DataFrame([input_dict])

    try:
        # Scale only the input features in correct column order
        X_scaled = scaler.transform(df_in[feature_cols])
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error scaling transaction features: {str(e)}"
        )

    # 4. Perform inference
    try:
        y_prob = model.predict_proba(X_scaled)[0, 1]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error executing model prediction: {str(e)}"
        )

    # 5. Map risk label and set placeholder for top contributing features
    risk_label = get_risk_label(y_prob)
    top_features = ["V17", "V14", "V12"]  # Placeholder for SHAP feature importances

    output_payload = {
        "fraud_probability": float(y_prob),
        "risk_label": risk_label,
        "top_features": top_features
    }

    # 6. Log prediction metadata to SQLite
    try:
        pred_id = save_prediction(
            model_id=model_id,
            prediction_type="single",
            input_summary=input_dict,
            output=output_payload
        )
        output_payload["prediction_id"] = pred_id
    except Exception as e:
        # Log error but don't fail the prediction response if database logging fails
        pass

    return output_payload

@router.post("/predict/batch")
def predict_batch(file: UploadFile = File(...)) -> StreamingResponse:
    """
    Scores a batch of transactions provided in a CSV file.
    Appends 'fraud_probability' and 'risk_label' columns and returns a scored CSV file.
    """
    # 1. Validate file extension
    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. Only CSV files are supported."
        )

    # 2. Fetch active model metadata
    active_model = get_active_model()
    if active_model is None:
        raise HTTPException(
            status_code=400,
            detail="No active model has been set. Please train and activate a model first using POST /models/{model_id}/activate."
        )

    model_id = active_model["model_id"]
    model_path = active_model["model_path"]
    scaler_path = active_model["scaler_path"]

    # 3. Load model and scaler artifacts from disk
    try:
        model = joblib.load(model_path)
        scaler = joblib.load(scaler_path)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load model artifacts: {str(e)}"
        )

    # 4. Read CSV and validate columns schema
    try:
        contents = file.file.read()
        df = pd.read_csv(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to parse CSV file: {str(e)}"
        )

    feature_cols = ["Time", "Amount"] + [f"V{i}" for i in range(1, 29)]
    missing_cols = [col for col in feature_cols if col not in df.columns]
    if missing_cols:
        raise HTTPException(
            status_code=400,
            detail=f"Uploaded CSV is missing required features: {missing_cols}"
        )

    # 5. Run batch inference
    try:
        X_scaled = scaler.transform(df[feature_cols])
        y_probs = model.predict_proba(X_scaled)[:, 1]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error executing batch predictions: {str(e)}"
        )

    # 6. Append prediction columns
    df["fraud_probability"] = y_probs
    df["risk_label"] = df["fraud_probability"].apply(get_risk_label)

    # 7. Convert DataFrame back to CSV for download
    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)

    # 8. Log prediction summary to SQLite
    try:
        input_summary = {
            "filename": file.filename,
            "row_count": len(df)
        }
        output_summary = {
            "processed_rows": len(df),
            "fraud_flagged_count": int((df["fraud_probability"] >= THRESHOLD_HIGH).sum()),
            "medium_risk_count": int((df["risk_label"] == "Medium").sum())
        }
        save_prediction(
            model_id=model_id,
            prediction_type="batch",
            input_summary=input_summary,
            output=output_summary
        )
    except Exception as e:
        # Prevent database logging errors from failing the CSV return
        pass

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=scored_{file.filename}"
        }
    )
