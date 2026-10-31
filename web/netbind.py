"""Как слушать сеть: только этот компьютер, Wi-Fi или Tailscale."""

from __future__ import annotations

import ipaddress
import socket
import subprocess

TAILSCALE_NET = ipaddress.ip_network("100.64.0.0/10")
BIND_MODES = ("local", "lan", "tailscale")
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def is_tailscale_ip(ip):
    try:
        addr = ipaddress.ip_address(str(ip).strip())
    except ValueError:
        return False
    return addr.version == 4 and addr in TAILSCALE_NET


def is_usable_ipv4(ip):
    try:
        addr = ipaddress.ip_address(str(ip).strip())
    except ValueError:
        return False
    return (
        addr.version == 4
        and not addr.is_loopback
        and not addr.is_link_local
        and not addr.is_unspecified
        and not addr.is_multicast
    )


def host_for_mode(mode):
    if mode == "local":
        return "127.0.0.1"
    if mode in ("lan", "tailscale"):
        return "0.0.0.0"
    raise ValueError(mode)


def saved_mode(settings):
    mode = settings.get("bind_mode") if isinstance(settings, dict) else None
    if mode in BIND_MODES:
        return mode
    if isinstance(settings, dict) and not settings.get("lan_access", True):
        return "local"
    return "lan"


def split_addresses(addresses):
    lan = []
    tailscale = []
    for raw in addresses:
        ip = str(raw).strip()
        if not is_usable_ipv4(ip):
            continue
        bucket = tailscale if is_tailscale_ip(ip) else lan
        if ip not in bucket:
            bucket.append(ip)
    return lan, tailscale


def _add_ip(found, ip):
    ip = str(ip).strip()
    if is_usable_ipv4(ip) and ip not in found:
        found.append(ip)


def _command_lines(command):
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=4,
            creationflags=_NO_WINDOW,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _tailscale_cli_ips():
    commands = [
        ["tailscale", "ip", "-4"],
        [r"C:\Program Files\Tailscale\tailscale.exe", "ip", "-4"],
    ]
    found = []
    for command in commands:
        for line in _command_lines(command):
            _add_ip(found, line)
        if found:
            break
    return found


def _adapter_ipv4s():
    found = []
    for line in _command_lines(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-NetIPAddress -AddressFamily IPv4 | Select-Object -ExpandProperty IPAddress",
        ]
    ):
        _add_ip(found, line)
    if found:
        return found
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            _add_ip(found, info[4][0])
    except OSError:
        pass
    return found


def default_route_ipv4():
    """Адрес сети, через которую компьютер выходит в интернет. Обычно это Wi-Fi."""
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(("192.0.2.1", 9))
        primary = probe.getsockname()[0]
        probe.close()
    except OSError:
        return ""
    if is_usable_ipv4(primary) and not is_tailscale_ip(primary):
        return primary
    return ""


def network_addresses():
    lan = []
    tailscale = []
    primary = default_route_ipv4()
    if primary:
        lan.append(primary)
    for ip in _tailscale_cli_ips():
        if is_tailscale_ip(ip) and ip not in tailscale:
            tailscale.append(ip)
    if not tailscale:
        extra_lan, extra_tailscale = split_addresses(_adapter_ipv4s())
        for ip in extra_tailscale:
            if ip not in tailscale:
                tailscale.append(ip)
        if not lan:
            lan.extend(extra_lan[:1])
    return {"lan": lan, "tailscale": tailscale}


def share_urls(mode, port, addresses=None):
    info = addresses if addresses is not None else network_addresses()
    local = f"http://127.0.0.1:{port}"
    if mode == "local":
        return {"local": local, "share": []}
    if mode == "tailscale":
        return {"local": local, "share": [f"http://{ip}:{port}" for ip in info["tailscale"]]}
    return {"local": local, "share": [f"http://{ip}:{port}" for ip in info["lan"]]}
