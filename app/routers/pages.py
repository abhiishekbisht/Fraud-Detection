from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import List, Dict, Any

from app.services.database import list_cleaned_datasets

router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
def render_upload_page(request: Request):
    """
    Renders the dataset upload and cleaning pipeline page.
    """
    return templates.TemplateResponse(
        request=request,
        name="upload.html",
        context={"active_page": "upload"}
    )

@router.get("/eda-dashboard", response_class=HTMLResponse)
def render_eda_page(request: Request):
    """
    Renders the statistical Exploratory Data Analysis dashboard page.
    """
    return templates.TemplateResponse(
        request=request,
        name="eda.html",
        context={"active_page": "eda"}
    )

@router.get("/train-dashboard", response_class=HTMLResponse)
def render_train_page(request: Request):
    """
    Renders the background training control studio and metrics dashboard.
    """
    return templates.TemplateResponse(
        request=request,
        name="train.html",
        context={"active_page": "train"}
    )

@router.get("/predict-dashboard", response_class=HTMLResponse)
def render_predict_page(request: Request):
    """
    Renders the inference center for single and batch predictions.
    """
    return templates.TemplateResponse(
        request=request,
        name="predict.html",
        context={"active_page": "predict"}
    )

@router.get("/history-dashboard", response_class=HTMLResponse)
def render_history_page(request: Request):
    """
    Renders the logged predictions audit history logs page.
    """
    return templates.TemplateResponse(
        request=request,
        name="history.html",
        context={"active_page": "history"}
    )


@router.get("/api/pages/cleaned-datasets", response_model=List[Dict[str, Any]])
def get_cleaned_datasets_api():
    """
    Helper API for select dropdowns, returning all datasets that completed cleaning.
    """
    try:
        datasets = list_cleaned_datasets()
        return datasets
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch cleaned datasets list: {str(e)}"
        )
