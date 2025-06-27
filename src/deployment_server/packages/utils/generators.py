import jinja2


template_socket = """\
[Unit]
Description={{ service_id }} socket.
PartOf={{ service_id }}.service

[Socket]
ListenStream={{ port }}
Accept=no

[Install]
WantedBy=sockets.target
"""


template_socket_service = """\
[Unit]
Description={{ service_id }} service.

[Service]
Type=exec
User={{ user }}
Group={{ group }}
WorkingDirectory={{ application_dir }}
Environment=PYTHONPATH={{ application_dir }}
Environment=PYTHONUNBUFFERED=1
Environment=DEBUG=0
Environment=APPLICATION_MODE={{ mode }}
Environment=APPLICATION_CONFIG_DIR={{ application_config_dir }}
ExecStart={{ exec_start }}
Restart=always
RestartSec=5
TimeoutStartSec=30
TimeoutStopSec=30

# security hardening
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
BindReadOnlyPaths={{ application_config_dir }}
ReadWritePaths={{ application_logs_dir }} {{ application_data_dir }}

# resource limits
LimitNOFILE=65536
MemoryMax=1G

# logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier={{ service_id }}

[Install]
WantedBy=multi-user.target
"""


template_service = """\
[Unit]
Description={{ service_id }} service.
Requires=network.target
After=network.target

[Service]
Type=exec
User={{ user }}
Group={{ group }}
WorkingDirectory={{ application_dir }}
Environment=PYTHONPATH={{ application_dir }}
Environment=PYTHONUNBUFFERED=1
Environment=DEBUG=0
Environment=APPLICATION_MODE={{ mode }}
Environment=APPLICATION_CONFIG_DIR={{ application_config_dir }}
ExecStart={{ exec_start }}
ExecReload=/bin/kill -HUP $MAINPID
KillSignal=SIGTERM
Restart=always
RestartSec=5
TimeoutStartSec=30
TimeoutStopSec=30

# security hardening
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
BindReadOnlyPaths={{ application_config_dir }}
ReadWritePaths={{ application_logs_dir }} {{ application_data_dir }}

# resource limits
LimitNOFILE=65536
MemoryMax=2G

# logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier={{ service_id }}

[Install]
WantedBy=multi-user.target
"""


template_nginx_proxy_host = r"""
upstream {{ upstream_name }} {
    {{ upstream_servers }}

    # Connection pooling
    keepalive 32;
    keepalive_requests 100;
    keepalive_timeout 60s;
}

server {
    listen 80;
    listen [::]:80;
    server_name {{ server_name }};
    server_tokens off;

    # Redirect all HTTP requests to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 0.0.0.0:443 ssl;
    listen [::]:443 ssl;
    http2 on;
    server_name {{ server_name }};
    server_tokens off;

    # stronger ssl security
    # ref 1: https://raymii.org/s/tutorials/Strong_SSL_Security_On_nginx.html
    # ref 2: https://ssl-config.mozilla.org/#server=nginx&version=1.17.7&config=intermediate&openssl=1.1.1k&guideline=5.7
    ssl_certificate {{ ssl_cert_fullchain_file }};
    ssl_certificate_key {{ ssl_cert_key_file }};
    include /etc/nginx/ssl_intermediate.conf;

    add_header X-Content-Type-Options nosniff always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    #add_header Content-Security-Policy "frame-ancestors 'self' https://frontend.example.com" always;
    add_header Strict-Transport-Security "max-age=63072000" always;

    client_max_body_size 10M;
    client_body_timeout 10s;
    client_header_timeout 10s;

    location / {
        limit_req zone=one burst=5 delay=1;

        proxy_pass http://{{ upstream_name }};
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $server_name;
        proxy_set_header X-Forwarded-Port $server_port;
        proxy_connect_timeout 10s;
        proxy_send_timeout 10s;
        proxy_read_timeout 10s;
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        proxy_busy_buffers_size 8k;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
    }
}
"""


template_nginx_static_host = r"""
server {
    listen 80;
    listen [::]:80;
    server_name {{ server_name }};
    server_tokens off;

    # Redirect all HTTP requests to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 0.0.0.0:443 ssl;
    listen [::]:443 ssl;
    http2 on;
    server_name {{ server_name }};
    server_tokens off;

    ssl_certificate {{ ssl_cert_fullchain_file }};
    ssl_certificate_key {{ ssl_cert_key_file }};
    include /etc/nginx/ssl_intermediate.conf;

    sendfile on;
    sendfile_max_chunk 1m;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;

    root {{ root_dir }};
    index index.html
    error_page 404 @error404;

    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    #add_header Content-Security-Policy "default-src 'self'; frame-src 'self' https://api.example.com; frame-ancestors 'self'" always;
    add_header Strict-Transport-Security "max-age=63072000" always;

    location @error404 {
        try_files /404.html =404;
    }

    location = /favicon.ico {
        log_not_found off;
        access_log off;
        add_header Cache-Control "public";
        add_header Vary "Accept-Encoding";
        etag on;
        expires max;
    }

    location = /robots.txt {
        log_not_found off;
        access_log off;
        add_header Cache-Control "public";
        add_header Vary "Accept-Encoding";
        etag on;
        expires max;
    }

    location / {
        try_files $uri $uri/ $uri/index.html =404;

        add_header Cache-Control "no-cache, no-store, must-revalidate";
        add_header Pragma "no-cache";
        expires off;
        etag off;

        try_files $uri $uri/index.html =404;
    }

    # immutable caching for static assets with hash: /media/path/to/my-image.as76as67sa67.jpeg
    location ~* ^/{{ static_paths }}/(.*)\.[a-f0-9]{8,16}(@2x|@3x|@4x)?\.(css|js|png|jpg|jpeg|gif|ico|bmp|svg|woff|woff2|ttf|eot|webp|avif|mp4|webm)$ {
        add_header Cache-Control "public, immutable";
        add_header Vary "Accept-Encoding";
        etag off;
        expires max;

        try_files $uri =404;
    }

    # etag caching for static assets: /media/path/to/my-image.jpeg
    location ~* ^/{{ static_paths }}/ {
        add_header Cache-Control "public";
        add_header Vary "Accept-Encoding";
        etag on;
        expires max;

        try_files $uri =404;
    }

    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }
}
"""


def systemd_service_with_socket(
    service_id,
    application_dir: str,
    application_logs_dir: str,
    application_data_dir: str,
    application_config_dir: str,
    mode: str,
    user: str,
    group: str,
    exec_start: str,
    port: str | int,
):
    template = jinja2.Environment(
        loader=jinja2.BaseLoader(), keep_trailing_newline=True, lstrip_blocks=True
    ).from_string(template_socket_service)
    service = template.render(
        service_id=service_id,
        application_dir=application_dir,
        application_logs_dir=application_logs_dir,
        application_data_dir=application_data_dir,
        application_config_dir=application_config_dir,
        mode=mode,
        user=user,
        group=group,
        exec_start=exec_start,
    )

    template = jinja2.Environment(
        loader=jinja2.BaseLoader(), keep_trailing_newline=True, lstrip_blocks=True
    ).from_string(template_socket)
    socket = template.render(service_id=service_id, port=port)
    return service, socket


def systemd_service(
    service_id: str,
    application_dir: str,
    application_logs_dir: str,
    application_data_dir: str,
    application_config_dir: str,
    mode: str,
    user: str,
    group: str,
    exec_start: str,
):
    template = jinja2.Environment(
        loader=jinja2.BaseLoader(), keep_trailing_newline=True, lstrip_blocks=True
    ).from_string(template_service)
    return template.render(
        service_id=service_id,
        user=user,
        group=group,
        application_dir=application_dir,
        application_logs_dir=application_logs_dir,
        application_data_dir=application_data_dir,
        application_config_dir=application_config_dir,
        mode=mode,
        exec_start=exec_start,
    )


def nginx_proxy_host(
    server_name: str,
    upstream_name: str,
    upstream_servers: str,
    ssl_cert_fullchain_file: str,
    ssl_cert_key_file: str,
):
    template = jinja2.Environment(
        loader=jinja2.BaseLoader(), keep_trailing_newline=True, lstrip_blocks=True
    ).from_string(template_nginx_proxy_host)
    return template.render(
        upstream_name=upstream_name,
        upstream_servers=upstream_servers,
        server_name=server_name,
        ssl_cert_fullchain_file=ssl_cert_fullchain_file,
        ssl_cert_key_file=ssl_cert_key_file,
    )


def nginx_static_host(
    server_name: str,
    root_dir: str,
    ssl_cert_fullchain_file: str,
    ssl_cert_key_file: str,
    static_paths: str,
):
    template = jinja2.Environment(
        loader=jinja2.BaseLoader(), keep_trailing_newline=True, lstrip_blocks=True
    ).from_string(template_nginx_static_host)
    return template.render(
        server_name=server_name,
        ssl_cert_fullchain_file=ssl_cert_fullchain_file,
        ssl_cert_key_file=ssl_cert_key_file,
        root_dir=root_dir,
        static_paths=static_paths,
    )
