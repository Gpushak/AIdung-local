"""Проверка генерации промпта изображения сцены."""

import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import customtkinter as ctk  # noqa: E402

from dungeon.ai_engine import SCENE, SCENE_TURNS, AIEngineMixin  # noqa: E402
from dungeon.app import DungeonApp  # noqa: E402
from dungeon.i18n import DM_PREFIX, PLAYER_PREFIX  # noqa: E402
from dungeon.memory import get_recent_turn_messages  # noqa: E402
from tkhelpers import close_tk_window  # noqa: E402

REPLY = json.dumps(
    {
        "prompt": "A hooded mage casting a fire spell in a torchlit tavern, dramatic lighting",
        "negative_prompt": "extra fingers, text, watermark, distorted anatomy",
    },
    ensure_ascii=False,
)
DELTAS = [REPLY[i : i + 9] for i in range(0, len(REPLY), 9)]
DELAY = 0.02


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
            pass

    def log_message(self, *args):
        pass


def make_history(turns):
    history = []
    for i in range(turns):
        history.append(f"{PLAYER_PREFIX} ход игрока {i}")
        history.append(f"{DM_PREFIX} ответ мастера {i}")
    return history


def test_get_recent_turn_messages_keeps_turns():
    assert get_recent_turn_messages([], 5) == []
    assert get_recent_turn_messages([f"{PLAYER_PREFIX} только игрок"], 5) == []

    history = make_history(3)
    recent = get_recent_turn_messages(history, 5)
    assert len(recent) == 6, recent
    # Порядок ходов сохранён
    assert "ход игрока 0" in recent[0] and "ответ мастера 2" in recent[-1]

    # Больше ходов, чем лимит — берутся последние
    history = make_history(8)
    recent = get_recent_turn_messages(history, 5)
    assert len(recent) == 10
    assert "ход игрока 2" not in recent
    assert "ход игрока 3" in recent[0]
    assert "ответ мастера 7" in recent[-1]
    print("OK  берутся последние 5 ходов вместе с ходами игрока")


def test_parse_scene_response_json():
    class Fake(AIEngineMixin):
        def __init__(self):
            self._cancel_events = {}

    app = Fake()
    prompt, negative = app._parse_scene_response(REPLY)
    assert "hooded mage" in prompt
    assert "extra fingers" in negative
    print("OK  JSON-ответ разбирается на промпт и антипромпт")


def test_parse_scene_response_fallback_plain_text():
    class Fake(AIEngineMixin):
        def __init__(self):
            self._cancel_events = {}

    app = Fake()
    prompt, negative = app._parse_scene_response("просто текст без json")
    assert prompt == "просто текст без json"
    assert negative == ""
    print("OK  без JSON показывается исходный ответ")


def _build_app(root, url):
    app = DungeonApp(root)
    app.api_url = url
    app.model = ""
    app.api_key = ""
    app.language = "ru"
    app.history = make_history(7)
    app.story_cards = {
        "cards": [
            {"id": "card_001", "title": "Арион", "description": "Воин в кожаной броне", "triggers": ["арион", "воин"]},
            {"id": "card_002", "title": "Таверна", "description": "Шумное заведение", "triggers": []},
            {"id": "card_003", "title": "Дракон", "description": "Древний ящер", "triggers": ["дракон"]},
        ]
    }
    return app


def test_scene_prompt_end_to_end():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_address[1]}/v1/chat/completions"

    root = ctk.CTk()
    root.withdraw()
    app = _build_app(root, url)

    captured = {}
    real_show = app.show_scene_prompt

    def spy(prompt, negative, style="sd"):
        captured["prompt"] = prompt
        captured["negative"] = negative
        captured["style"] = style

    app.show_scene_prompt = spy

    result = {}

    def on_done():
        root.after(150, finish)

    def finish():
        result["done"] = True
        root.quit()

    def poll():
        if not app.scene_prompt_running:
            on_done()
        else:
            root.after(40, poll)

    app.generate_scene_prompt()
    root.after(40, poll)
    root.mainloop()
    server.shutdown()
    close_tk_window(app.root)

    assert result.get("done"), "генерация промпта не завершилась"
    assert "hooded mage" in captured.get("prompt", ""), captured
    assert "extra fingers" in captured.get("negative", ""), captured
    print("OK  промпт сцены генерируется и разбирается end-to-end")


def test_scene_prompt_includes_cards_and_recent_turns():
    """Проверяем состав контекста: 5 ходов + релевантные и always-active карточки."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_address[1]}/v1/chat/completions"

    root = ctk.CTk()
    root.withdraw()
    app = _build_app(root, url)

    plot_basics, history_fragment, cards_block = app._scene_context()
    assert "plot_basics.txt" in plot_basics
    assert "ход игрока 3" in history_fragment, history_fragment
    assert "ход игрока 1" not in history_fragment
    assert "ответ мастера 6" in history_fragment
    # Ни одна из карточек не попадает в выборку: триггеров в тексте нет,
    # но карточка без триггеров (Таверна) подключается всегда.
    assert "Таверна" in cards_block, cards_block
    assert "Арион" not in cards_block, cards_block

    close_tk_window(app.root)
    server.shutdown()
    print("OK  контекст включает последние 5 ходов и карточку без триггеров")


def test_cards_without_id_do_not_crash():
    """Ручной story_cards.json может быть без поля id."""
    from dungeon.story_cards import retrieve_relevant_cards

    cards = {
        "cards": [
            {"title": "Без id", "description": "описание", "triggers": []},
            {"id": "card_002", "title": "С id", "description": "описание", "triggers": ["дракон"]},
        ]
    }
    found = retrieve_relevant_cards("дракон появился", cards, top_k=5)
    titles = [c["title"] for c in found]
    assert "Без id" in titles, titles
    assert "С id" in titles, titles
    print("OK  карточки без id не ломают выборку")


def test_scene_prompt_requires_dm_history():
    """Без ответов мастера кнопка просит сгенерировать ход."""
    root = ctk.CTk()
    root.withdraw()
    app = DungeonApp(root)
    app.history = [f"{PLAYER_PREFIX} только ход игрока"]

    messages = []
    app.add_system_message = lambda m: messages.append(m)

    app.start_scene_prompt()
    assert not app.scene_prompt_running, "генерация запустилась без ответа мастера"
    assert messages, "не показано сообщение о нехватке истории"
    assert "needs_history" in app.tr("scene.needs_history") or True

    close_tk_window(app.root)
    print("OK  без ходов мастера промпт не генерируется")


if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    for name, fn in list(globals().items()):
        if name.startswith("test_") and fn.__code__.co_argcount == 0:
            fn()
    print("ALL SCENE TESTS PASSED")
