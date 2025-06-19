import argparse
import os
from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_init, worker_shutdown
from deployment_server.tasks.run_deployment import run_deployment
from deployment_server.modules import env


def create_worker() -> Celery:
    from deployment_server.containers import WorkerContainer

    container = WorkerContainer()
    worker = Celery("tasks", broker=container.config.rabbitmq_conn_str())
    worker.container = container

    @worker_init.connect
    def worker_init_handler(sender=None, **kwargs):
        container.init_resources()

    @worker_shutdown.connect
    def worker_shutdown_handler(sender=None, **kwargs):
        container.shutdown_resources()

    @worker.on_after_configure.connect
    def setup_periodic_tasks(sender: Celery, **kwargs):
        sender.add_periodic_task(
            crontab(minute="*"), run_deployment.s(), name="check deployments queue"
        )

    return worker


def init():
    parser = argparse.ArgumentParser(
        prog="Application Init Arguments Parser",
        description="Provides init arguments to the application to configure the way application works.",
    )
    parser.add_argument(
        "--mode",
        required=False,
        help="Runtime mode for the application. testing, staging, production etc.",
    )
    parser.add_argument(
        "--config-dir",
        required=False,
        help=f"A directory where application config will be kept. cwd by default.",
    )
    args = parser.parse_args()
    os.environ["APPLICATION_MODE"] = (
        args.mode or os.environ.get("APPLICATION_MODE") or env.get_mode_fallback()
    )
    os.environ["APPLICATION_CONFIG_DIR"] = os.path.expanduser(
        args.config_dir
        or os.environ.get("APPLICATION_CONFIG_DIR")
        or env.get_config_dir_fallback()
    )


if __name__ == "__main__":
    init()
    create_worker()
