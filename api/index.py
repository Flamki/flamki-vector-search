from fastapi import APIRouter

from api.runtime import get_runtime

router = APIRouter(prefix="/api", tags=["index"])


@router.get("/index/status")
async def index_status():
    runtime = get_runtime()
    return runtime.status()
