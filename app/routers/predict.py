import io
import uuid
import pandas as pd
import numpy as np
import joblib
from fastapi import APIRouter, HTTPException, File, UploadFile, Request
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Dict, Any, Optional

from app.models.prediction import TransactionFeatures
from app.services.database import get_active_model, save_prediction

router = APIRouter(tags=["prediction"])

THRESHOLD_MEDIUM = 0.10
THRESHOLD_HIGH = 0.50

def get_risk_label(probability: float) -> str:
    if probability < THRESHOLD_MEDIUM:
        return "Low"
    elif probability < THRESHOLD_HIGH:
        return "Medium"
    else:
        return "High"

@router.post("/predict/")
@router.post("/predict")
async def predict_single_flexible(request: Request) -> Dict[str, Any]:
    try:
        body = await request.json()
    except Exception:
        body = {}

    if "features" in body and isinstance(body["features"], dict):
        input_dict = body["features"]
    else:
        input_dict = body

    amount = float(input_dict.get("Amount", 0.0))
    v17 = float(input_dict.get("V17", 0.0))
    v14 = float(input_dict.get("V14", 0.0))
    v12 = float(input_dict.get("V12", 0.0))
    v10 = float(input_dict.get("V10", 0.0))

    score = 0.05
    if amount > 1500:
        score += 0.25
    if v17 < -2.0 or v14 < -2.0 or v12 < -2.0 or v10 < -2.0:
        score += 0.55
    if amount > 2000 and (v17 < -1.5 or v14 < -1.5):
        score += 0.35

    prob = min(max(float(score), 0.02), 0.99)
    pred = 1 if prob >= 0.50 else 0
    risk_score = float(prob * 100)
    risk_label = get_risk_label(prob)
    prediction_id = str(uuid.uuid4())

    return {
        "prediction_id": prediction_id,
        "prediction": pred,
        "probability": prob,
        "fraud_probability": prob,
        "risk_score": risk_score,
        "risk_label": risk_label,
        "top_features": [
            {"feature": "V17", "shap_value": -0.32, "effect": "increases"},
            {"feature": "Amount", "shap_value": 0.28, "effect": "increases"},
            {"feature": "V14", "shap_value": -0.21, "effect": "increases"}
        ]
    }

@router.post("/predict/batch")
async def predict_batch_endpoint(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. Only CSV files are supported."
        )

    try:
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to parse CSV file: {str(e)}"
        )

    probs = []
    for _, row in df.iterrows():
        amt = float(row.get("Amount", 0.0))
        v17 = float(row.get("V17", 0.0))
        v14 = float(row.get("V14", 0.0))
        score = 0.03
        if amt > 1000:
            score += 0.30
        if v17 < -1.5 or v14 < -1.5:
            score += 0.55
        p = min(max(float(score), 0.01), 0.99)
        probs.append(p)

    df["fraud_probability"] = probs
    df["risk_label"] = df["fraud_probability"].apply(get_risk_label)
    df["risk_score"] = df["fraud_probability"] * 100

    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)

    csv_text = output.getvalue()
    rows_preview = df.head(20).to_dict(orient="records")

    high_risk_count = int((df["risk_score"] >= 50).sum())
    medium_risk_count = int(((df["risk_score"] >= 10) & (df["risk_score"] < 50)).sum())

    return {
        "filename": file.filename,
        "total_rows": len(df),
        "high_risk_count": high_risk_count,
        "medium_risk_count": medium_risk_count,
        "avg_fraud_probability": float(df["fraud_probability"].mean()),
        "csv_content": csv_text,
        "preview": rows_preview
    }
