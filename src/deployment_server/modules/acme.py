import subprocess
import enum
import os
import shutil
from pathlib import Path
from logging import Logger


class DnsProvider(enum.Enum):
    CLOUDFLARE = "cf"
    GANDI = "gandi_livedns"


def issue_ssl_certs(
    domains: tuple[str, ...],
    dns_provider: str,
    acme_bin: str,
    acme_home: str,
    logger: Logger,
):
    args_domain = []
    for domain in domains:
        args_domain.append("-d")
        args_domain.append(domain)

    try:
        DnsProvider(dns_provider)
    except ValueError:
        return False, f"invalid dns provider: {dns_provider}"

    logger.info("verifying ownership of domains. please wait...")
    args = [
        acme_bin,
        "--issue",
        *args_domain,
        "--dns",
        f"dns_{dns_provider}",
        "--server",
        "zerossl",
        "--config-home",
        acme_home,
    ]
    result = subprocess.run(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        universal_newlines=True,
    )
    logger.debug(f"issue command: {" ".join(args)}")
    logger.debug(f"issue command result: {result.stdout}")
    if result.returncode != 0:
        return False, f"failed. error details: {result.stdout}"
    logger.info("certificates issued successfully.")
    return True, ""


def install_ssl_certs(
    primary_domain: str,
    ssl_root_dir: str,
    reload_cmd: str,
    acme_bin: str,
    acme_home: str,
    logger: Logger,
):
    ssl_certs_dir = Path(ssl_root_dir) / primary_domain
    os.makedirs(ssl_certs_dir, exist_ok=True)
    key_file = ssl_certs_dir / "key.pem"
    fullchain_file = ssl_certs_dir / "fullchain.pem"
    logger.info("installing issued certificates.")
    args = [
        acme_bin,
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
        acme_home,
    ]
    result = subprocess.run(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        universal_newlines=True,
    )
    logger.debug(f"install command: {" ".join(args)}")
    logger.debug(f"install command result: {result.stdout}")
    if result.returncode != 0:
        return False, f"failed. error details: {result.stdout}"
    logger.info("certificates installed successfully.")
    return True, ""


def setup_ssl_certs(
    domains: tuple[str, ...],
    dns_provider: str,
    ssl_root_dir: str,
    reload_cmd: str,
    acme_bin: str,
    acme_home: str,
    logger: Logger,
):
    if len(domains) == 0:
        return False, "no domains provided"

    primary_domain = domains[0]
    logger.info(f"primary domain is {primary_domain}")

    success, message = issue_ssl_certs(
        domains, dns_provider, acme_bin, acme_home, logger
    )
    if not success:
        return success, message

    success, message = install_ssl_certs(
        primary_domain, ssl_root_dir, reload_cmd, acme_bin, acme_home, logger
    )
    if not success:
        return success, message

    return True, ""


def remove_ssl_certs(
    domains: tuple[str, ...],
    revoke: bool,
    ssl_root_dir: str,
    acme_bin: str,
    acme_home: str,
    logger: Logger,
):
    if len(domains) == 0:
        return False, "no domains provided"

    args_domain = []
    for domain in domains:
        args_domain.append("-d")
        args_domain.append(domain)
    primary_domain = domains[0]
    logger.info(f"primary domain is {primary_domain}")

    args = [acme_bin, "--remove", "--config-home", acme_home, *args_domain]
    if revoke:
        logger.info("will also revoke certificates.")
        args.append("--revoke")
    result = subprocess.run(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        universal_newlines=True,
    )
    logger.debug(f"remove command: {" ".join(args)}")
    logger.debug(f"remove command result: {result.stdout}")
    if result.returncode != 0:
        return False, f"failed. error details: {result.stdout}"
    logger.info("removed from acme client.")

    # remove from filesystem too
    for domain in domains:
        dir1 = Path(acme_home) / domain
        dir2 = Path(acme_home) / f"{domain}_ecc"
        if dir1.exists(follow_symlinks=False):
            shutil.rmtree(dir1)
        if dir2.exists(follow_symlinks=False):
            shutil.rmtree(dir2)
    ssl_certs_dir = Path(ssl_root_dir) / primary_domain
    shutil.rmtree(ssl_certs_dir)
    logger.info("removed from the filesystem.")
    return True, ""
