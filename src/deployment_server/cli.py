import os
import sys
import click
import logging
from deployment_server.modules import acme, nginx
from deployment_server.packages.utils import validators
from deployment_server.modules import env


def init_logging(name: str, debug: bool = False):
    app_name = "deployer"
    logger = logging.getLogger(f"{app_name} - {name}")
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    log_format = "%(levelname)s - %(name)s - %(message)s"
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter(log_format))
    logger.addHandler(stream_handler)
    return logger


@click.group()
def main():
    pass


@click.command()
@click.argument("domain", nargs=-1, required=True)
@click.option("--dns", required=True, help="The dns provider.")
@click.option(
    "--ssl-root-dir",
    required=False,
    default="/etc/nginx/ssl",
    show_default=True,
    help="The directory to install the ssl certs.",
)
@click.option(
    "--reload-cmd",
    required=False,
    default='"/usr/bin/systemctl reload nginx"',
    show_default=True,
    help="The command to execute after renewing ssl certs.",
)
@click.option(
    "--acme-bin-path",
    required=False,
    default=os.path.expanduser("~/.acme.sh/acme.sh"),
    show_default=True,
    help="The directory where acme.sh is installed.",
)
@click.option(
    "--acme-home-path",
    required=False,
    default=os.path.expanduser("~/.acme.sh"),
    show_default=True,
    help="The directory where acme.sh keeps its configuration.",
)
@click.option("--debug/--no-debug", default=False, help="Enable debugging.")
def setup_ssl_certs(
    domain: tuple[str],
    dns: str,
    ssl_root_dir: str,
    reload_cmd: str,
    acme_bin_path: str,
    acme_home_path: str,
    debug: bool,
):
    """
    Issue and install ssl certificates for the given domains.

    DOMAIN is the list of domains to acquire ssl certificates.
    """
    if debug:
        os.environ["DEBUG"] = "1"
    logger = init_logging("setting up ssl certs...", env.is_debugging())
    logger.info("preparing")

    if validators.program_doesnt_exist(acme_bin_path):
        acme_bin = "acme.sh"
        if validators.program_doesnt_exist(acme_bin):
            logger.error("couldn't find acme.sh executable.")
            sys.exit(1)
    logger.debug("acme.sh executable found.")

    if not os.path.isdir(acme_home_path):
        logger.error("acme.sh home path doesn't exist or unable to access.")
        sys.exit(1)
    logger.debug("acme.sh home path found.")

    success, message = acme.setup_ssl_certs(
        domains=domain,
        dns_provider=dns,
        ssl_root_dir=ssl_root_dir,
        reload_cmd=reload_cmd,
        acme_bin=acme_bin_path,
        acme_home=acme_home_path,
        logger=logger,
    )
    if not success:
        logger.error(f"failed. {message}")
        sys.exit(1)

    logger.info("completed successfully.")


@click.command()
@click.argument("domain", nargs=-1, required=True)
@click.option("--revoke/--no-revoke", default=True, help="Also revoke certificates.")
@click.option(
    "--ssl-root-dir",
    required=False,
    default="/etc/nginx/ssl",
    show_default=True,
    help="The directory to where the ssl certs copied.",
)
@click.option(
    "--acme-bin-path",
    required=False,
    default=os.path.expanduser("~/.acme.sh/acme.sh"),
    show_default=True,
    help="The directory where acme.sh is installed.",
)
@click.option(
    "--acme-home-path",
    required=False,
    default=os.path.expanduser("~/.acme.sh"),
    show_default=True,
    help="The directory where acme.sh keeps its configuration.",
)
@click.option("--debug/--no-debug", default=False, help="Enable debugging.")
def remove_ssl_certs(
    domain: tuple[str],
    revoke: bool,
    ssl_root_dir: str,
    acme_bin_path: str,
    acme_home_path: str,
    debug: bool,
):
    """
    Remove ssl certificates for the given domains.

    DOMAIN is the list of domains to remove the ssl certificates.
    """
    if debug:
        os.environ["DEBUG"] = "1"
    logger = init_logging("removing ssl certs...", env.is_debugging())
    logger.info("preparing")

    if validators.program_doesnt_exist(acme_bin_path):
        acme_bin = "acme.sh"
        if validators.program_doesnt_exist(acme_bin):
            logger.error("couldn't find acme.sh executable.")
            sys.exit(1)
    logger.debug("acme.sh executable found.")

    if not os.path.isdir(acme_home_path):
        logger.error("acme.sh home path doesn't exist or unable to access.")
        sys.exit(1)
    logger.debug("acme.sh home path found.")

    success, message = acme.remove_ssl_certs(
        domain, revoke, ssl_root_dir, acme_bin_path, acme_home_path, logger
    )
    if not success:
        logger.error(f"failed. {message}")
        sys.exit(1)

    logger.info("completed successfully.")


@click.command()
@click.option(
    "-s",
    "--server-name",
    multiple=True,
    required=True,
    help="The hostname(s) to accept client requests on.",
)
@click.option("--upstream-name", required=True, help="The upstream name.")
@click.option(
    "-u",
    "--upstream-server",
    multiple=True,
    required=True,
    help="The upstream server(s).",
)
@click.option(
    "--ssl-cert-fullchain-file",
    required=False,
    default=nginx.template_ssl_cert_fullchain_file,
    show_default=True,
    help="The fullchain file path.",
)
@click.option(
    "--ssl-cert-key-file",
    required=False,
    default=nginx.template_ssl_cert_key_file,
    show_default=True,
    help="The key file path.",
)
@click.option(
    "--nginx-conf-dir",
    required=False,
    default="/etc/nginx/conf.d",
    show_default=True,
    help="The directory to save the nginx config file.",
)
def setup_proxy_host(
    server_name: tuple[str, ...],
    upstream_name: str,
    upstream_server: tuple[str, ...],
    ssl_cert_fullchain_file: str,
    ssl_cert_key_file: str,
    nginx_conf_dir: str,
):
    click.echo("setting up proxy host...")
    success, message = nginx.setup_proxy_host(
        server_names=server_name,
        upstream_name=upstream_name,
        upstream_servers=upstream_server,
        ssl_cert_fullchain_file=ssl_cert_fullchain_file,
        ssl_cert_key_file=ssl_cert_key_file,
        nginx_conf_dir=nginx_conf_dir,
    )
    if not success:
        click.UsageError(message).show()
        click.echo("setting up proxy host... failed.")
        sys.exit(1)

    click.echo("setting up proxy host... done.")


@click.command()
@click.option(
    "-s",
    "--server-name",
    multiple=True,
    required=True,
    help="The hostname(s) to accept client requests on.",
)
@click.option(
    "--root-dir", required=True, help="The root directory to serve files from."
)
@click.option(
    "-p",
    "--static-paths",
    multiple=True,
    required=True,
    help="Static path to serve with caching enabled.",
)
@click.option(
    "--ssl-cert-fullchain-file",
    required=False,
    default=nginx.template_ssl_cert_fullchain_file,
    show_default=True,
    help="The fullchain file path.",
)
@click.option(
    "--ssl-cert-key-file",
    required=False,
    default=nginx.template_ssl_cert_key_file,
    show_default=True,
    help="The key file path.",
)
@click.option(
    "--nginx-conf-dir",
    required=False,
    default="/etc/nginx/conf.d",
    show_default=True,
    help="The directory to save the nginx config file.",
)
def setup_static_host(
    server_name: tuple[str, ...],
    root_dir: str,
    static_paths: tuple[str, ...],
    ssl_cert_fullchain_file: str,
    ssl_cert_key_file: str,
    nginx_conf_dir: str,
):
    click.echo("setting up static host...")
    success, message = nginx.setup_static_host(
        server_names=server_name,
        root_dir=root_dir,
        static_paths=static_paths,
        ssl_cert_fullchain_file=ssl_cert_fullchain_file,
        ssl_cert_key_file=ssl_cert_key_file,
        nginx_conf_dir=nginx_conf_dir,
    )
    if not success:
        click.UsageError(message).show()
        click.echo("setting up static host... failed.")
        sys.exit(1)
    click.echo("setting up static host... done.")


main.add_command(setup_ssl_certs)
main.add_command(remove_ssl_certs)
main.add_command(setup_proxy_host)
main.add_command(setup_static_host)
