from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse
import os

router = APIRouter(tags=["pages"]) 

REACT_INDEX_PATH = os.path.join(os.path.dirname(__file__), "../../frontend/dist/index.html")

def _serve_react_spa():
    if os.path.exists(REACT_INDEX_PATH):
        return FileResponse(REACT_INDEX_PATH, media_type="text/html")
    return HTMLResponse(content="<h1>React build not found. Please run `npm run build`.</h1>", status_code=200)

@router.get("/app-upload", response_class=HTMLResponse)
def render_upload_page(request: Request):
    return _serve_react_spa()

@router.get("/eda-dashboard", response_class=HTMLResponse)
def render_eda_page(request: Request):
    return _serve_react_spa()

@router.get("/train-dashboard", response_class=HTMLResponse)
def render_train_page(request: Request):
    return _serve_react_spa()

@router.get("/predict-dashboard", response_class=HTMLResponse)
def render_predict_page(request: Request):
    return _serve_react_spa()

@router.get("/history-dashboard", response_class=HTMLResponse)
def render_history_page(request: Request):
    return _serve_react_spa()
