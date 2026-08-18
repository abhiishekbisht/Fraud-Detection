from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

from app.services.database import init_db
from app.routers.upload import router as upload_router
from app.routers.cleaning import router as cleaning_router
from app.routers.eda import router as eda_router
from app.routers.train import router as train_router
from app.routers.models import router as models_router
from app.routers.predict import router as predict_router
from app.routers.pages import router as pages_router
from app.routers.downloads import router as downloads_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database on startup
    init_db()
    yield

app = FastAPI(
    title="FraudLens API",
    description="Automated Transaction Fraud Detection Platform Backend",
    version="1.0.0",
    lifespan=lifespan
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers with both /api prefix and root for maximum compatibility
routers = [
    upload_router,
    cleaning_router,
    eda_router,
    train_router,
    models_router,
    predict_router,
    downloads_router,
]

for r in routers:
    app.include_router(r, prefix="/api")
    app.include_router(r)

app.include_router(pages_router)

# Health check endpoints
@app.get("/health")
@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "FraudLens API"}

# Serve React SPA static assets if frontend/dist exists
from fastapi.staticfiles import StaticFiles
if os.path.exists("frontend/dist"):
    app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")
