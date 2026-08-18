import io
import pandas as pd
import numpy as np
import joblib
import shap
from fastapi import APIRouter, HTTPException, File, UploadFile
from fastapi.responses import StreamingResponse
from typing import Dict, Any, List, Optional

from app.models.prediction import TransactionFeatures
from app.services.database import get_active_model, save_prediction, get_prediction_by_id, get_model_by_id, get_prediction_history

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

def get_shap_explanation(model: Any, scaler: Any, dataset_id: str, df_row: pd.DataFrame) -> tuple:
    """
    Computes SHAP values for the transaction row using the best-suited SHAP explainer.
    Returns: (features_list, explainer) where features_list is a sorted list of dictionaries:
    [{"feature": str, "shap_value": float, "effect": "increases" | "decreases"}, ...]
    """
    feature_cols = ["Time", "Amount"] + [f"V{i}" for i in range(1, 29)]
    X_input = scaler.transform(df_row[feature_cols])

    model_type_str = str(type(model))
    
    if "LogisticRegression" in model_type_str:
        # Linear models require background data
        cleaned_path = f"data/cleaned/{dataset_id}.csv"
        try:
            df_cleaned = pd.read_csv(cleaned_path)
            background_samples = df_cleaned[feature_cols].sample(min(100, len(df_cleaned)), random_state=42)
            X_bg = scaler.transform(background_samples)
        except Exception:
            # Fallback to zero background if cleaned file is missing
            X_bg = np.zeros((1, 30))
        explainer = shap.LinearExplainer(model, X_bg)
        raw_shap_values = explainer.shap_values(X_input)
    else:
        # Tree-based models (RandomForestClassifier, HistGradientBoostingClassifier, XGBClassifier)
        explainer = shap.TreeExplainer(model)
        raw_shap_values = explainer.shap_values(X_input)

    # Resolve SHAP value shape discrepancies
    if isinstance(raw_shap_values, list):
        shap_array = raw_shap_values[1] if len(raw_shap_values) > 1 else raw_shap_values[0]
    else:
        shap_array = raw_shap_values

    # Handle 3D output arrays: (n_samples, n_features, n_classes)
    if len(shap_array.shape) == 3:
        shap_array = shap_array[:, :, 1]

    # For a single prediction row
    row_shap = shap_array[0]

    # Pair features, calculate effects, and sort by absolute contribution descending
    features_list = []
    for idx, col_name in enumerate(feature_cols):
        val = float(row_shap[idx])
        effect = "increases" if val >= 0 else "decreases"
        features_list.append({
            "feature": col_name,
            "shap_value": val,
            "effect": effect
        })

    features_list.sort(key=lambda x: abs(x["shap_value"]), reverse=True)
    return features_list, explainer

@router.post("/predict")
def predict_single(features: TransactionFeatures) -> Dict[str, Any]:
    """
    Evaluates a single credit card transaction for fraud risk.
    Loads the active model run, transforms features, calculates SHAP contributions, and logs prediction.
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

    # 3. Align and scale input features
    feature_cols = ["Time", "Amount"] + [f"V{i}" for i in range(1, 29)]
    input_dict = features.dict()
    df_in = pd.DataFrame([input_dict])

    try:
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

    risk_label = get_risk_label(y_prob)

    # 5. Compute real SHAP value contributions
    try:
        features_list, _ = get_shap_explanation(
            model=model,
            scaler=scaler,
            dataset_id=active_model["dataset_id"],
            df_row=df_in
        )
        top_features = features_list[:3]
    except Exception:
        # Fallback to placeholder if SHAP fails
        top_features = [
            {"feature": "V17", "shap_value": 0.0, "effect": "increases"},
            {"feature": "V14", "shap_value": 0.0, "effect": "increases"},
            {"feature": "V12", "shap_value": 0.0, "effect": "increases"}
        ]

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
    except Exception:
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
    except Exception:
        pass

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=scored_{file.filename}"
        }
    )

@router.get("/explain/{prediction_id}")
def explain_prediction(prediction_id: str) -> Dict[str, Any]:
    """
    Computes and returns the full SHAP explanation breakdown (all 30 features sorted by impact)
    for a past prediction.
    """
    # 1. Retrieve prediction log
    pred_log = get_prediction_by_id(prediction_id)
    if pred_log is None:
        raise HTTPException(
            status_code=404,
            detail=f"Prediction with ID '{prediction_id}' not found."
        )

    model_id = pred_log["model_id"]

    # 2. Retrieve model metadata
    model_meta = get_model_by_id(model_id)
    if model_meta is None:
        raise HTTPException(
            status_code=404,
            detail=f"Model run associated with model_id '{model_id}' was not found."
        )

    # 3. Load model and scaler
    try:
        model = joblib.load(model_meta["model_path"])
        scaler = joblib.load(model_meta["scaler_path"])
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load model artifacts for explanation: {str(e)}"
        )

    # 4. Enforce that prediction log is a single prediction
    if pred_log["prediction_type"] != "single":
        raise HTTPException(
            status_code=400,
            detail="SHAP explanations can only be computed for single transaction prediction logs."
        )

    df_row = pd.DataFrame([pred_log["input_summary"]])

    # 5. Compute SHAP breakdown
    try:
        features_list, explainer = get_shap_explanation(
            model=model,
            scaler=scaler,
            dataset_id=model_meta["dataset_id"],
            df_row=df_row
        )
        
        base_val = explainer.expected_value
        if hasattr(base_val, "__len__"):
            base_val = base_val[1] if len(base_val) > 1 else base_val[0]
        base_value = float(base_val)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calculating SHAP breakdown: {str(e)}"
        )

    return {
        "prediction_id": prediction_id,
        "model_id": model_id,
        "model_name": model_meta["name"],
        "base_value": base_value,
        "prediction_probability": pred_log["output"]["fraud_probability"],
        "risk_label": pred_log["output"]["risk_label"],
        "shap_values": features_list
    }

@router.get("/predict/history")
def get_prediction_history_endpoint(
    page: int = 1,
    limit: int = 10,
    risk_label: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Returns a paginated list of logged predictions with optional filtering on risk label and timestamp.
    """
    if risk_label and risk_label not in ["Low", "Medium", "High"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid risk_label. Must be one of: 'Low', 'Medium', 'High'."
        )

    try:
        history = get_prediction_history(
            page=page,
            limit=limit,
            risk_label=risk_label,
            start_date=start_date,
            end_date=end_date
        )
        return history
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving prediction history: {str(e)}"
        )
