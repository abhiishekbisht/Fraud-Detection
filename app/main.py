from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.services.data_manager import data_manager
from app.services.eda import compute_eda
from app.services.database import init_db
from app.routers.upload import router as upload_router
from app.routers.cleaning import router as cleaning_router

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

@app.get("/health")
def health_check():
    """
    Simple health check endpoint that returns 'ok' status.
    """
    return {"status": "ok"}

@app.get("/eda/{dataset_id}")
def get_eda(dataset_id: str):
    """
    Calculates and returns EDA metrics (class balance, amount stats, 
    correlation matrix, top features) for a registered dataset.
    """
    # 1. Retrieve the dataset from the data manager
    try:
        df = data_manager.get_dataset(dataset_id)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Dataset with ID '{dataset_id}' not found."
        )

    # 2. Compute EDA statistics
    try:
        eda_results = compute_eda(df)
        return eda_results
    except ValueError as val_err:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid dataset structure: {str(val_err)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error computing EDA metrics: {str(e)}"
        )
