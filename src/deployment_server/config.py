import os
from dotenv import load_dotenv


load_dotenv()


class Config:
    name = "deployment-server"
    github_token = os.environ.get("GITHUB_TOKEN")
    postmark_server_token = os.environ.get("POSTMARK_SERVER_TOKEN")
    postmark_from = os.environ.get("POSTMARK_FROM")
    pg_conn_str = (
        os.environ.get("PG_CONN_STR") or "postgresql://localhost:5432/deployment_server"
    )
    github_webhook_secret_token = os.environ.get("GITHUB_WEBHOOK_SECRET_TOKEN")
    rabbitmq_conn_str = os.environ.get("RABBITMQ_CONN_STR")
    systemd_dir = "/etc/systemd/user"
    debug = True if os.environ.get("DEBUG") else False

    def __init__(self):
        self.dir = f"{os.path.expanduser("~")}/.{self.name}"


config = Config()
