#!/usr/bin/env python3
"""Запуск веб-версии. Сначала окно выбора сети, затем сервер."""

import argparse
import socket
import sys
import threading
import webbrowser
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dungeon.storage import load_global_settings, read_json_with_backup, save_global_settings  # noqa: E402
from dungeon.storage import SETTINGS_FILE, CorruptedDataError  # noqa: E402
from web.launch_dialog import ask_bind_mode, tell_port_busy  # noqa: E402
from web.netbind import host_for_mode, share_urls  # noqa: E402
from web.server import WEB_PORT, create_app  # noqa: E402


def remember_bind_mode(mode):
    """Пишет только режим сети, не затирая остальные настройки."""
    if SETTINGS_FILE.exists():
        try:
            saved, _source = read_json_with_backup(SETTINGS_FILE, None)
        except CorruptedDataError:
            return
        if not isinstance(saved, dict):
            return
        saved["bind_mode"] = mode
        saved["lan_access"] = mode != "local"
        save_global_settings(saved)
        return
    settings = load_global_settings()
    settings["bind_mode"] = mode
    settings["lan_access"] = mode != "local"
    save_global_settings(settings)


def port_is_free(host, port):
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        probe.bind((host, port))
    except OSError:
        return False
    finally:
        probe.close()
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(description="Start AIDM web")
    parser.add_argument("--bind", choices=("local", "lan", "tailscale"))
    args = parser.parse_args(argv)
    settings = load_global_settings()
    mode = args.bind or ask_bind_mode(WEB_PORT, settings)
    if not mode:
        return 0
    host = host_for_mode(mode)
    if not port_is_free(host, WEB_PORT):
        tell_port_busy(WEB_PORT, settings.get("language", "ru"))
        return 1
    remember_bind_mode(mode)
    urls = share_urls(mode, WEB_PORT)
    print(urls["local"])
    for url in urls["share"]:
        print(url)
    threading.Timer(0.8, lambda: webbrowser.open(urls["local"])).start()
    uvicorn.run(create_app(bind_host=host), host=host, port=WEB_PORT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
