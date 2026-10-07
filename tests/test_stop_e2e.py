"""Сквозная проверка хода и остановки с поддельным сервером.

Поднимает локальный HTTP-сервер, отдающий OpenAI-совместимый поток, и
прогоняет настоящий process_action в фоновом потоке внутри работающего
mainloop Tk — так же, как в реальном приложении. Через N секунд
имитируется нажатие «Стоп».
"""

import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import customtkinter as ctk  # noqa: E402

from dungeon.ai_engine import ACTION  # noqa: E402
from dungeon.app import DungeonApp  # noqa: E402
from dungeon.i18n import DM_PREFIX, PLAYER_PREFIX  # noqa: E402
from tkhelpers import close_tk_window  # noqa: E402

DELTAS = [f"Предложение номер {i}. " for i in range(40)]
DELAY = 0.05


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        self.rfile.read(length)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        try:
            for delta in DELTAS:
                payload = {"choices": [{"delta": {"content": delta}}]}
                self.wfile.write(f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode("utf-8"))
                self.wfile.flush()
                time.sleep(DELAY)
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()
        except OSError:
            # Клиент отключился — ожидаемо при остановке. OSError покрывает
            # все разрывы соединения на любой ОС.
            pass

    def log_message(self, *args):
        pass


def run_case(stop_after=None):
    """Возвращает (завершился_ли_ход, история) для одного прогона."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_address[1]}/v1/chat/completions"

    root = ctk.CTk()
    root.withdraw()
    app = DungeonApp(root)
    app.api_url = url
    app.model = ""
    app.api_key = ""
    app.language = "ru"
    app.turns_since_summary = 0
    app.turns_since_memory = 0
    app._schedule_summary_after_turn = False
    app._schedule_memory_after_turn = False
    app.history = []
    app.begin_action_turn()

    done = {"finished": False, "stopped": False}
    result = {}

    def on_done():
        # Даём Tk выполнить оставшиеся after-коллбэки (финализация, служебные
        # сообщения), прежде чем снимать результат.
        root.after(120, lambda: _finish())

    def _finish():
        result["finished"] = True
        result["history"] = list(app.history)
        done["finished"] = True
        root.quit()

    def maybe_stop():
        if stop_after is not None and not done["stopped"]:
            done["stopped"] = True
            app.request_stop_generation()

    def poll_stop():
        maybe_stop()

    seen = {"chunks": []}
    original_append = app.append_to_dm_stream

    def counting_append(chunk):
        seen["chunks"].append(chunk)
        original_append(chunk)

    app.append_to_dm_stream = counting_append

    # Запускаем ход и планируем остановку
    threading.Thread(target=app.process_action, args=("Игрок осматривается.",), daemon=True).start()
    if stop_after is not None:
        # Останавливаем через stop_after дельт по времени: поток идёт по 50 мс
        # на предложение, поэтому 3 дельты ≈ 150 мс от начала.
        root.after(int(stop_after * DELAY * 1000), maybe_stop)

    def poll():
        if not app.processing:
            on_done()
        else:
            root.after(50, poll)

    root.after(50, poll)
    root.mainloop()
    app.append_to_dm_stream = original_append
    server.shutdown()
    # Гасим отложенные after-коллбэки CustomTkinter до уничтожения окна,
    # иначе Tcl печатает «invalid command name ...» уже после destroy.
    close_tk_window(app.root)
    return result["finished"], result.get("history", [])


def test_full_turn_without_stop():
    finished, history = run_case(stop_after=None)
    assert finished, "ход не завершился"
    assert len(history) == 2, history
    assert history[0].startswith(PLAYER_PREFIX)
    reply = history[1]
    assert reply.startswith(DM_PREFIX)
    assert "Предложение номер 39" in reply, "ответ обрезан: " + reply[-80:]
    print("OK  полный ход без остановки получает весь ответ")


def test_turn_cancelled_keeps_partial_reply():
    # 12 дельт по 50 мс ≈ 600 мс: к этому моменту ответ уже наполовину в логе,
    # но поток ещё далеко от конца (всего 40 дельт ≈ 2 с)
    finished, history = run_case(stop_after=12)
    assert finished, "ход не завершился после остановки"
    assert len(history) == 2, history
    reply = history[1]
    assert reply.startswith(DM_PREFIX)
    assert "Предложение номер 39" not in reply, "остановка не сработала: ответ полный"
    assert "Предложение номер 0" in reply, "частичный ответ потерян"
    # Часть ответа должна быть, но не вся — остановка сработала по делу
    assert reply.count("Предложение") < len(DELTAS), reply
    print("OK  остановка сохраняет уже полученную часть ответа")


if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    for name, fn in list(globals().items()):
        if name.startswith("test_") and fn.__code__.co_argcount == 0:
            fn()
    print("ALL E2E TESTS PASSED")
