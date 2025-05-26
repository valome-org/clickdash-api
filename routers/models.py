import os

from config.settings import LLM_MODEL
from fastapi import APIRouter, HTTPException
from openai import OpenAI

router = APIRouter()

# Initialize clients to check availability
openai_client = None
if os.getenv("OPENAI_API_KEY") and os.getenv("OPENAI_API_KEY") != "your-openai-api-key-here":
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


@router.get("/api/models/status")
async def get_model_status():
    """Get current model configuration and availability"""
    return {
        "current_model": LLM_MODEL,
        "available_models": {
            "openai": {
                "configured": openai_client is not None,
                "api_key_set": os.getenv("OPENAI_API_KEY") is not None and os.getenv("OPENAI_API_KEY") != "your-openai-api-key-here"
            },
            "gemini": {
                "configured": os.getenv("GOOGLE_API_KEY") is not None and os.getenv("GOOGLE_API_KEY") != "your-google-api-key-here",
                "api_key_set": os.getenv("GOOGLE_API_KEY") is not None and os.getenv("GOOGLE_API_KEY") != "your-google-api-key-here"
            }
        }
    }


@router.post("/api/models/switch")
async def switch_model(request: dict):
    """Switch between available models"""
    from config.settings import LLM_MODEL

    new_model = request.get("model", "").lower()
    if new_model not in ["openai", "gemini"]:
        raise HTTPException(status_code=400, detail="Invalid model. Choose 'openai' or 'gemini'")

    # Check if the requested model is available
    if new_model == "openai" and not openai_client:
        raise HTTPException(status_code=400, detail="OpenAI is not configured. Please set OPENAI_API_KEY")

    if new_model == "gemini" and (not os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY") == "your-google-api-key-here"):
        raise HTTPException(status_code=400, detail="Gemini is not configured. Please set GOOGLE_API_KEY")

    # Update the global LLM_MODEL variable
    import config.settings
    config.settings.LLM_MODEL = new_model

    return {"message": f"Model switched to {new_model}", "current_model": new_model}
