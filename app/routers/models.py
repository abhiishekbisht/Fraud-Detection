from fastapi import APIRouter, HTTPException, Header
from typing import List, Dict, Any, Optional
from app.services.database import list_all_models, activate_model

router = APIRouter(tags=["models"])

@router.get("/models", response_model=List[Dict[str, Any]])
def get_models(x_session_id: Optional[str] = Header("global", alias="X-Session-ID")) -> List[Dict[str, Any]]:
    """
    Returns all trained model runs for the active session sorted by PR-AUC descending.
    """
    session_id = x_session_id or "global"
    try:
        models_list = list_all_models(session_id=session_id)
        return models_list
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error listing trained models: {str(e)}"
        )

@router.post("/models/{model_id}/activate")
def activate_model_endpoint(
    model_id: str,
    x_session_id: Optional[str] = Header("global", alias="X-Session-ID")
) -> Dict[str, Any]:
    """
    Activates a specific model run for the active session.
    """
    session_id = x_session_id or "global"
    activated = activate_model(model_id, session_id=session_id)
    
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

