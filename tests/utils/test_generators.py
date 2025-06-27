from deployment_server.packages.utils import generators


def test_nginx_proxy_host():
    server_name = "abc.com www.abc.com"
    upstream_name = "some_prod_server"
    upstream_servers = """\
server 127.0.0.1:8080;
server 127.0.0.1:8081;
"""
    ssl_cert_fullchain_file = "/etc/nginx/ssl/abc.com/fullchain.pem"
    ssl_cert_key_file = "/etc/nginx/ssl/abc.com/key.pem"
    content = generators.nginx_proxy_host(
        server_name=server_name,
        upstream_name=upstream_name,
        upstream_servers=upstream_servers,
        ssl_cert_fullchain_file=ssl_cert_fullchain_file,
        ssl_cert_key_file=ssl_cert_key_file,
    )

    assert "upstream some_prod_server {" in content
    assert upstream_servers in content
    assert "server_name abc.com www.abc.com;" in content
    assert "proxy_pass http://some_prod_server;" in content


def test_nginx_static_host():
    server_name = "abc.com www.abc.com"
    root_dir = "/var/www/abc.com"
    static_paths = "(media|assets)"
    ssl_cert_fullchain_file = "/etc/nginx/ssl/abc.com/fullchain.pem"
    ssl_cert_key_file = "/etc/nginx/ssl/abc.com/key.pem"
    content = generators.nginx_static_host(
        server_name=server_name,
        root_dir=root_dir,
        static_paths=static_paths,
        ssl_cert_fullchain_file=ssl_cert_fullchain_file,
        ssl_cert_key_file=ssl_cert_key_file,
    )
    assert "server_name abc.com www.abc.com;" in content
    assert "root /var/www/abc.com;" in content
    assert "location ~* ^/(media|assets)/(.*)" in content
    assert "location ~* ^/(media|assets)/ {" in content
