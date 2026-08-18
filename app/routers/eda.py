from fastapi import APIRouter, HTTPException
from app.services.database import get_cleaning_report, dataset_exists
from app.services.data_manager import data_manager
from app.services.eda import compute_eda

router = APIRouter(tags=["eda"])

@router.get("/eda/{dataset_id}")
def get_eda(dataset_id: str):
    """
    Calculates and returns EDA metrics (class balance, amount stats, 
    correlation matrix, top features) for a registered dataset.
    Requires that the dataset has been cleaned first.
    """
    # 1. Check if dataset exists in database
    try:
        if not dataset_exists(dataset_id):
            raise HTTPException(
                status_code=404,
                detail=f"Dataset with ID '{dataset_id}' not found."
            )
    except HTTPException:
        raise
    except Exception:
        pass # Database fallback

    # 2. Enforce that the dataset has been cleaned first
    try:
        report = get_cleaning_report(dataset_id)
        if report is None:
            raise HTTPException(
                status_code=400,
                detail=f"Dataset with ID '{dataset_id}' has not been cleaned. Please clean it first using GET /clean/{dataset_id}."
            )
    except HTTPException:
        raise
    except Exception as e:
        # Fallback in case of database connectivity issues, let it proceed to check in-memory data
        pass

    # 2. Retrieve the dataset from the data manager
    try:
        df = data_manager.get_dataset(dataset_id)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Dataset with ID '{dataset_id}' not found."
        )

    # 3. Compute EDA statistics
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
