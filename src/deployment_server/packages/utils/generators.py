import jinja2


template_socket = """\
[Unit]
Description={{ name }} socket.
PartOf={{ name }}.service

[Socket]
ListenStream={{ port }}
Accept=no

[Install]
WantedBy=sockets.target
"""


template_socket_service = """\
[Unit]
Description={{ name }} service.
Requires={{ name }}.socket
After={{ name }}.socket

[Service]
Type=exec
User={{ user }}
Group={{ group }}
WorkingDirectory=/opt/{{ name }}
Environment=PYTHONPATH=/opt/{{ name }}
Environment=PYTHONUNBUFFERED=1
ExecStart=/opt/{{ name }}/.venv/bin/python -m {{ module_name }}
Restart=always
RestartSec=5
TimeoutStartSec=30
TimeoutStopSec=30

# socket activation
StandardInput=socket

# security hardening
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/var/log/{{ name }} /var/lib/{{ name }}

# resource limits
LimitNOFILE=65536
MemoryMax=1G

# logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier={{ name }}

[Install]
WantedBy=multi-user.target
"""


template_service = """\
[Unit]
Description={{ name }} service.
Requires=network.target
After=network.target

[Service]
Type=exec
User={{ user }}
Group={{ group }}
WorkingDirectory=/opt/{{ name }}
Environment=PYTHONPATH=/opt/{{ name }}
Environment=PYTHONUNBUFFERED=1
ExecStart=/opt/{{ name }}/.venv/bin/python -m {{ module_name }}
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
ReadWritePaths=/var/log/{{ name }} /var/lib/{{ name }}

# resource limits
LimitNOFILE=65536
MemoryMax=2G

# logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier={{ name }}

[Install]
WantedBy=multi-user.target
"""


def systemd_service_with_socket(
    name: str, user: str, group: str, module_name: str, port: str | int
):
    template = jinja2.Environment(
        loader=jinja2.BaseLoader(), keep_trailing_newline=True, lstrip_blocks=True
    ).from_string(template_socket_service)
    service = template.render(
        name=name, user=user, group=group, module_name=module_name
    )

    template = jinja2.Environment(
        loader=jinja2.BaseLoader(), keep_trailing_newline=True, lstrip_blocks=True
    ).from_string(template_socket)
    socket = template.render(name=name, port=port)
    return service, socket


def systemd_service(name: str, user: str, group: str, module_name: str):
    template = jinja2.Environment(
        loader=jinja2.BaseLoader(), keep_trailing_newline=True, lstrip_blocks=True
    ).from_string(template_socket_service)
    return template.render(name=name, user=user, group=group, module_name=module_name)
