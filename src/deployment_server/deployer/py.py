import os
import subprocess
import venv
from pathlib import Path
from deployment_server.config import config
from deployment_server.dependencies import logger
from deployment_server.models import Project
from deployment_server.core import git, systemd


def deploy(project: Project, install_dir: str):
    logger.debug(f"verifying venv...")
    venv_dir = os.path.join(install_dir, ".venv")
    if not os.path.isdir(venv_dir):
        logger.debug(f"creating venv for the first time...")
        venv.create(venv_dir, with_pip=True, upgrade_deps=True)
    logger.debug(f"verifying venv... done.")

    logger.debug(f"verifying package...")
    py_exec = Path(venv_dir) / "bin" / "python"
    pip_exec = Path(venv_dir) / "bin" / "pip"
    priv_url = git.make_git_url_privileged(
        project.pip_index_url, project.pip_index_user, project.pip_index_auth
    )
    args = [
        str(pip_exec),
        "install",
        "--upgrade",
        "--index-url",
        priv_url,
        project.pip_package_name,
    ]
    result = subprocess.run(
        args, cwd=install_dir, check=True, capture_output=True, text=True
    )
    if result.returncode != 0:
        logger.debug(f"verifying package... failed: {result.stderr}")
        return False, "verifying package... failed."
    logger.debug(f"verifying package... done.")

    logger.debug(f"verifying systemd service...")
    should_reload_systemd = False
    socket_name = f"{project.name}.socket"
    socket_file = os.path.join(config.systemd_dir, socket_name)
    if not os.path.isfile(socket_file):
        logger.debug(f"creating socket for the first time...")
        should_reload_systemd = True
        socket_content = systemd.generate_socket(project.name, 8000)
        systemd.write(socket_file, socket_content)

    service_name = f"{project.name}.service"
    service_file = os.path.join(config.systemd_dir, service_name)
    if not os.path.isfile(service_file):
        should_reload_systemd = True
        logger.debug(f"creating service for the first time...")
        service_content = systemd.generate_service(
            project.name, project.name, project.name
        )
        systemd.write(service_file, service_content)

    if should_reload_systemd:
        args = ["sudo", "systemctl", "daemon-reload"]
        result = subprocess.run(
            args, cwd=install_dir, check=True, capture_output=True, text=True
        )
        if result.returncode != 0:
            Path(socket_file).unlink(missing_ok=True)
            Path(service_file).unlink(missing_ok=True)
            logger.debug(f"verifying systemd service... failed: {result.stderr}")
            return False, "verifying systemd service... failed."
        args = ["sudo", "systemctl", "enable", socket_name]
        result = subprocess.run(
            args, cwd=install_dir, check=True, capture_output=True, text=True
        )
        if result.returncode != 0:
            logger.debug(f"verifying systemd service... failed: {result.stderr}")
            return False, "verifying systemd service... failed."
        args = ["sudo", "systemctl", "start", socket_name]
        result = subprocess.run(
            args, cwd=install_dir, check=True, capture_output=True, text=True
        )
        if result.returncode != 0:
            logger.debug(f"verifying systemd service... failed: {result.stderr}")
            return False, "verifying systemd service... failed."
    else:
        args = ["sudo", "systemctl", "restart", service_name]
        result = subprocess.run(
            args, cwd=install_dir, check=True, capture_output=True, text=True
        )
        if result.returncode != 0:
            logger.debug(f"verifying systemd service... failed: {result.stderr}")
            return False, "verifying systemd service... failed."

    stat = os.system(f"sudo systemctl status {socket_name}")
    if stat != 0:
        logger.error(
            f"verifying systemd service... failed: {socket_name} is not running."
        )
        return False, "verifying systemd service... failed."
    logger.debug(f"verifying systemd service... done.")
    return True, "deployed successfully."
