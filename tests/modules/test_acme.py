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
    success, message = acme.setup_ssl_certs(
        ("abc.com", "www.abc.com"), dns_provider, ssl_root_dir, reload_cmd
    )
    assert success == True
    assert mock_run.call_count == 2

    issue_call_args = [
        "acme.sh",
        "--issue",
        "-d",
        "abc.com",
        "-d",
        "www.abc.com",
        "--dns",
        f"dns_{dns_provider}",
    ]
    mock_run.assert_any_call(issue_call_args, capture_output=True, text=True)

    key_file = f"{ssl_root_dir}/abc.com/key.pem"
    fullchain_file = f"{ssl_root_dir}/abc.com/fullchain.pem"
    install_call_args = [
        "acme.sh",
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
    mock_run.assert_any_call(install_call_args, capture_output=True, text=True)

    mock_makedirs.assert_called_once_with(
        Path(f"{ssl_root_dir}/abc.com"), exist_ok=True
    )
