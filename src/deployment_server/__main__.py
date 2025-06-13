import os
import uvicorn
from deployment_server.app import app


if __name__ == "__main__":
    uvicorn.run(
        app, host="0.0.0.0", port=8000, fd=3 if os.environ.get("LISTEN_FDS") else None
    )
