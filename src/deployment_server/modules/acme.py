import subprocess
import enum
import os
from pathlib import Path


class DnsProvider(enum.Enum):
    CLOUDFLARE = "cf"
    GANDI = "gandi_livedns"


def issue_ssl_certs(domains: tuple[str], dns_provider: str):
    args_domain = []
    for domain in domains:
        args_domain.append("-d")
        args_domain.append(domain)

    try:
        DnsProvider(dns_provider)
    except ValueError:
        return False, f"invalid dns provider: {dns_provider}"

    args = ["acme.sh", "--issue", *args_domain, "--dns", f"dns_{dns_provider}"]
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        return False, f"failed to issue ssl certs: {result.stderr}"

    return True, ""


def install_ssl_certs(primary_domain: str, ssl_root_dir: str, reload_cmd: str):
    ssl_certs_dir = Path(ssl_root_dir) / primary_domain
    os.makedirs(ssl_certs_dir, exist_ok=True)
    key_file = ssl_certs_dir / "key.pem"
    fullchain_file = ssl_certs_dir / "fullchain.pem"
    args = [
        "acme.sh",
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
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        return False, f"failed to install ssl certs: {result.stderr}"
    return True, ""


def setup_ssl_certs(
    domains: tuple[str], dns_provider: str, ssl_root_dir: str, reload_cmd: str
):
    if len(domains) == 0:
        return False, "no domains provided"

    primary_domain = domains[0]
    success, message = issue_ssl_certs(domains, dns_provider)
    if not success:
        return success, message

    success, message = install_ssl_certs(primary_domain, ssl_root_dir, reload_cmd)
    if not success:
        return success, message

    return True, ""
