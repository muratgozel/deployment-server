import subprocess
import enum
import os
import shutil
import click
from pathlib import Path


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

    args = ["./acme.sh", "--issue", *args_domain, "--dns", f"dns_{dns_provider}"]
    click.echo(f"setting up ssl certs... issuing command: {" ".join(args)}")
    result = subprocess.run(args, cwd=acme_bin_dir, capture_output=True, text=True)
    if result.returncode != 0:
        return False, f"failed to issue ssl certs: {result.stderr}"

    return True, ""


def install_ssl_certs(
    primary_domain: str, ssl_root_dir: str, reload_cmd: str, acme_bin_dir: str
):
    ssl_certs_dir = Path(ssl_root_dir) / primary_domain
    os.makedirs(ssl_certs_dir, exist_ok=True)
    key_file = ssl_certs_dir / "key.pem"
    fullchain_file = ssl_certs_dir / "fullchain.pem"
    args = [
        "./acme.sh",
        "--install",
        "-d",
        primary_domain,
        "--key-file",
        key_file.as_posix(),
        "--fullchain-file",
        fullchain_file.as_posix(),
        "--reloadcmd",
        reload_cmd,
    ]
    click.echo(f"setting up ssl certs... install command: {" ".join(args)}")
    result = subprocess.run(args, cwd=acme_bin_dir, capture_output=True, text=True)
    if result.returncode != 0:
        return False, f"failed to install ssl certs: {result.stderr}"
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


def remove_ssl_certs_renewal(domains: tuple[str, ...], acme_bin_dir: str):
    args_domain = []
    for domain in domains:
        args_domain.append("-d")
        args_domain.append(domain)

    args = ["./acme.sh", "--remove", *args_domain]
    result = subprocess.run(args, cwd=acme_bin_dir, capture_output=True, text=True)
    if result.returncode != 0:
        return False, f"failed to issue ssl certs: {result.stderr}"

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


def revoke_ssl_certs(domains: tuple[str, ...], acme_bin_dir: str):
    args_domain = []
    for domain in domains:
        args_domain.append("-d")
        args_domain.append(domain)

    args = ["./acme.sh", "--revoke", *args_domain, "--revoke-reason", "0"]
    result = subprocess.run(args, cwd=acme_bin_dir, capture_output=True, text=True)
    if result.returncode != 0:
        return False, f"failed to revoke ssl certs: {result.stderr}"

    return True, ""


def remove_ssl_certs(
    domains: tuple[str, ...], revoke: bool, acme_bin_dir: str, acme_data_dir: str
):
    if len(domains) == 0:
        return False, "no domains provided"

    success, message = remove_ssl_certs_renewal(domains, acme_bin_dir)
    if not success:
        return success, message

    success, message = remove_ssl_certs_from_filesystem(domains, acme_data_dir)
    if not success:
        return success, message

    if revoke is True:
        success, message = revoke_ssl_certs(domains, acme_bin_dir)
        if not success:
            return success, message

    return True, ""
