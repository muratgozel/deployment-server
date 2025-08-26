import subprocess
import enum
import os
import shutil
import click
from pathlib import Path
from deployment_server.modules import env


class DnsProvider(enum.Enum):
    CLOUDFLARE = "cf"
    GANDI = "gandi_livedns"


def issue_ssl_certs(domains: tuple[str, ...], dns_provider: str, acme_bin_dir: str):
    args_domain = []
    for domain in domains:
        args_domain.append("-d")
        args_domain.append(domain)

    try:
        DnsProvider(dns_provider)
    except ValueError:
        return False, f"invalid dns provider: {dns_provider}"

    env_vars = os.environ.copy()
    env_vars.update(
        {
            "AUTO_UPGRADE": "0",
            "ACME_DIRECTORY": acme_bin_dir,
            "LE_WORKING_DIR": acme_bin_dir,
        }
    )
    args = [
        "./acme.sh",
        "--issue",
        *args_domain,
        "--dns",
        f"dns_{dns_provider}",
        "--server",
        "zerossl",
        "--config-home",
        acme_bin_dir,
    ]
    result = subprocess.run(
        args,
        env=env_vars,
        cwd=acme_bin_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        universal_newlines=True,
        shell=True,
    )
    if env.is_debugging():
        click.echo(f"issue command: {" ".join(args)}")
        click.echo(f"issue command result: {result.stdout}")
    if result.returncode != 0:
        message = "failed to issue certs."
        if not env.is_debugging():
            message += f" error: {result.stdout}"
    return True, ""


def install_ssl_certs(
    primary_domain: str, ssl_root_dir: str, reload_cmd: str, acme_bin_dir: str
):
    ssl_certs_dir = Path(ssl_root_dir) / primary_domain
    os.makedirs(ssl_certs_dir, exist_ok=True)
    key_file = ssl_certs_dir / "key.pem"
    fullchain_file = ssl_certs_dir / "fullchain.pem"
    env_vars = os.environ.copy()
    env_vars.update(
        {
            "AUTO_UPGRADE": "0",
            "ACME_DIRECTORY": acme_bin_dir,
            "LE_WORKING_DIR": acme_bin_dir,
        }
    )
    args = [
        "./acme.sh",
        "--install-cert",
        "-d",
        primary_domain,
        "--key-file",
        key_file.as_posix(),
        "--fullchain-file",
        fullchain_file.as_posix(),
        "--reloadcmd",
        reload_cmd,
        "--config-home",
        "/root/acme.sh",
    ]
    result = subprocess.run(
        args,
        env=env_vars,
        cwd=acme_bin_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        universal_newlines=True,
    )
    if env.is_debugging():
        click.echo(f"install command: {" ".join(args)}")
        click.echo(f"install command result: {result.stdout}")
    if result.returncode != 0:
        message = "failed to install certs."
        if not env.is_debugging():
            message += f" error: {result.stdout}"
        return False, message
    return True, ""


def setup_ssl_certs(
    domains: tuple[str, ...],
    dns_provider: str,
    ssl_root_dir: str,
    reload_cmd: str,
    acme_bin_dir: str,
):
    if len(domains) == 0:
        return False, "no domains provided"

    primary_domain = domains[0]
    click.echo(f"setting up ssl certs... primary domain: {primary_domain}")
    success, message = issue_ssl_certs(domains, dns_provider, acme_bin_dir)
    if not success:
        return success, message

    success, message = install_ssl_certs(
        primary_domain, ssl_root_dir, reload_cmd, acme_bin_dir
    )
    if not success:
        return success, message

    return True, ""


def remove_ssl_certs_acme(domains: tuple[str, ...], acme_bin_dir: str, revoke: bool):
    args_domain = []
    for domain in domains:
        args_domain.append("-d")
        args_domain.append(domain)

    env_vars = os.environ.copy()
    env_vars.update(
        {
            "AUTO_UPGRADE": "0",
            "ACME_DIRECTORY": acme_bin_dir,
            "LE_WORKING_DIR": acme_bin_dir,
        }
    )
    args = ["./acme.sh", "--remove", "--config-home", "/root/acme.sh", *args_domain]
    if revoke:
        args.append("--revoke")
    result = subprocess.run(
        args,
        env=env_vars,
        cwd=acme_bin_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        universal_newlines=True,
    )
    if env.is_debugging():
        click.echo(f"remove command: {" ".join(args)}")
        click.echo(f"remove command result: {result.stdout}")
    if result.returncode != 0:
        message = "failed to remove."
        if not env.is_debugging():
            message += f" error: {result.stdout}"
        return False, message
    return True, ""


def remove_ssl_certs_from_filesystem(domains: tuple[str, ...], acme_data_dir: str):
    for domain in domains:
        dir1 = Path(acme_data_dir) / domain
        dir2 = Path(acme_data_dir) / f"{domain}_ecc"
        if dir1.exists(follow_symlinks=False):
            shutil.rmtree(dir1)
        if dir2.exists(follow_symlinks=False):
            shutil.rmtree(dir2)
    return True, ""


def remove_ssl_certs(
    domains: tuple[str, ...], revoke: bool, acme_bin_dir: str, acme_data_dir: str
):
    if len(domains) == 0:
        return False, "no domains provided"

    success, message = remove_ssl_certs_acme(domains, acme_bin_dir, revoke)
    if not success:
        return success, message

    success, message = remove_ssl_certs_from_filesystem(domains, acme_data_dir)
    if not success:
        return success, message

    return True, ""
