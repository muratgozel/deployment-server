from deployment_server.init import init
from deployment_server.worker import create_worker
from deployment_server.modules import env


if __name__ == "__main__":
    init()

    worker = create_worker()
    codename = worker.container.config.codename()
    mode = env.get_mode()
    data_dir_prod = f"/var/lib/{mode}-{codename}"
    schedule_db_file = (
        f"{data_dir_prod}/celerybeat-schedule"
        if env.is_prod()
        else "./celerybeat-schedule"
    )
    worker.start(["beat", "--loglevel=info", "--schedule", schedule_db_file])
