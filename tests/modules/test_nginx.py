from unittest.mock import patch, MagicMock, mock_open
from deployment_server.modules import nginx


@patch("deployment_server.modules.nginx.is_nginx_available", return_value=True)
@patch("builtins.open", new_callable=mock_open)
@patch("subprocess.run")
@patch("os.path.exists", return_value=True)
def test_setup_proxy_host(mock_exists, mock_run, mock_open, mock_is_nginx_available):
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stderr = ""
    mock_run.return_value = mock_result

    server_names = ("abc.com", "www.abc.com")
    upstream_name = "some_prod_server"
    upstream_servers = ("127.0.0.1:8080", "127.0.0.1:8081")
    ssl_cert_fullchain_file = "/etc/nginx/ssl/abc.com/fullchain.pem"
    ssl_cert_key_file = "/etc/nginx/ssl/abc.com/key.pem"
    nginx_conf_dir = "/etc/nginx/conf.d"
    success, message = nginx.setup_proxy_host(
        server_names=server_names,
        upstream_name=upstream_name,
        upstream_servers=upstream_servers,
        ssl_cert_fullchain_file=ssl_cert_fullchain_file,
        ssl_cert_key_file=ssl_cert_key_file,
        nginx_conf_dir=nginx_conf_dir,
    )
    assert success == True

    mock_exists.assert_any_call(ssl_cert_fullchain_file)
    mock_exists.assert_any_call(ssl_cert_key_file)

    assert mock_run.call_count == 2
    mock_run.assert_any_call(
        ["service", "nginx", "reload"], text=True, capture_output=True
    )

    mock_open.assert_called_once_with(f"{nginx_conf_dir}/{server_names[0]}.conf", "w")


@patch("deployment_server.modules.nginx.is_nginx_available", return_value=True)
@patch("builtins.open", new_callable=mock_open)
@patch("subprocess.run")
@patch("os.path.isdir", return_value=True)
@patch("os.path.exists", return_value=True)
def test_setup_static_host(
    mock_exists, mock_isdir, mock_run, mock_open, mock_is_nginx_available
):
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stderr = ""
    mock_run.return_value = mock_result

    server_names = ("abc.com", "www.abc.com")
    root_dir = "/var/www/abc.com"
    static_paths = ("static", "assets")
    ssl_cert_fullchain_file = "/etc/nginx/ssl/abc.com/fullchain.pem"
    ssl_cert_key_file = "/etc/nginx/ssl/abc.com/key.pem"
    nginx_conf_dir = "/etc/nginx/conf.d"
    success, message = nginx.setup_static_host(
        server_names=server_names,
        root_dir=root_dir,
        static_paths=static_paths,
        ssl_cert_fullchain_file=ssl_cert_fullchain_file,
        ssl_cert_key_file=ssl_cert_key_file,
        nginx_conf_dir=nginx_conf_dir,
    )
    assert success == True

    mock_exists.assert_any_call(ssl_cert_fullchain_file)
    mock_exists.assert_any_call(ssl_cert_key_file)

    mock_isdir.assert_any_call(root_dir)

    assert mock_run.call_count == 2
    mock_run.assert_any_call(
        ["service", "nginx", "reload"], text=True, capture_output=True
    )

    mock_open.assert_called_once_with(f"{nginx_conf_dir}/{server_names[0]}.conf", "w")
