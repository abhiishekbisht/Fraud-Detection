from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.services.database import init_db
from app.routers.upload import router as upload_router
from app.routers.cleaning import router as cleaning_router
from app.routers.eda import router as eda_router
from app.routers.train import router as train_router

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
    allow_origins=["*"],  # Adjust in production as needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(upload_router)
app.include_router(cleaning_router)
app.include_router(eda_router)
app.include_router(train_router)

@app.get("/health")
def health_check():
    """
    Simple health check endpoint that returns 'ok' status.
    """
    return {"status": "ok"}
