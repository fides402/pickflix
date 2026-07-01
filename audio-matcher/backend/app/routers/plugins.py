from fastapi import APIRouter

from app.config import get_settings
from app.services.plugin_scanner import scan_paths

router = APIRouter(prefix="/plugins", tags=["plugins"])


@router.get("")
async def list_plugins():
    settings = get_settings()
    found = scan_paths(settings.plugin_scan_path_list())
    return {
        "scan_paths": settings.plugin_scan_path_list(),
        "count": len(found),
        "plugins": [
            {
                "id": p.id,
                "name": p.name,
                "vendor": p.vendor,
                "bundle_path": p.bundle_path,
                "metadata_source": p.metadata_source,
                "classes": [{"name": c.name, "category": c.category} for c in p.classes],
            }
            for p in found
        ],
    }
