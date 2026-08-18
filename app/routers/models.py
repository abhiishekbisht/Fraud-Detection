from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from app.services.database import list_all_models, activate_model

router = APIRouter(tags=["models"])

@router.get("/models", response_model=List[Dict[str, Any]])
def get_models() -> List[Dict[str, Any]]:
    """
    Returns all trained model runs, complete with evaluation metrics, 
    dataset reference, and timestamps. Sorted by PR-AUC descending.
    """
    try:
        models_list = list_all_models()
        return models_list
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error listing trained models: {str(e)}"
        )

@router.post("/models/{model_id}/activate")
def activate_model_endpoint(model_id: str) -> Dict[str, Any]:
    """
    Activates a specific model run. Subsequent single and batch predictions 
    will automatically load and use this active model.
    """
    # Attempt to activate model in SQLite database
    activated = activate_model(model_id)
    
    if not activated:
        raise HTTPException(
            status_code=404,
            detail=f"Model run with ID '{model_id}' not found."
        )
        
    return {
        "message": f"Model '{model_id}' has been successfully activated.",
        "model_id": model_id,
        "is_active": True
    }
