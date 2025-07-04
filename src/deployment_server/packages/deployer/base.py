import os
import pwd
import grp
import subprocess
import shutil
import re
import venv
from logging import Logger
from pathlib import Path
from typing import Annotated
from dependency_injector import containers, providers
from dependency_injector.wiring import Provide
from deployment_server.containers import WorkerContainer
from deployment_server.models import Daemon, DaemonType
from deployment_server.packages.utils import modifiers, generators


def find_yaml_files(service_name: str) -> list[str | Path]:
    config_dir = Path(os.environ.get("APPLICATION_CONFIG_DIR"))
    config_file_names_to_load = (
        "config.yaml",
        f"config_{os.environ.get('APPLICATION_MODE')}.yaml",
        f"config_{service_name}.yaml",
        f"config_{os.environ.get('APPLICATION_MODE')}_{service_name}.yaml",
    )
    yaml_files = [
        config_dir / name
        for name in config_file_names_to_load
        if (config_dir / name).exists()
    ]
    return yaml_files


class Container(containers.DeclarativeContainer):
    config = providers.Configuration(strict=True)


class Deployer:

    def __init__(self):
        self.logger = Annotated[Logger, Provide[WorkerContainer.logger]]
        self.application_root_dir = Path("/opt")
        self.application_config_root_dir = Path("/etc")
        self.application_logs_root_dir = Path("/var/log")
        self.application_data_root_dir = Path("/var/lib")
        self.user_root_dir = Path("/home")
        self.systemd_root_dir = Path("/etc/systemd/system")
        self.os_groups = ("deployer",)

    def deploy(
        self,
        project_code: str,
        mode: str,
        pip_package_name: str = None,
        pip_index_url: str = None,
        pip_index_user: str = None,
        pip_index_auth: str = None,
        daemons: list[Daemon] = None,
    ):
        try:
            application_dir, os_user, os_groups = self.verify_os_configuration(
                project_code, mode
            )
        except Exception as ex:
            return False, str(ex)

        # TODO fetch secrets

        db_migrations_root_dir = application_dir

        if pip_package_name is not None:
            try:
                pkg_dir, py_exec, pip_exec = self.install_pip_package(
                    project_code=project_code,
                    mode=mode,
                    pip_package_name=pip_package_name,
                    pip_index_url=pip_index_url,
                    pip_index_user=pip_index_user,
                    pip_index_auth=pip_index_auth,
                )
                db_migrations_root_dir = pkg_dir
            except Exception as ex:
                return False, str(ex)

        os.environ["APPLICATION_MODE"] = mode
        os.environ["APPLICATION_CONFIG_DIR"] = (
            self.get_application_config_dir(project_code, mode)
        ).as_posix()
        container = Container()
        container.config.set_yaml_files(files=find_yaml_files("deploy"))
        container.config.load()

        try:
            self.run_database_migrations(
                db_migrations_root_dir, container.config.pg_conn_str()
            )
        except Exception as ex:
            return False, str(ex)

        if daemons is not None and len(daemons) > 0:
            systemd_units = [d for d in daemons if d.type == DaemonType.SYSTEMD]
            if len(systemd_units) > 0:
                self.setup_systemd_units(
                    daemons=systemd_units,
                    project_code=project_code,
                    mode=mode,
                    os_user=os_user,
                    os_group=os_groups[0],
                )

        return True, ""

    def setup_systemd_units(
        self,
        daemons: list[Daemon],
        project_code: str,
        mode: str,
        os_user: str,
        os_group: str,
    ):
        application_dir = self.get_application_dir(project_code, mode)
        application_config_dir = self.get_application_config_dir(project_code, mode)
        application_logs_dir = self.get_application_logs_dir(project_code, mode)
        application_data_dir = self.get_application_data_dir(project_code, mode)

        new_sockets = new_socket_services = new_services = existing_sockets = (
            existing_socket_services
        ) = existing_services = []
        for d in daemons:
            service_id = f"{self.get_application_id(project_code, mode)}-{d.name}"
            py_exec, pip_exec = self.get_executables(self.get_venv_dir(application_dir))
            exec_start = f"{py_exec} -m {d.py_module_name}"
            if d.type == DaemonType.DOCKER:
                # NOTE no support for docker deployments currently
                continue
            if d.port:
                socket_file_name = f"{service_id}.socket"
                service_file_name = f"{service_id}.service"
                socket_file_path = self.systemd_root_dir / socket_file_name
                service_file_path = self.systemd_root_dir / service_file_name
                service_content, socket_content = (
                    generators.systemd_service_with_socket(
                        service_id=service_id,
                        application_dir=application_dir.as_posix(),
                        application_logs_dir=application_logs_dir.as_posix(),
                        application_data_dir=application_data_dir.as_posix(),
                        application_config_dir=application_config_dir.as_posix(),
                        exec_start=exec_start,
                        mode=mode,
                        user=os_user,
                        group=os_group,
                        port=d.port,
                    )
                )
                if not socket_file_path.exists():
                    success, message = self.write_file(socket_file_path, socket_content)
                    if not success:
                        raise ValueError(
                            f"failed to write systemd socket {socket_file_name}. error: {message}"
                        )
                    new_sockets.append(d.name)
                else:
                    existing_sockets.append(d.name)
                if not service_file_path.exists():
                    success, message = self.write_file(
                        service_file_path, service_content
                    )
                    if not success:
                        raise ValueError(
                            f"failed to write systemd service {service_file_name}. error: {message}"
                        )
                    new_socket_services.append(d.name)
                else:
                    existing_socket_services.append(d.name)
            else:
                service_file_name = f"{service_id}.service"
                service_file_path = self.systemd_root_dir / service_file_name
                service_content = generators.systemd_service(
                    service_id=service_id,
                    application_dir=application_dir.as_posix(),
                    application_logs_dir=application_logs_dir.as_posix(),
                    application_data_dir=application_data_dir.as_posix(),
                    application_config_dir=application_config_dir.as_posix(),
                    exec_start=exec_start,
                    mode=mode,
                    user=os_user,
                    group=os_group,
                )
                if not service_file_path.exists():
                    success, message = self.write_file(
                        service_file_path, service_content
                    )
                    if not success:
                        raise ValueError(
                            f"failed to write systemd service {service_file_name}. error: {message}"
                        )
                    new_services.append(d.name)
                else:
                    existing_services.append(d.name)

        new_services_combined = [*new_sockets, *new_services]

        if len(new_services_combined) > 0:
            args = ["sudo", "systemctl", "enable", *new_services_combined]
            result = subprocess.run(args, capture_output=True, text=True)
            if result.returncode != 0:
                raise ValueError(
                    f"failed to enable new sockets. error: {result.stderr}"
                )
            args = ["sudo", "systemctl", "start", *new_services_combined]
            result = subprocess.run(args, capture_output=True, text=True)
            if result.returncode != 0:
                raise ValueError(f"failed to start new sockets. error: {result.stderr}")

        if len([*new_services_combined, *new_socket_services]) > 0:
            args = ["sudo", "systemctl", "daemon-reload"]
            result = subprocess.run(args, capture_output=True, text=True)
            if result.returncode != 0:
                raise ValueError(
                    f"failed to execute daemon-reload. error: {result.stderr}"
                )

        if len(existing_socket_services) > 0:
            args = ["sudo", "systemctl", "restart", *existing_socket_services]
            result = subprocess.run(args, capture_output=True, text=True)
            if result.returncode != 0:
                raise ValueError(
                    f"failed to restart existing sockets. error: {result.stderr}"
                )

        if len(existing_services) > 0:
            args = ["sudo", "systemctl", "reload", *existing_services]
            result = subprocess.run(args, capture_output=True, text=True)
            if result.returncode != 0:
                raise ValueError(
                    f"failed to restart existing services. error: {result.stderr}"
                )

        stat = os.system(
            f"sudo systemctl status --no-pager f{' '.join([*new_sockets, *existing_sockets, *existing_services])}"
        )
        if stat != 0:
            raise ValueError(f"some systemd units aren't running.")

        return True

    def run_database_migrations(self, root_dir: Path, db_conn_str: str):
        db_migrations_dir = root_dir / "db" / "migrations"
        if db_migrations_dir.exists():
            args = [
                "dbmate",
                "--wait",
                "--wait-timeout",
                "10s",
                "-d",
                db_migrations_dir.as_posix(),
                "up",
            ]
            result = subprocess.run(
                args,
                env=dict(os.environ, DATABASE_URL=db_conn_str),
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                raise ValueError(f"failed to run db migrations: {result.stderr}")
        self.logger.info("verified db migrations")

        return True

    def install_pip_package(
        self,
        project_code: str,
        mode: str,
        pip_package_name: str,
        pip_index_url: str,
        pip_index_user: str,
        pip_index_auth: str,
    ) -> tuple[Path, Path, Path]:
        application_dir = self.get_application_dir(project_code, mode)
        venv_dir = self.get_venv_dir(application_dir)
        if not venv_dir.exists():
            venv.create(venv_dir, with_pip=True, upgrade_deps=True)
        self.logger.info(f"verified venv")

        py_exec, pip_exec = self.get_executables(venv_dir)
        priv_url = modifiers.add_auth_to_url(
            pip_index_url, pip_index_auth, pip_index_user
        )
        args = [
            str(pip_exec),
            "install",
            "--upgrade",
            "--index-url",
            priv_url,
            pip_package_name,
        ]
        result = subprocess.run(
            args, cwd=application_dir, capture_output=True, text=True
        )
        if result.returncode != 0:
            raise ValueError(
                f"failed to install/update package: {pip_package_name}. error: {result.stderr}"
            )
        self.logger.info(f"verified package {pip_package_name}")

        def get_package_location() -> tuple[bool, str, Path | None]:
            result = subprocess.run(
                [str(pip_exec), "show", pip_package_name],
                cwd=application_dir,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                return False, result.stderr, None
            for line in result.stdout.splitlines():
                if line.startswith("Location:"):
                    extracted_path = (
                        Path(line[line.find(":") + 1 :].strip()) / pip_package_name
                    )
                    return True, "", extracted_path
            return False, "couldn't find location", None

        success, error_message, pkg_dir = get_package_location()
        if not success:
            raise ValueError(
                f"failed to get package: {pip_package_name} location: {error_message}"
            )

        return pkg_dir, py_exec, pip_exec

    def verify_os_configuration(self, project_code: str, mode: str):
        os_user = project_code
        os_group = project_code
        os_groups = (*self.os_groups,)

        for group in os_groups:
            if not self.is_os_group_exists(group):
                result = subprocess.run(
                    ["groupadd", group], capture_output=True, text=True
                )
                if result.returncode != 0:
                    raise ValueError(f"failed to create os group: {group}")
        self.logger.info(f"verified os groups: {','.join(os_groups)}")

        if not self.is_os_user_exists(os_user):
            try:
                user_home = self.user_root_dir / os_user
                user_groups = ",".join(os_groups)
                args = [
                    "useradd",
                    "-d",
                    user_home.as_posix(),
                    "-m",
                    "-s",
                    "/bin/bash",
                    "-g",
                    os_group,
                    "-G",
                    user_groups,
                    os_user,
                ]
                result = subprocess.run(args, capture_output=True, text=True)
                if result.returncode != 0:
                    raise ValueError(f"failed to create os user: {os_user}")
                os.chmod(user_home, 0o750)
                os.makedirs(user_home / ".ssh", exist_ok=True)
                with open(user_home / ".ssh" / "authorized_keys", "w") as f:
                    pass
                os.chmod(user_home / ".ssh", 0o700)
                os.chmod(user_home / ".ssh" / "authorized_keys", 0o600)
            except Exception as ex:
                self.logger.error(f"failed to create user {os_user}. error: {str(ex)}")
                return False
        self.logger.info(f"verified os user: {os_user}")

        application_dir = self.get_application_dir(project_code, mode)
        os.makedirs(application_dir, exist_ok=True)
        os.chown(
            application_dir,
            pwd.getpwnam(os_user).pw_uid,
            grp.getgrnam(self.os_groups[0]).gr_gid,
        )
        self.logger.info(f"verified application directory: {str(application_dir)}")

        config_dir = self.get_application_config_dir(project_code, mode)
        os.makedirs(config_dir, exist_ok=True)
        os.chown(
            config_dir,
            pwd.getpwnam(os_user).pw_uid,
            grp.getgrnam(self.os_groups[0]).gr_gid,
        )
        os.chmod(config_dir, 0o755)
        critical_files = self.find_critical_files(config_dir)
        for file in critical_files:
            os.chown(
                file,
                pwd.getpwnam(os_user).pw_uid,
                grp.getgrnam(self.os_groups[0]).gr_gid,
            )
            os.chmod(file, 0o640)
        self.logger.info(
            f"verified application config directory and files: {str(config_dir)}"
        )

        application_logs_dir = self.get_application_logs_dir(project_code, mode)
        application_data_dir = self.get_application_data_dir(project_code, mode)
        os.makedirs(application_logs_dir, exist_ok=True)
        os.makedirs(application_data_dir, exist_ok=True)
        os.chown(
            application_logs_dir,
            pwd.getpwnam(os_user).pw_uid,
            grp.getgrnam(os_group).gr_gid,
        )
        os.chmod(application_logs_dir, 0o775)
        os.chown(
            application_data_dir,
            pwd.getpwnam(os_user).pw_uid,
            grp.getgrnam(os_group).gr_gid,
        )
        os.chmod(application_data_dir, 0o775)

        return application_dir, os_user, os_groups

    def remove_os_configuration(self, project_code: str, mode: str):
        application_dir = self.get_application_dir(project_code, mode)
        shutil.rmtree(application_dir, ignore_errors=True)

        os_user = project_code
        os_group = project_code

        if self.is_os_group_exists(os_group):
            result = subprocess.run(
                ["groupdel", os_group], capture_output=True, text=True
            )
            if result.returncode != 0:
                raise ValueError(f"failed to remove os group: {os_group}")

        if self.is_os_user_exists(os_user):
            result = subprocess.run(
                ["userdel", "-r", os_user], capture_output=True, text=True
            )
            if result.returncode != 0:
                raise ValueError(f"failed to remove os group: {os_user}")

        return True

    def find_critical_files(self, dir: Path):
        if not dir.exists():
            raise ValueError(f"directory doesn't exist: {dir}")
        if not dir.is_dir():
            raise ValueError(f"path is not a directory: {dir}")

        matching_files = []

        try:
            # all files (and subfolders) inside dir
            for item in os.listdir(dir):
                item_path = os.path.join(dir, item)

                if os.path.isdir(item_path):
                    continue

                if item.endswith(".yaml") and "config" in item.lower():
                    matching_files.append(item_path)

                elif item == ".env" or re.match(r"^\.env\..+$", item):
                    matching_files.append(item_path)

        except PermissionError:
            raise PermissionError(f"Permission denied accessing directory '{dir}'")

        return sorted(matching_files)

    def get_executables(self, venv_dir: Path):
        py_exec = venv_dir / "bin" / "python"
        pip_exec = venv_dir / "bin" / "pip"
        return py_exec, pip_exec

    def get_application_config_dir(self, project_code: str, mode: str):
        return self.application_config_root_dir / self.get_application_id(
            project_code, mode
        )

    def get_application_logs_dir(self, project_code: str, mode: str):
        return self.application_logs_root_dir / self.get_application_id(
            project_code, mode
        )

    def get_application_data_dir(self, project_code: str, mode: str):
        return self.application_data_root_dir / self.get_application_id(
            project_code, mode
        )

    def get_venv_dir(self, application_dir: Path):
        return application_dir / ".venv"

    def get_application_dir(self, project_code: str, mode: str):
        return self.application_root_dir / self.get_application_id(project_code, mode)

    def get_application_id(self, project_code: str, mode: str):
        return f"{mode}-{project_code}"

    def is_os_user_exists(self, username: str) -> bool:
        try:
            pwd.getpwnam(username)
            return True
        except KeyError:
            return False

    def is_os_group_exists(self, group_name: str) -> bool:
        try:
            grp.getgrnam(group_name)
            return True
        except KeyError:
            return False

    def write_file(self, file: str | Path, content: str):
        try:
            with open(file, "w") as f:
                try:
                    f.write(content)
                    return True, "file saved successfully."
                except (IOError, OSError):
                    return False, f"failed to write to file. file: {file}"
        except (FileNotFoundError, PermissionError, OSError):
            return False, f"failed to open file for writing. file: {file}"
