from deployment_server.init import init
from deployment_server.worker import create_worker
from deployment_server.modules import env


if __name__ == "__main__":
    init()

    worker = create_worker()
    worker.start(["beat", "--loglevel=info"])
