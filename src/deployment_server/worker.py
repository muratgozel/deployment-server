from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_init, worker_shutdown
from deployment_server.init import init
from deployment_server.modules import env


def create_worker() -> Celery:
    from deployment_server.containers import WorkerContainer
    from deployment_server.tasks.run_deployment import run_deployment

    container = WorkerContainer()
    worker = Celery("tasks", broker=container.config.rabbitmq_conn_str())
    worker.container = container

    @worker_init.connect
    def worker_init_handler(sender=None, **kwargs):
        container.init_resources()

    @worker_shutdown.connect
    def worker_shutdown_handler(sender=None, **kwargs):
        container.shutdown_resources()

    worker.conf.beat_schedule = {
        "check-deployments-queue": {
            "task": "deployment_server.tasks.run_deployment.run_deployment",
            "schedule": crontab(minute="*"),
        },
    }
    worker.conf.timezone = "UTC"

    return worker


if __name__ == "__main__":
    init()

    worker = create_worker()
    worker.worker_main(["worker", "--loglevel=info"])
