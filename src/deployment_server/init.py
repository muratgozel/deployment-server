import argparse
import os
from deployment_server.modules import env


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
    parser.add_argument(
        "--port", required=False, help="Port number to run the server on."
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
    os.environ["APPLICATION_SERVER_PORT"] = (
        args.port
        or os.environ.get("APPLICATION_SERVER_PORT")
        or env.get_port_fallback()
    )
