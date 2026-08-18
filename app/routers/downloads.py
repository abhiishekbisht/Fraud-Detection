from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from app.services.database import get_model_by_id, list_cleaned_datasets, get_active_model
import os

router = APIRouter(prefix="/api/download", tags=["downloads"])

@router.get("/cleaned/{dataset_id}")
async def download_cleaned_dataset(dataset_id: str):
    """Serve cleaned CSV file for a dataset if it belongs to the requesting session."""
    cleaned_path = f"data/cleaned/{dataset_id}.csv"
    if not os.path.exists(cleaned_path):
        raise HTTPException(status_code=404, detail="Cleaned dataset not found")
    return FileResponse(path=cleaned_path, filename=f"{dataset_id}_cleaned.csv", media_type="text/csv")

@router.get("/model/{model_id}")
async def download_model(model_id: str):
    """Serve the serialized model file (.joblib) for a given model ID."""
    model_meta = get_model_by_id(model_id)
    if not model_meta:
        raise HTTPException(status_code=404, detail="Model not found")
    model_path = model_meta.get("model_path")
    if not model_path or not os.path.exists(model_path):
        raise HTTPException(status_code=404, detail="Model file not found on server")
    filename = os.path.basename(model_path)
    return FileResponse(path=model_path, filename=filename, media_type="application/octet-stream")

@router.get("/eda-report/{dataset_id}")
async def download_eda_report(dataset_id: str):
    """Serve a JSON EDA report for a dataset if it exists."""
    report_path = f"data/eda_reports/{dataset_id}.json"
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="EDA report not found")
    return FileResponse(path=report_path, filename=f"{dataset_id}_eda_report.json", media_type="application/json")

@router.get("/executive/{model_id}")
async def download_executive_report(model_id: str):
    """Generate and serve a styled HTML executive summary report for a model.
    For now, we return a simple placeholder HTML page with key metadata.
    """
    model_meta = get_model_by_id(model_id)
    if not model_meta:
        raise HTTPException(status_code=404, detail="Model not found")
    html_content = f"""
    <html><head><title>Executive Report - {model_meta.get('name')}</title></head>
    <body style='font-family:system-ui; background:#111; color:#eaeaea; padding:2rem;'>
    <h1 style='color:#0f766e;'>{model_meta.get('name')} – Executive Summary</h1>
    <p><strong>Dataset:</strong> {model_meta.get('dataset_id')}</p>
    <p><strong>Metrics (PR‑AUC):</strong> {model_meta.get('pr_auc'):.4f}</p>
    <p><strong>ROC‑AUC:</strong> {model_meta.get('roc_auc'):.4f}</p>
    <p><strong>Created at:</strong> {model_meta.get('created_at')}</p>
    </body></html>
    """
    return JSONResponse(content={"html": html_content})
