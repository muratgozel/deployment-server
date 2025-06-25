import sys
import click
from deployment_server.modules import acme


@click.group()
def main():
    pass


@click.command()
@click.argument("domain", nargs=-1)
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
    default="service nginx reload",
    show_default=True,
    help="The command to execute after renewing ssl certs.",
)
def setup_ssl_certs(domain: tuple[str], dns: str, ssl_root_dir: str, reload_cmd: str):
    """
    Issue and install ssl certificates for the given domains.
    It uses acme.sh.

    DOMAIN is the list of domains to acquire ssl certificates.
    """
    success, message = acme.setup_ssl_certs(
        domains=domain,
        dns_provider=dns,
        ssl_root_dir=ssl_root_dir,
        reload_cmd=reload_cmd,
    )
    if not success:
        click.UsageError(message).show()
        sys.exit(1)

    click.echo("ssl certs issued and installed successfully.")


main.add_command(setup_ssl_certs)
