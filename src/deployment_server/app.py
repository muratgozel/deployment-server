from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.openapi.utils import get_openapi
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from deployment_server.dependencies import logger, AsyncSessionLocal
from deployment_server.routers import on_release


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # setup ops
    async with AsyncSessionLocal() as session:
        pass
    yield
    # cleanup
    pass


app = FastAPI()


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(content=exc.detail, status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    logger.debug(f"invalid request.", exc)
    return JSONResponse(content={"error": {"code": "invalid_request"}}, status_code=400)


def get_openapi_custom():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Deployment Server OpenAPI Schema",
        version="0.1.0",
        summary="All API endpoints for the deployment server.",
        description="This schema is auto-generated and used for SDK generation and documentation purposes.",
        servers=[
            {"url": "http://localhost:8000", "description": "development server."}
        ],
        routes=app.routes,
    )
    error_schema = {
        "type": "object",
        "properties": {
            "error": {
                "type": "object",
                "properties": {"code": {"type": "string"}},
                "required": ["code"],
            }
        },
        "required": ["error"],
    }
    openapi_schema["components"]["schemas"]["HTTPValidationError"] = error_schema
    openapi_schema["components"]["schemas"]["ValidationError"] = error_schema
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = get_openapi_custom


app.include_router(on_release.router)


@app.get("/", response_class=PlainTextResponse, operation_id="home")
async def home():
    return f"This is deployment server."


@app.get("/health", response_class=PlainTextResponse, operation_id="healthcheck")
async def healthcheck():
    return PlainTextResponse()
