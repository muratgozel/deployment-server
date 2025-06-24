import os
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import PlainTextResponse
from deployment_server.modules import env
from deployment_server.init import init


def create_app() -> FastAPI:
    from deployment_server.containers import ServerContainer
    from deployment_server.packages.utils.customizers import get_openapi_custom
    from deployment_server.routers import health, project, deployment

    container = ServerContainer()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        await container.init_resources()
        yield
        await container.shutdown_resources()

    app = FastAPI(lifespan=lifespan)
    app.container = container
    app.openapi = get_openapi_custom
    app.include_router(health.router)
    app.include_router(project.router)
    app.include_router(deployment.router)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request, exc):
        return JSONResponse(content=exc.detail, status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request, exc):
        return JSONResponse(
            content={"error": {"code": "invalid_request"}}, status_code=400
        )

    @app.get("/", response_class=PlainTextResponse, operation_id="home")
    async def home():
        return PlainTextResponse(f"This is {container.config.codename()}")

    return app


def get_socket_fd():
    listen_fds = os.environ.get("LISTEN_FDS")
    listen_pid = os.environ.get("LISTEN_PID")

    if listen_fds and listen_pid:
        # verify the PID matches (security check)
        if int(listen_pid) == os.getpid():
            num_fds = int(listen_fds)
            if num_fds > 0:
                # first socket fd is always 3 (after stdin=0, stdout=1, stderr=2)
                return 3

    return None


if __name__ == "__main__":
    init()

    socket_fd = get_socket_fd()

    if socket_fd is not None:
        uvicorn.run(
            app="deployment_server.server:create_app", factory=True, fd=socket_fd
        )
    else:
        uvicorn.run(
            app="deployment_server.server:create_app",
            factory=True,
            host="0.0.0.0",
            port=int(os.environ.get("APPLICATION_SERVER_PORT")),
            reload=env.is_dev(),
        )
