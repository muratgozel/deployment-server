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


def generate_socket(name: str, port: str | int):
    template = jinja2.Environment(
        loader=jinja2.BaseLoader(), keep_trailing_newline=True, lstrip_blocks=True
    ).from_string(template_socket)
    return template.render(name=name, port=port)


template_service = """\
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
ExecStart=/opt/{{ name }}/.venv/bin/python -m {{ name }}
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
ReadWritePaths=/opt/{{ name }}/logs /opt/{{ name }}/data

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


def generate_service(name: str, user: str, group: str):
    template = jinja2.Environment(
        loader=jinja2.BaseLoader(), keep_trailing_newline=True, lstrip_blocks=True
    ).from_string(template_service)
    return template.render(name=name, user=user, group=group)


def write(file: str, content: str):
    try:
        with open(file, "w") as f:
            try:
                f.write(content)
                return True, "file saved successfully."
            except (IOError, OSError):
                return False, f"failed to write to file. file: {file}"
    except (FileNotFoundError, PermissionError, OSError):
        return False, f"failed to open file for writing. file: {file}"
