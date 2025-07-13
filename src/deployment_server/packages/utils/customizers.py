from typing import Annotated
from dependency_injector.wiring import inject, Provide
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from deployment_server.containers.server import ServerContainer


@inject
def generate_get_openapi_custom(
    app: FastAPI, codename: Annotated[str, Provide[ServerContainer.config.codename]]
):
    def get_openapi_custom():
        if app.openapi_schema:
            return app.openapi_schema

        openapi_schema = get_openapi(
            title="Deployment Server OpenAPI Schema",
            version="0.1.0",
            summary=f"All API endpoints for the {codename} server.",
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

    return get_openapi_custom
