from fastapi import APIRouter
from fastapi.responses import PlainTextResponse


router = APIRouter(prefix="/health", tags=["health"])


@router.get("/", response_class=PlainTextResponse, operation_id="healthcheck")
async def healthcheck():
    return PlainTextResponse("")
