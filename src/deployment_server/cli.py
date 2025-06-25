import os
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
@click.option(
    "--acme-bin-dir",
    required=False,
    default=os.path.expanduser("~/acme.sh"),
    show_default=True,
    help="The directory where acme.sh is installed.",
)
def setup_ssl_certs(
    domain: tuple[str], dns: str, ssl_root_dir: str, reload_cmd: str, acme_bin_dir: str
):
    """
    Issue and install ssl certificates for the given domains.

    DOMAIN is the list of domains to acquire ssl certificates.
    """
    click.echo("setting up ssl certs...")
    success, message = acme.setup_ssl_certs(
        domains=domain,
        dns_provider=dns,
        ssl_root_dir=ssl_root_dir,
        reload_cmd=reload_cmd,
        acme_bin_dir=acme_bin_dir,
    )
    if not success:
        click.UsageError(message).show()
        click.echo("setting up ssl certs... failed.")
        sys.exit(1)

    click.echo("setting up ssl certs... done.")


@click.command()
@click.argument("domain", nargs=-1)
@click.option("--revoke/--no-revoke", default=True, help="Also revoke certificates.")
@click.option(
    "--acme-bin-dir",
    required=False,
    default=os.path.expanduser("~/acme.sh"),
    show_default=True,
    help="The directory where acme.sh is installed.",
)
@click.option(
    "--acme-data-dir",
    required=False,
    default=os.path.expanduser("~/.acme.sh"),
    show_default=True,
    help="The directory where acme.sh stores its data.",
)
def remove_ssl_certs(
    domain: tuple[str], revoke: bool, acme_bin_dir: str, acme_data_dir: str
):
    """
    Remove ssl certificates for the given domains.

    DOMAIN is the list of domains to remove the ssl certificates.
    """
    click.echo("removing ssl certs...")

    success, message = acme.remove_ssl_certs(
        domain, revoke, acme_bin_dir, acme_data_dir
    )
    if not success:
        click.UsageError(message).show()
        click.echo("removing ssl certs... failed.")
        sys.exit(1)

    click.echo("removing ssl certs... done.")


main.add_command(setup_ssl_certs)
main.add_command(remove_ssl_certs)
