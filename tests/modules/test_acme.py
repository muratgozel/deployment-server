from unittest.mock import patch, MagicMock
from pathlib import Path
from deployment_server.modules import acme


@patch("subprocess.run")
@patch("os.makedirs")
def test_setup_ssl_certs(mock_makedirs, mock_run):
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stderr = ""
    mock_run.return_value = mock_result

    dns_provider = "cf"
    ssl_root_dir = "/etc/nginx/ssl"
    reload_cmd = "service nginx reload"
    acme_bin_dir = "/path/to/acme.sh"
    success, message = acme.setup_ssl_certs(
        ("abc.com", "www.abc.com"), dns_provider, ssl_root_dir, reload_cmd, acme_bin_dir
    )
    assert success == True
    assert mock_run.call_count == 2

    issue_call_args = [
        "./acme.sh",
        "--issue",
        "-d",
        "abc.com",
        "-d",
        "www.abc.com",
        "--dns",
        f"dns_{dns_provider}",
    ]
    mock_run.assert_any_call(
        issue_call_args, cwd=acme_bin_dir, capture_output=True, text=True
    )

    key_file = f"{ssl_root_dir}/abc.com/key.pem"
    fullchain_file = f"{ssl_root_dir}/abc.com/fullchain.pem"
    install_call_args = [
        "./acme.sh",
        "--install",
        "-d",
        "abc.com",
        "--key-file",
        key_file,
        "--fullchain-file",
        fullchain_file,
        "--reloadcmd",
        reload_cmd,
    ]
    mock_run.assert_any_call(
        install_call_args, cwd=acme_bin_dir, capture_output=True, text=True
    )

    mock_makedirs.assert_called_once_with(
        Path(f"{ssl_root_dir}/abc.com"), exist_ok=True
    )


@patch("subprocess.run")
@patch("shutil.rmtree")
def test_remove_ssl_certs(mock_rmtree, mock_run):
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stderr = ""
    mock_run.return_value = mock_result

    acme_bin_dir = "/path/to/acme.sh"
    acme_data_dir = "/path/to/acme.sh-data"
    success, message = acme.remove_ssl_certs(
        ("abc.com", "www.abc.com"), True, acme_bin_dir, acme_data_dir
    )
    assert success == True
    assert mock_run.call_count == 2

    remove_call_args = ["./acme.sh", "--remove", "-d", "abc.com", "-d", "www.abc.com"]
    mock_run.assert_any_call(
        remove_call_args, cwd=acme_bin_dir, capture_output=True, text=True
    )

    revoke_call_args = [
        "./acme.sh",
        "--revoke",
        "-d",
        "abc.com",
        "-d",
        "www.abc.com",
        "--revoke-reason",
        "0",
    ]
    mock_run.assert_any_call(
        revoke_call_args, cwd=acme_bin_dir, capture_output=True, text=True
    )

    mock_rmtree.assert_not_called()
