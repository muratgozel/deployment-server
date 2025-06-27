import os
import shutil
import subprocess
from deployment_server.packages.utils import generators, validators


template_ssl_cert_fullchain_file = "/etc/nginx/ssl/<server_name>/fullchain.pem"
template_ssl_cert_key_file = "/etc/nginx/ssl/<server_name>/key.pem"


def is_nginx_available():
    return shutil.which("nginx") is not None


def setup_proxy_host(
    server_names: tuple[str, ...],
    upstream_name: str,
    upstream_servers: tuple[str, ...],
    ssl_cert_fullchain_file: str,
    ssl_cert_key_file: str,
    nginx_conf_dir: str,
):
    if len(server_names) == 0:
        return False, "no server names provided"

    if len(upstream_servers) == 0:
        return False, "no upstream servers provided"

    if validators.nginx_upstream_name(upstream_name) is False:
        return False, f"invalid upstream name: {upstream_name}"

    primary_server_name = server_names[0]

    if ssl_cert_fullchain_file == template_ssl_cert_fullchain_file:
        ssl_cert_fullchain_file = ssl_cert_fullchain_file.replace(
            "<server_name>", primary_server_name
        )

    if ssl_cert_key_file == template_ssl_cert_key_file:
        ssl_cert_key_file = ssl_cert_key_file.replace(
            "<server_name>", primary_server_name
        )

    if not os.path.exists(ssl_cert_fullchain_file):
        return False, f"ssl cert fullchain file not found: {ssl_cert_fullchain_file}"

    if not os.path.exists(ssl_cert_key_file):
        return False, f"ssl cert key file not found: {ssl_cert_key_file}"

    server_names_text = " ".join(server_names)
    upstream_servers_text = ""
    for u in upstream_servers:
        upstream_servers_text += f"    server {u};\n"

    content = generators.nginx_proxy_host(
        server_name=server_names_text,
        upstream_name=upstream_name,
        upstream_servers=upstream_servers_text,
        ssl_cert_fullchain_file=ssl_cert_fullchain_file,
        ssl_cert_key_file=ssl_cert_key_file,
    )

    if is_nginx_available():
        args = ["nginx", "-t", "-c", "/dev/stdin"]
        result = subprocess.run(args, input=content, text=True, capture_output=True)
        if result.returncode != 0:
            return False, f"failed to validate nginx config: {result.stderr}"

    with open(f"{nginx_conf_dir}/{primary_server_name}.conf", "w") as f:
        f.write(content)

    if is_nginx_available():
        args = ["service", "nginx", "reload"]
        result = subprocess.run(args, text=True, capture_output=True)
        if result.returncode != 0:
            return False, f"failed to reload nginx: {result.stderr}"

    return True, ""


def setup_static_host(
    server_names: tuple[str, ...],
    root_dir: str,
    static_paths: tuple[str, ...],
    ssl_cert_fullchain_file: str,
    ssl_cert_key_file: str,
    nginx_conf_dir: str,
):
    if len(server_names) == 0:
        return False, "no server names provided"

    primary_server_name = server_names[0]

    if ssl_cert_fullchain_file == template_ssl_cert_fullchain_file:
        ssl_cert_fullchain_file = ssl_cert_fullchain_file.replace(
            "<server_name>", primary_server_name
        )

    if ssl_cert_key_file == template_ssl_cert_key_file:
        ssl_cert_key_file = ssl_cert_key_file.replace(
            "<server_name>", primary_server_name
        )

    if not os.path.exists(ssl_cert_fullchain_file):
        return False, f"ssl cert fullchain file not found: {ssl_cert_fullchain_file}"

    if not os.path.exists(ssl_cert_key_file):
        return False, f"ssl cert key file not found: {ssl_cert_key_file}"

    if not os.path.isdir(root_dir):
        return False, f"root directory not found: {root_dir}"

    server_names_text = " ".join(server_names)
    static_paths_text = f"({'|'.join(static_paths)})"
    content = generators.nginx_static_host(
        server_name=server_names_text,
        root_dir=root_dir,
        ssl_cert_fullchain_file=ssl_cert_fullchain_file,
        ssl_cert_key_file=ssl_cert_key_file,
        static_paths=static_paths_text,
    )

    if is_nginx_available():
        args = ["nginx", "-t", "-c", "/dev/stdin"]
        result = subprocess.run(args, input=content, text=True, capture_output=True)
        if result.returncode != 0:
            return False, f"failed to validate nginx config: {result.stderr}"

    with open(f"{nginx_conf_dir}/{primary_server_name}.conf", "w") as f:
        f.write(content)

    if is_nginx_available():
        args = ["service", "nginx", "reload"]
        result = subprocess.run(args, text=True, capture_output=True)
        if result.returncode != 0:
            return False, f"failed to reload nginx: {result.stderr}"

    return True, ""
