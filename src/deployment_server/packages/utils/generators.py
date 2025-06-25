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
