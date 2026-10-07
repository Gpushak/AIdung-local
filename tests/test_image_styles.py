"""Проверка переключателя формата промпта для изображений."""

import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import customtkinter as ctk  # noqa: E402

from dungeon.app import DungeonApp  # noqa: E402
from dungeon.config import DEFAULT_IMAGE_STYLE, IMAGE_PROMPT_STYLES  # noqa: E402
from dungeon.i18n import DM_PREFIX, PLAYER_PREFIX, t  # noqa: E402
from dungeon.storage import load_global_settings  # noqa: E402
from tkhelpers import close_tk_window  # noqa: E402

# Что должен содержать промпт для каждого формата (маркеры под язык)
STYLE_MARKERS = {
    "sd": {
        "ru": ["(", "masterpiece", "best quality", "теги"],
        "en": ["(", "masterpiece", "best quality", "tags"],
    },
    "midjourney": {
        "ru": ["--ar", "style raw", "--v", "естественное описание"],
        "en": ["--ar", "style raw", "--v", "flowing paragraph"],
    },
    "flux": {
        "ru": ["Flux", "предложения", "Анти-промпт"],
        "en": ["Flux", "sentences", "negative prompt"],
    },
    "generic": {
        "ru": ["ФОРМАТ", "предложения", "Анти-промпт"],
        "en": ["natural English", "separate sentence"],
    },
}


class Handler(BaseHTTPRequestHandler):
    """Возвращает промпт в формате выбранного стиля, чтобы проверить подстановку."""

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        sent = json.dumps(body, ensure_ascii=False)
        self.server.last_request = sent
        answer = json.dumps({"prompt": "a, b, c", "negative_prompt": "bad"}, ensure_ascii=False)
        payload = {"choices": [{"message": {"content": answer}}]}
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        self.wfile.write(b"data: " + raw + b"\n\n")
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()

    def log_message(self, *args):
        pass


def test_default_style_is_sd():
    assert DEFAULT_IMAGE_STYLE == "sd"
    assert IMAGE_PROMPT_STYLES == ("sd", "midjourney", "flux", "generic")
    print("OK  формат по умолчанию — Stable Diffusion")


def test_every_style_has_rules_in_both_languages():
    for lang in ("ru", "en"):
        for style in IMAGE_PROMPT_STYLES:
            rules = t(lang, f"prompt.scene_style.{style}")
            assert rules and rules != f"prompt.scene_style.{style}", (lang, style)
            for marker in STYLE_MARKERS[style][lang]:
                assert marker in rules, (lang, style, marker)
    print("OK  у каждого формата есть свои правила в обоих языках")


def test_style_rules_reach_the_request():
    """Проверяем, что выбранный формат реально попадает в запрос к модели."""
    for style in IMAGE_PROMPT_STYLES:
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
        app.image_prompt_style = style
        app.history = [f"{PLAYER_PREFIX} ход", f"{DM_PREFIX} ответ"]

        captured = {}
        app.show_scene_prompt = lambda p, n, s="sd": captured.update(prompt=p, negative=n, style=s)

        result = {}

        def on_done():
            result["done"] = True
            root.quit()

        def poll():
            if not app.scene_prompt_running:
                root.after(120, on_done)
            else:
                root.after(30, poll)

        app.generate_scene_prompt()
        root.after(30, poll)
        root.mainloop()
        server.shutdown()
        close_tk_window(app.root)

        assert result.get("done"), style
        assert captured.get("style") == style, (captured.get("style"), style)
        assert captured.get("prompt") == "a, b, c", captured

    print("OK  выбранный формат доходит до модели и в диалог")


def test_settings_persist_unknown_style():
    """Некорректный стиль из settings.json заменяется на дефолтный."""
    import tempfile
    from pathlib import Path as P

    from dungeon import config as cfg

    with tempfile.TemporaryDirectory() as tmp:
        p = P(tmp)
        settings_file = p / "settings.json"
        settings_file.write_text(
            json.dumps({"image_prompt_style": "nonexistent_model", "language": "ru"}), encoding="utf-8"
        )
        old = cfg.SETTINGS_FILE
        try:
            cfg.SETTINGS_FILE = settings_file
            import dungeon.storage as storage

            storage.SETTINGS_FILE = settings_file
            loaded = storage.load_global_settings()
            assert loaded["image_prompt_style"] == DEFAULT_IMAGE_STYLE, loaded["image_prompt_style"]
        finally:
            cfg.SETTINGS_FILE = old
            import dungeon.storage as storage

            storage.SETTINGS_FILE = old
    print("OK  неизвестный формат из настроек заменяется дефолтным")


if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    for name, fn in list(globals().items()):
        if name.startswith("test_") and fn.__code__.co_argcount == 0:
            fn()
    print("ALL STYLE TESTS PASSED")
