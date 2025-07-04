from deployment_server.init import init
from deployment_server.worker import create_worker
from deployment_server.modules import env


if __name__ == "__main__":
    init()

    schedule_db_file = (
        "/var/lib/prod-deployment-server-25-http/celerybeat-schedule"
        if env.is_prod()
        else "./celerybeat-schedule"
    )

    worker = create_worker()
    worker.start(["beat", "--loglevel=info", "--schedule", schedule_db_file])
