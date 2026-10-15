"""Основные действия игры: миры, ходы, память, карточки, сцена и суммаризация."""

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_web_api as base  # noqa: E402
from dungeon.api_stream import ACTION, CARDS, MEMORY, SCENE, SUMMARY  # noqa: E402
from dungeon.story_cards import description_text, format_story_cards_block  # noqa: E402
from web.server import create_app  # noqa: E402


def _client(tmp):
    base._use_tmp(tmp)
    app = create_app()
    return app, app.state.session, base.TestClient(app)


def _wait_idle(client, timeout=4):
    deadline = time.time() + timeout
    state = client.get("/api/state").json()
    while time.time() < deadline:
        state = client.get("/api/state").json()
        if not state["status"]["busy"]:
            return state
        time.sleep(0.05)
    raise AssertionError("операция не завершилась: " + str(state["status"]))


def _stub(session, replies):
    def read(_response, key, on_delta=None):
        body = replies.get(key, "ответ")
        if on_delta and key == ACTION:
            on_delta(body)
        return body, False

    session._api_post = lambda payload, **kwargs: base._Response()
    session._read_response = read


def _history_text(state):
    return "\n".join(row["text"] for row in state["history"])


def test_worlds_files_and_toggles():
    import tempfile

    with tempfile.TemporaryDirectory() as folder:
        tmp = Path(folder)
        _app, _session, client = _client(tmp)
        template = client.get("/api/worlds/template")
        assert template.status_code == 200
        assert "introduction.txt" in template.json()["files"]

        created = client.post(
            "/api/worlds",
            json={"name": "Лагерь", "files": {"plot_basics.txt": "завязка у костра"}},
        )
        assert created.status_code == 200, created.text
        assert client.get("/api/files").json()["plot_basics.txt"] == "завязка у костра"
        assert client.get("/api/worlds").json()["current"] == "Лагерь"

        assert client.post("/api/worlds", json={"name": "Лагерь"}).status_code == 409
        assert client.post("/api/worlds", json={"name": "a/b"}).status_code == 400

        intro = client.put("/api/files/introduction.txt", json={"content": "Ночь у ворот."})
        assert intro.status_code == 200, intro.text
        state = client.get("/api/state").json()
        assert state["history"][0]["kind"] == "intro"
        assert "Ночь у ворот" in state["history"][0]["text"]

        summary = client.post("/api/toggles/summary")
        assert summary.status_code == 200
        assert summary.json()["summary_enabled"] is False
        memory = client.post("/api/toggles/memory")
        assert memory.json()["memory_enabled"] is False
        stored = json.loads((tmp / "settings.json").read_text(encoding="utf-8"))
        assert stored["summary_enabled"] is False
        assert stored["memory_enabled"] is False

        assert client.post("/api/worlds", json={"name": "Другой"}).status_code == 200
        removed = client.delete("/api/worlds/Другой")
        assert removed.status_code == 200
        assert "Другой" not in client.get("/api/worlds").json()["worlds"]
        assert client.delete("/api/worlds/нет такого").status_code == 404
    print("OK  миры, вступление и переключатели суммаризации и памяти")


def test_cards_keep_object_descriptions_readable():
    card = {
        "id": "card_001",
        "title": "Арион",
        "description": {"Name": "Арион", "Age": 20, "Triggers": ["шрам"]},
        "triggers": ["арион"],
    }
    text = description_text(card["description"])
    assert "Name: Арион" in text
    assert "Age: 20" in text
    assert "[object Object]" not in text
    block = format_story_cards_block([card], "ru")
    assert "Name: Арион" in block

    import tempfile

    with tempfile.TemporaryDirectory() as folder:
        tmp = Path(folder)
        _app, _session, client = _client(tmp)
        assert client.post("/api/worlds", json={"name": "Camp"}).status_code == 200
        saved = client.put("/api/cards", json={"cards": [card]})
        assert saved.status_code == 200, saved.text
        loaded = client.get("/api/cards").json()["cards"][0]
        assert loaded["description"]["Name"] == "Арион"
        raw = json.loads((tmp / "Camp" / "story_cards.json").read_text(encoding="utf-8"))
        assert raw["cards"][0]["description"]["Age"] == 20
    print("OK  описание карточки-объекта читается текстом и сохраняется")


def test_edit_undo_and_regenerate():
    import tempfile

    with tempfile.TemporaryDirectory() as folder:
        tmp = Path(folder)
        app, session, client = _client(tmp)
        assert client.post("/api/worlds", json={"name": "Camp"}).status_code == 200
        client.put("/api/settings", json={"summary_enabled": False, "memory_enabled": False})
        history = ["Игрок: осмотреться", "Мастер: В зале темно."]
        (tmp / "Camp" / "history.json").write_text(json.dumps(history, ensure_ascii=False), encoding="utf-8")
        (tmp / "Camp" / "summary_state.json").write_text(json.dumps({"covered_count": 2}), encoding="utf-8")
        opened = client.post("/api/worlds/open", json={"name": "Camp"})
        assert opened.status_code == 200, opened.text
        player = next(row for row in opened.json()["history"] if row["kind"] == "player")

        edited = client.post(f"/api/history/{player['index']}", json={"text": "глянуть на потолок"})
        assert edited.status_code == 200, edited.text
        assert "потолок" in _history_text(edited.json())
        cursor = json.loads((tmp / "Camp" / "summary_state.json").read_text(encoding="utf-8"))
        assert cursor["covered_count"] <= player["index"]
        dm = next(row for row in edited.json()["history"] if row["kind"] == "dm")
        assert client.post(f"/api/history/{dm['index']}", json={"text": "   "}).status_code == 409

        _stub(session, {ACTION: "Новый ответ мастера"})
        assert client.post("/api/regenerate").status_code == 200
        state = _wait_idle(client)
        text = _history_text(state)
        assert "потолок" in text
        assert "Новый ответ мастера" in text
        assert "темно" not in text

        once = client.post("/api/undo")
        assert once.status_code == 200
        assert "Новый ответ мастера" not in _history_text(once.json())
        while True:
            step = client.post("/api/undo")
            if step.status_code == 409:
                break
            assert step.status_code == 200, step.text
        prompt = client.get("/api/prompt").json()["prompt"]
        assert prompt and "потолок" in prompt["user"]
    print("OK  правка, перегенерация и отмена хода")


def test_memory_summary_scene_and_card_description():
    import tempfile

    with tempfile.TemporaryDirectory() as folder:
        tmp = Path(folder)
        app, session, client = _client(tmp)
        assert client.post("/api/worlds", json={"name": "Camp"}).status_code == 200
        client.put(
            "/api/settings",
            json={"summary_enabled": False, "memory_enabled": True, "memory_interval": 1},
        )
        _stub(
            session,
            {
                ACTION: "Страж кивает.",
                MEMORY: '{"summary":"нашли ключ","keys":["ключ"],"location":"пещера","npcs":["страж"]}',
                SUMMARY: "Краткая хроника у ворот",
                SCENE: '{"prompt":"torchlight hall","negative_prompt":"blur"}',
                CARDS: "Рыцарь в тёмном плаще.",
            },
        )
        events = []
        original_emit = session.emit

        def capture(kind, **payload):
            events.append((kind, payload))
            return original_emit(kind, **payload)

        session.emit = capture

        assert client.post("/api/turn", json={"text": "спросить стража"}).status_code == 200
        state = _wait_idle(client)
        assert "Страж кивает" in _history_text(state)
        bank = client.get("/api/memory").json()
        assert bank["entries"]
        assert bank["entries"][-1]["summary"] == "нашли ключ"
        assert bank["entries"][-1]["keys"] == ["ключ"]
        stored = json.loads((tmp / "Camp" / "memory_bank.json").read_text(encoding="utf-8"))
        assert stored["entries"][-1]["location"] == "пещера"

        assert client.post("/api/summary").status_code == 200
        _wait_idle(client)
        assert (tmp / "Camp" / "summary.txt").read_text(encoding="utf-8") == "Краткая хроника у ворот"
        cursor = json.loads((tmp / "Camp" / "summary_state.json").read_text(encoding="utf-8"))
        assert cursor["covered_count"] == len(session.history)

        assert client.post("/api/scene").status_code == 200
        _wait_idle(client)
        scene = client.get("/api/scene").json()["scene"]
        assert scene["prompt"] == "torchlight hall"
        assert scene["negative"] == "blur"

        assert client.post("/api/cards/describe", json={"title": "Страж", "description": "у ворот"}).status_code == 200
        deadline = time.time() + 3
        while time.time() < deadline and not any(kind == "card_desc" for kind, _payload in events):
            time.sleep(0.05)
        described = [payload for kind, payload in events if kind == "card_desc"]
        assert described
        assert described[-1]["title"] == "Страж"
        assert "плаще" in described[-1]["text"]

        undone = client.post("/api/undo")
        assert undone.status_code == 200
        after = client.get("/api/memory").json()
        assert after["entries"] == []
        stored = json.loads((tmp / "Camp" / "memory_bank.json").read_text(encoding="utf-8"))
        assert stored["entries"] == []
    print("OK  память пишется на диск, суммаризация, сцена и описание карточки")


if __name__ == "__main__":
    test_worlds_files_and_toggles()
    test_cards_keep_object_descriptions_readable()
    test_edit_undo_and_regenerate()
    test_memory_summary_scene_and_card_description()
    print("ALL PLAY TESTS PASSED")
