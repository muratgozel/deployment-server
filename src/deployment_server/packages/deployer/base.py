import os
import pwd
import grp
import subprocess
import shutil
import venv
from typing import Any
from logging import Logger
from pathlib import Path
from typing import Annotated
from dependency_injector.wiring import Provide
from deployment_server.containers import WorkerContainer
from deployment_server.packages.utils import modifiers, generators


class Deployer:

    def __init__(self):
        self.logger = Annotated[Logger, Provide[WorkerContainer.logger]]
        self.application_root_dir = Path("/opt")
        self.user_root_dir = Path("/home")
        self.systemd_root_dir = Path("/etc/systemd/user")
        self.os_groups = ("deployer",)

    def deploy(
        self,
        project_code: str,
        mode: str,
        systemd_units: list[dict[str, Any]] = (),
        pip_package_name: str = None,
        pip_index_url: str = None,
        pip_index_user: str = None,
        pip_index_auth: str = None,
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

        try:
            self.run_database_migrations(db_migrations_root_dir)
        except Exception as ex:
            return False, str(ex)

        if len(systemd_units) > 0:
            self.setup_systemd_units(systemd_units, os_user, os_groups[0])

        return True, ""

    def setup_systemd_units(
        self, units: list[dict[str, Any]], os_user: str, os_group: str
    ):
        new_sockets = existing_sockets = new_services = existing_services = []
        for unit in units:
            unit_name = unit["name"]
            unit_port = unit["port"]
            socket_file_name = f"{unit_name}.socket"
            service_file_name = f"{unit_name}.service"
            socket_file_path = self.systemd_root_dir / socket_file_name
            service_file_path = self.systemd_root_dir / service_file_name

            if not socket_file_path.exists():
                socket_content = generators.systemd_socket(unit_name, unit_port)
                success, message = self.write_file(socket_file_path, socket_content)
                if not success:
                    raise ValueError(
                        f"failed to write systemd socket {socket_file_name}. error: {message}"
                    )
                new_sockets.append(unit_name)
            else:
                existing_sockets.append(unit_name)

            if not service_file_path.exists():
                service_content = generators.systemd_service(
                    unit_name, os_user, os_group
                )
                success, message = self.write_file(service_file_path, service_content)
                if not success:
                    raise ValueError(
                        f"failed to write systemd service {service_file_name}. error: {message}"
                    )
                new_services.append(unit_name)
            else:
                existing_services.append(unit_name)

        if len(new_sockets) > 0:
            args = ["sudo", "systemctl", "enable", *new_sockets]
            result = subprocess.run(args, capture_output=True, text=True)
            if result.returncode != 0:
                raise ValueError(
                    f"failed to enable new sockets. error: {result.stderr}"
                )
            args = ["sudo", "systemctl", "start", *new_sockets]
            result = subprocess.run(args, capture_output=True, text=True)
            if result.returncode != 0:
                raise ValueError(f"failed to start new sockets. error: {result.stderr}")

        if len(new_sockets) > 0 or len(new_services) > 0:
            args = ["sudo", "systemctl", "daemon-reload"]
            result = subprocess.run(args, capture_output=True, text=True)
            if result.returncode != 0:
                raise ValueError(
                    f"failed to execute daemon-reload. error: {result.stderr}"
                )

        if len(existing_services) > 0:
            args = ["sudo", "systemctl", "restart", *existing_services]
            result = subprocess.run(args, capture_output=True, text=True)
            if result.returncode != 0:
                raise ValueError(f"failed to start new sockets. error: {result.stderr}")

        stat = os.system(
            f"sudo systemctl status --no-pager f{' '.join([*new_sockets, *existing_sockets])}"
        )
        if stat != 0:
            raise ValueError(f"some systemd units aren't running.")

        return True

    def run_database_migrations(self, root_dir: Path):
        db_migrations_dir = root_dir / "db" / "migrations"
        if db_migrations_dir.exists():
            args = [
                "dbmate",
                "--wait",
                "--wait-timeout",
                "10",
                "-d",
                db_migrations_dir.as_posix(),
                "up",
            ]
            result = subprocess.run(args, capture_output=True, text=True)
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
        venv_dir = application_dir / ".venv"
        if not venv_dir.exists():
            venv.create(venv_dir, with_pip=True, upgrade_deps=True)
        self.logger.info(f"verified venv")

        py_exec = Path(venv_dir) / "bin" / "python"
        pip_exec = Path(venv_dir) / "bin" / "pip"
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
        os_groups = (os_group, *self.os_groups)

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

    def get_application_dir(self, project_code: str, mode: str):
        return self.application_root_dir / f"{mode}-{project_code}"

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
