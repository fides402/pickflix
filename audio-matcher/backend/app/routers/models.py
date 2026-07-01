from fastapi import APIRouter, Query

from app.services.openrouter_client import OpenRouterClient

router = APIRouter(prefix="/models", tags=["models"])
_client = OpenRouterClient()


@router.get("/free")
async def list_free_models(refresh: bool = Query(False)):
    models = await _client.free_models(force_refresh=refresh)
    default_id = await _client.default_model_id()
    return {
        "default": default_id,
        "count": len(models),
        "models": [
            {"id": m.id, "name": m.name, "context_length": m.context_length, "selected": m.id == default_id}
            for m in models
        ],
    }
