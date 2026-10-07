"""Проверка остановки генерации промпта сцены."""

import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import customtkinter as ctk  # noqa: E402

from dungeon.ai_engine import SCENE  # noqa: E402
from dungeon.app import DungeonApp  # noqa: E402
from dungeon.i18n import DM_PREFIX, PLAYER_PREFIX  # noqa: E402
from tkhelpers import close_tk_window  # noqa: E402

DELAY = 0.05


class SlowHandler(BaseHTTPRequestHandler):
    """Медленный поток, чтобы успеть нажать «Стоп»."""

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        self.rfile.read(length)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        try:
            for i in range(200):
                payload = {"choices": [{"delta": {"content": f"token{i} "}}]}
                self.wfile.write(f"data: {json.dumps(payload)}\n\n".encode("utf-8"))
                self.wfile.flush()
                time.sleep(DELAY)
            self.wfile.write(b"data: [DONE]\n\n")
        except OSError:
            # Клиент повесил трубку при отмене — это ожидаемое поведение,
            # а не ошибка теста. OSError покрывает все разрывы соединения
            # (BrokenPipe/ConnectionReset на Unix, ConnectionAborted на Windows).
            pass

    def log_message(self, *args):
        pass


def test_scene_prompt_can_be_cancelled():
    server = ThreadingHTTPServer(("127.0.0.1", 0), SlowHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_address[1]}/v1/chat/completions"

    root = ctk.CTk()
    root.withdraw()
    app = DungeonApp(root)
    app.api_url = url
    app.model = ""
    app.api_key = ""
    app.language = "ru"
    app.history = [f"{PLAYER_PREFIX} ход", f"{DM_PREFIX} ответ"]

    opened = {"dialog": False}

    def spy(prompt, negative):
        opened["dialog"] = True

    app.show_scene_prompt = spy

    result = {}

    def on_done():
        result["done"] = True
        root.quit()

    def poll():
        if not app.scene_prompt_running:
            root.after(150, on_done)
        else:
            root.after(40, poll)

    app.generate_scene_prompt()

    # Ждём старта и жмём «Стоп» так же, как это делает кнопка
    def press_stop():
        if app.is_cancelled(SCENE):
            return
        if app.scene_prompt_running:
            app.request_stop_generation()
        else:
            root.after(40, press_stop)

    app.generate_scene_prompt()
    root.after(40, press_stop)
    root.after(40, poll)
    root.mainloop()
    server.shutdown()
    close_tk_window(app.root)

    assert result.get("done"), "генерация не остановилась"
    assert not opened.get("dialog"), "окно показано, хотя генерацию остановили"
    print("OK  генерация промпта сцены прерывается кнопкой «Стоп»")


if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    for name, fn in list(globals().items()):
        if name.startswith("test_") and fn.__code__.co_argcount == 0:
            fn()
    print("ALL SCENE CANCEL TESTS PASSED")
