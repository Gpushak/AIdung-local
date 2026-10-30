"""Проверка веб-версии через HTTP, без окна Tk и без сети."""

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import dungeon.config as config  # noqa: E402
import dungeon.storage as storage  # noqa: E402
import web.session as session_mod  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from web.server import create_app  # noqa: E402


class _Response:
    def raise_for_status(self):
        return None

    def close(self):
        return None


def _use_tmp(tmp: Path):
    tmp.mkdir(parents=True, exist_ok=True)
    settings = tmp / "settings.json"
    config.BASE_DIR = tmp
    config.SETTINGS_FILE = settings
    storage.BASE_DIR = tmp
    storage.SETTINGS_FILE = settings
    session_mod.BASE_DIR = tmp


def test_file_save_and_summary_threshold(tmp_path=None):
    import tempfile

    with tempfile.TemporaryDirectory() as folder:
        tmp = Path(folder)
        _use_tmp(tmp)
        client = TestClient(create_app())
        created = client.post("/api/worlds", json={"name": "Camp"})
        assert created.status_code == 200, created.text
        saved = client.put("/api/files/plot_basics.txt", json={"content": "новый сюжет"})
        assert saved.status_code == 200, saved.text
        assert "новый сюжет" in client.get("/api/files").json()["plot_basics.txt"]
        assert (tmp / "Camp" / "plot_basics.txt").read_text(encoding="utf-8") == "новый сюжет"

        history = ["Игрок: " + ("слово " * 400)]
        (tmp / "Camp" / "history.json").write_text(json.dumps(history, ensure_ascii=False), encoding="utf-8")
        opened = client.post("/api/worlds/open", json={"name": "Camp"})
        assert opened.status_code == 200, opened.text
        updated = client.put("/api/settings", json={"context_size": 200, "max_tokens": 300, "summary_fill_percent": 80})
        assert updated.status_code == 200, updated.text
        state = client.get("/api/state").json()
        assert state["fill"]["summary_fill_percent"] == 80
        assert state["fill"]["ratio"] >= 0.8
        assert state["fill"]["color"] == "danger"

        rejected = client.put(
            "/api/settings",
            json={"prompt_overrides": {"ru": {"prompt.summary": "без полей"}, "en": {}}},
        )
        assert rejected.status_code == 400
    print("OK  файл мира пишется, полоса видит порог, битый промпт не сохраняется")


def test_history_opens_on_the_tail():
    import tempfile

    with tempfile.TemporaryDirectory() as folder:
        tmp = Path(folder)
        _use_tmp(tmp)
        client = TestClient(create_app())
        assert client.post("/api/worlds", json={"name": "Camp"}).status_code == 200
        history = [f"Игрок: реплика {index} " + ("слово " * 80) for index in range(30)]
        (tmp / "Camp" / "history.json").write_text(json.dumps(history, ensure_ascii=False), encoding="utf-8")
        opened = client.post("/api/worlds/open", json={"name": "Camp"})
        assert opened.status_code == 200, opened.text
        state = opened.json()
        assert state["history_total"] >= 30
        assert state["history_from"] > 0
        assert state["history"][0]["index"] == state["history_from"]
        assert state["history"][-1]["text"].startswith("реплика 29")
        assert len(state["history"]) < state["history_total"]

        earlier = client.get("/api/history", params={"before": state["history_from"]})
        assert earlier.status_code == 200, earlier.text
        page = earlier.json()
        assert page["history_from"] < state["history_from"]
        assert page["history"][-1]["index"] == state["history_from"] - 1
    print("OK  при открытии приходит хвост истории, более ранний кусок запрашивается отдельно")


def test_turn_and_stop():
    import tempfile

    with tempfile.TemporaryDirectory() as folder:
        tmp = Path(folder)
        _use_tmp(tmp)
        app = create_app()
        session = app.state.session
        client = TestClient(app)
        assert client.post("/api/worlds", json={"name": "Camp"}).status_code == 200

        def finish_read(_response, _key, on_delta=None):
            if on_delta:
                on_delta("Готово")
            return "Готово", False

        session._api_post = lambda payload, **kwargs: _Response()
        session._read_response = finish_read
        assert client.post("/api/turn", json={"text": "осмотреться"}).status_code == 200
        deadline = time.time() + 3
        text = ""
        while time.time() < deadline:
            state = client.get("/api/state").json()
            text = "\n".join(row["text"] for row in state["history"])
            if "Готово" in text and not state["status"]["busy"]:
                break
            time.sleep(0.05)
        assert "Готово" in text
        assert "осмотреться" in text

        hold = {"cancel": False}

        def blocking_read(_response, key, on_delta=None):
            while not session.is_cancelled(key):
                time.sleep(0.02)
            if on_delta:
                on_delta("обрыв")
            return "обрыв", True

        session._read_response = blocking_read
        assert client.post("/api/turn", json={"text": "ждать"}).status_code == 200
        time.sleep(0.1)
        stopped = client.post("/api/stop")
        assert stopped.status_code == 200
        assert stopped.json()["stopped"]
        deadline = time.time() + 3
        while time.time() < deadline and client.get("/api/state").json()["status"]["busy"]:
            time.sleep(0.05)
        assert client.get("/api/state").json()["status"]["busy"] is False
        hold["cancel"] = True
    print("OK  ход дописывает ответ, стоп отпускает генерацию")


def test_direction_turn():
    import tempfile

    with tempfile.TemporaryDirectory() as folder:
        tmp = Path(folder)
        _use_tmp(tmp)
        app = create_app()
        session = app.state.session
        client = TestClient(app)
        assert client.post("/api/worlds", json={"name": "Camp"}).status_code == 200
        seen = {}

        def finish_read(_response, _key, on_delta=None):
            if on_delta:
                on_delta("Сцена сдвинулась")
            return "Сцена сдвинулась", False

        def capture(payload, **kwargs):
            seen["user"] = payload["messages"][-1]["content"]
            return _Response()

        session._api_post = capture
        session._read_response = finish_read
        assert client.post("/api/turn", json={"direction": "герой находит ключ"}).status_code == 200
        deadline = time.time() + 3
        text = ""
        while time.time() < deadline:
            state = client.get("/api/state").json()
            text = "\n".join(row["text"] for row in state["history"])
            if "Сцена сдвинулась" in text and not state["status"]["busy"]:
                break
            time.sleep(0.05)
        assert "герой находит ключ" in text
        assert text.count("герой находит ключ") == 1
        assert "Сцена сдвинулась" in text
        assert "герой находит ключ" in seen["user"]
        assert "Автор задаёт направление" in seen["user"]
    print("OK  «Дальше?» записывает направление один раз и отдаёт его в ход")


def test_lan_setting_roundtrip():
    import tempfile

    with tempfile.TemporaryDirectory() as folder:
        tmp = Path(folder)
        _use_tmp(tmp)
        client = TestClient(create_app())
        assert client.post("/api/worlds", json={"name": "Camp"}).status_code == 200
        opened = client.get("/api/settings")
        assert opened.status_code == 200
        assert opened.json()["lan_access"] is True
        saved = client.put("/api/settings", json={"lan_access": False})
        assert saved.status_code == 200, saved.text
        assert saved.json()["lan_access"] is False
        again = client.get("/api/settings")
        assert again.json()["lan_access"] is False
        info = client.get("/api/network")
        assert info.status_code == 200, info.text
        body = info.json()
        assert body["local_url"] == "http://127.0.0.1:8765"
        assert body["listening"] == "127.0.0.1"
        assert isinstance(body["lan_urls"], list)
        assert isinstance(body["tailscale_urls"], list)
        assert again.json()["bind_mode"] == "local"
        hint = client.get("/api/strings").json()["dialog.lan_hint"]
        assert "Wi-Fi" in hint
    print("OK  доступ из локальной сети сохраняется и показывает адрес")


def test_world_export_and_import():
    import io
    import tempfile
    import zipfile

    with tempfile.TemporaryDirectory() as folder:
        tmp = Path(folder)
        _use_tmp(tmp)
        client = TestClient(create_app())
        assert client.post("/api/worlds", json={"name": "Camp"}).status_code == 200
        assert client.put("/api/files/plot_basics.txt", json={"content": "сюжет для переноса"}).status_code == 200
        (tmp / "Camp" / "settings.json").write_text('{"api_key":"nope"}', encoding="utf-8")
        (tmp / "Camp" / "notes.txt.bak").write_text("резерв", encoding="utf-8")

        exported = client.get("/api/worlds/Camp/export")
        assert exported.status_code == 200, exported.text
        assert exported.headers["content-type"].startswith("application/zip")
        with zipfile.ZipFile(io.BytesIO(exported.content)) as archive:
            names = set(archive.namelist())
            assert "plot_basics.txt" in names
            assert "history.json" in names
            assert "notes.txt.bak" in names
            assert "settings.json" not in names
            assert archive.read("plot_basics.txt").decode("utf-8") == "сюжет для переноса"

        nested = io.BytesIO()
        with zipfile.ZipFile(nested, "w") as archive:
            archive.writestr("Camp/plot_basics.txt", "сюжет из папки")
            archive.writestr("Camp/history.json", json.dumps(["Игрок: привет"], ensure_ascii=False))
            archive.writestr("Camp/__MACOSX/skip.txt", "мусор")
            archive.writestr("Camp/settings.json", '{"api_key":"nope"}')
        brought = client.post(
            "/api/worlds/import?name=Camp%202",
            content=nested.getvalue(),
            headers={"Content-Type": "application/zip"},
        )
        assert brought.status_code == 200, brought.text
        assert brought.json()["name"] == "Camp 2"
        assert client.get("/api/state").json()["world"] == "Camp 2"
        assert (tmp / "Camp 2" / "plot_basics.txt").read_text(encoding="utf-8") == "сюжет из папки"
        assert not (tmp / "Camp 2" / "settings.json").exists()

        again = client.post(
            "/api/worlds/import?name=Camp%202",
            content=exported.content,
            headers={"Content-Type": "application/zip"},
        )
        assert again.status_code == 409

        slipped = io.BytesIO()
        with zipfile.ZipFile(slipped, "w") as archive:
            archive.writestr("../settings.json", "secret")
            archive.writestr("history.json", "[]")
        rejected = client.post(
            "/api/worlds/import?name=Escape",
            content=slipped.getvalue(),
            headers={"Content-Type": "application/zip"},
        )
        assert rejected.status_code == 400
        assert not (tmp / "Escape").exists()
        if (tmp / "settings.json").exists():
            assert "secret" not in (tmp / "settings.json").read_text(encoding="utf-8")
    print("OK  мир выгружается в zip и поднимается из архива без настроек и чужих путей")


def test_player_line_is_visible_before_the_reply():
    import tempfile
    import threading

    with tempfile.TemporaryDirectory() as folder:
        tmp = Path(folder)
        _use_tmp(tmp)
        app = create_app()
        session = app.state.session
        client = TestClient(app)
        assert client.post("/api/worlds", json={"name": "Camp"}).status_code == 200
        release = threading.Event()

        def blocking_read(_response, key, on_delta=None):
            while not release.is_set() and not session.is_cancelled(key):
                time.sleep(0.02)
            return "Готово", False

        session._api_post = lambda payload, **kwargs: _Response()
        session._read_response = blocking_read
        assert client.post("/api/turn", json={"text": "осмотреться"}).status_code == 200
        state = client.get("/api/state").json()
        player = [row for row in state["history"] if row["kind"] == "player"]
        assert player and player[-1]["text"] == "осмотреться"
        assert all(row["kind"] != "dm" for row in state["history"])
        assert state["status"]["busy"] is True
        release.set()
        deadline = time.time() + 3
        while time.time() < deadline and client.get("/api/state").json()["status"]["busy"]:
            time.sleep(0.05)
        done = client.get("/api/state").json()
        assert done["status"]["busy"] is False
        assert sum(1 for row in done["history"] if row["text"] == "осмотреться") == 1
        assert any(row["kind"] == "dm" and "Готово" in row["text"] for row in done["history"])
    print("OK  реплика игрока есть в ленте до окончания ответа и не дублируется")


def test_reply_tokens_follow_model_usage():
    import tempfile

    from dungeon.api_stream import _iter_response_deltas
    from dungeon.tokens import count_tokens, reply_tokens

    narration = "Темный коридор тянется дальше. " * 40
    assert count_tokens(narration) > 40
    assert reply_tokens({"completion_tokens": 19}, narration) == 19
    assert reply_tokens({"completion_tokens": True}, narration) == count_tokens(narration)
    assert reply_tokens(None, narration) == count_tokens(narration)

    class _Chunks:
        def __init__(self, chunks):
            self._chunks = chunks

        def iter_content(self, chunk_size=None):
            yield from self._chunks

    usage = {}
    pieces = "".join(
        _iter_response_deltas(
            _Chunks(
                [
                    'data: {"choices":[{"delta":{"content":"Раз"}}]}\n'.encode(),
                    'data: {"choices":[],"usage":{"prompt_tokens":8,"completion_tokens":19,"total_tokens":27}}\n'.encode(),
                    b"data: [DONE]\n",
                ]
            ),
            usage,
        )
    )
    assert pieces == "Раз"
    assert usage["completion_tokens"] == 19

    plain = {}
    body = '{"choices":[{"message":{"content":"Два"}}],"usage":{"completion_tokens":2}}'.encode()
    assert "".join(_iter_response_deltas(_Chunks([body]), plain)) == "Два"
    assert plain["completion_tokens"] == 2

    with tempfile.TemporaryDirectory() as folder:
        tmp = Path(folder)
        _use_tmp(tmp)
        app = create_app()
        session = app.state.session
        client = TestClient(app)
        assert client.post("/api/worlds", json={"name": "Camp"}).status_code == 200
        assert client.put(
            "/api/settings",
            json={"summary_enabled": False, "memory_enabled": False},
        ).status_code == 200
        seen = {}

        def finish_read(_response, _key, on_delta=None):
            session._last_api_usage = {"prompt_tokens": 8, "completion_tokens": 19}
            if on_delta:
                on_delta(narration)
            return narration, False

        def capture(payload, **kwargs):
            seen["stream_options"] = payload.get("stream_options")
            return _Response()

        session._api_post = capture
        session._read_response = finish_read
        assert client.post("/api/turn", json={"text": "осмотреться"}).status_code == 200
        deadline = time.time() + 3
        notice = ""
        while time.time() < deadline:
            state = client.get("/api/state").json()
            notice = (state["notices"] or [""])[-1]
            if "Ответ: 19" in notice and not state["status"]["busy"]:
                break
            time.sleep(0.05)
        assert "Ответ: 19" in notice
        assert f"Ответ: {count_tokens(narration)}" not in notice
        assert seen["stream_options"] == {"include_usage": True}
    print("OK  строка «Ответ» берёт completion_tokens модели, а не локальную оценку")


def test_resume_sees_partial_reply_and_finished_jobs():
    import tempfile

    from dungeon.i18n import DM_PREFIX

    with tempfile.TemporaryDirectory() as folder:
        tmp = Path(folder)
        _use_tmp(tmp)
        app = create_app()
        session = app.state.session
        client = TestClient(app)
        assert client.post("/api/worlds", json={"name": "Camp"}).status_code == 200
        session.processing = True
        session.start_dm_stream()
        session.append_to_dm_stream("Первая ")
        session.append_to_dm_stream("часть")
        live = client.get("/api/state").json()
        assert live["streaming"] is True
        assert live["draft"] == "Первая часть"
        assert live["status"]["busy"] is True
        assert live["status"]["text"] == "Генерация..."
        assert live["rev"] >= 1
        session.history.append(f"{DM_PREFIX} Первая часть")
        session.finalize_dm_stream("Первая часть")
        session.processing = False
        session.summary_indexing = True
        summary = client.get("/api/state").json()
        assert summary["draft"] == ""
        assert summary["streaming"] is False
        assert summary["status"]["text"] == "Суммаризация..."
        assert any(row["kind"] == "dm" and row["text"] == "Первая часть" for row in summary["history"])
        session.summary_indexing = False
        session.memory_indexing = True
        assert client.get("/api/state").json()["status"]["text"] == "Индексация памяти..."
        session.memory_indexing = False
        done = client.get("/api/state").json()
        assert done["status"]["busy"] is False
        assert done["status"]["text"] == "Готов"
    print("OK  снимок состояния хранит недописанный ответ и статус фона")


def test_state_is_not_cached():
    import tempfile

    with tempfile.TemporaryDirectory() as folder:
        tmp = Path(folder)
        _use_tmp(tmp)
        client = TestClient(create_app())
        assert client.post("/api/worlds", json={"name": "Camp"}).status_code == 200
        response = client.get("/api/state")
        assert response.status_code == 200
        cache = response.headers.get("cache-control", "")
        assert "no-store" in cache
        page = client.get("/")
        assert "no-store" in page.headers.get("cache-control", "")
        assert "app.js?v=10" in page.text
        assert 'rel="icon"' in page.text
        icon = client.get("/favicon.ico")
        assert icon.status_code == 200
        assert icon.content[:4] == b"\x00\x00\x01\x00"
    print("OK  страница и состояние не кэшируются браузером телефона")


def test_context_scale_follows_model_prompt():
    from dungeon.tokens import (
        count_tokens,
        model_token_scale,
        observe_model_prompt,
        prompt_token_count,
        raw_count_tokens,
        set_model_token_scale,
    )

    text = "Темный коридор тянется дальше. " * 80
    set_model_token_scale(1.0)
    try:
        raw = raw_count_tokens(text)
        assert count_tokens(text) == raw
        assert observe_model_prompt(500, {"prompt_tokens": 100}) is False
        assert model_token_scale() == 1.0
        assert observe_model_prompt(16000, {"prompt_tokens": 12000}) is True
        scale = model_token_scale()
        assert 0.75 <= scale <= 0.85
        assert count_tokens(text) < raw
        assert prompt_token_count({"prompt_tokens": 12000}, 16000) == 12000
        assert observe_model_prompt(16000, {"prompt_tokens": True}) is False
    finally:
        set_model_token_scale(1.0)
    print("OK  шкала контекста сжимает локальный счёт до prompt_tokens модели")


def test_first_turn_learns_scale_before_packing():
    """Первый ход сверяет счётчик до нарезки истории, иначе в модель уходит урезанный промпт."""
    import tempfile

    from dungeon.tokens import (
        model_token_scale,
        raw_count_tokens,
        set_model_token_scale,
    )

    class _UsageResponse(_Response):
        def __init__(self, usage):
            self._usage = usage

        def json(self):
            return {"usage": self._usage}

    set_model_token_scale(1.0)
    try:
        with tempfile.TemporaryDirectory() as folder:
            tmp = Path(folder)
            _use_tmp(tmp)
            app = create_app()
            session = app.state.session
            client = TestClient(app)
            assert client.post("/api/worlds", json={"name": "Camp"}).status_code == 200
            piece = "слово " * 80
            one = raw_count_tokens(f"Игрок: реплика 0 {piece}") + 1
            total = int(26000 / max(one, 1)) + 5
            history = [f"Игрок: реплика {index} {piece}" for index in range(total)]
            (tmp / "Camp" / "history.json").write_text(json.dumps(history, ensure_ascii=False), encoding="utf-8")
            assert client.post("/api/worlds/open", json={"name": "Camp"}).status_code == 200
            assert client.put(
                "/api/settings",
                json={
                    "context_size": 16384,
                    "max_tokens": 400,
                    "summary_enabled": False,
                    "memory_enabled": False,
                },
            ).status_code == 200
            calls = []

            def finish_read(_response, _key, on_delta=None):
                if on_delta:
                    on_delta("Готово")
                return "Готово", False

            def post(payload, **kwargs):
                calls.append(payload)
                if payload.get("stream") is False and payload.get("max_tokens") == 1:
                    content = payload["messages"][0]["content"]
                    reported = max(1, int(raw_count_tokens(content) * 0.7))
                    return _UsageResponse({"prompt_tokens": reported, "completion_tokens": 1})
                return _Response()

            session._api_post = post
            session._read_response = finish_read
            assert client.post("/api/turn", json={"text": "осмотреться"}).status_code == 200
            deadline = time.time() + 4
            while time.time() < deadline and client.get("/api/state").json()["status"]["busy"]:
                time.sleep(0.05)
            turn = next(payload for payload in calls if payload.get("stream"))
            sent = raw_count_tokens(turn["messages"][0]["content"]) + raw_count_tokens(turn["messages"][1]["content"])
            assert model_token_scale() < 0.85
            # Без сверки локальный потолок около 16к. После неё в промпт входит больше текста.
            assert sent > 17000
    finally:
        set_model_token_scale(1.0)
    print("OK  первый ход узнаёт масштаб до нарезки истории")


def test_summary_learns_scale_before_packing():
    """Суммаризация сверяет счётчик до нарезки, иначе в модель уходит около 10к из 16к."""
    import tempfile

    from dungeon.tokens import model_token_scale, raw_count_tokens, set_model_token_scale

    class _UsageResponse(_Response):
        def __init__(self, usage):
            self._usage = usage

        def json(self):
            return {"usage": self._usage}

    set_model_token_scale(1.0)
    try:
        with tempfile.TemporaryDirectory() as folder:
            tmp = Path(folder)
            _use_tmp(tmp)
            app = create_app()
            session = app.state.session
            client = TestClient(app)
            assert client.post("/api/worlds", json={"name": "Camp"}).status_code == 200
            piece = "слово " * 80
            one = raw_count_tokens(f"Игрок: реплика 0 {piece}") + 1
            total = int(26000 / max(one, 1)) + 5
            history = [f"Игрок: реплика {index} {piece}" for index in range(total)]
            (tmp / "Camp" / "history.json").write_text(json.dumps(history, ensure_ascii=False), encoding="utf-8")
            assert client.post("/api/worlds/open", json={"name": "Camp"}).status_code == 200
            assert client.put(
                "/api/settings",
                json={"context_size": 16384, "memory_enabled": False},
            ).status_code == 200
            calls = []

            def finish_read(_response, _key, on_delta=None):
                return "Краткая хроника", False

            def post(payload, **kwargs):
                calls.append(payload)
                if payload.get("stream") is False and payload.get("max_tokens") == 1:
                    content = payload["messages"][0]["content"]
                    reported = max(1, int(raw_count_tokens(content) * 0.7))
                    return _UsageResponse({"prompt_tokens": reported, "completion_tokens": 1})
                return _Response()

            session._api_post = post
            session._read_response = finish_read
            assert client.post("/api/summary").status_code == 200
            deadline = time.time() + 4
            while time.time() < deadline and client.get("/api/state").json()["status"]["busy"]:
                time.sleep(0.05)
            summary = next(payload for payload in calls if payload.get("max_tokens") == 1000)
            sent = raw_count_tokens(summary["messages"][0]["content"])
            assert model_token_scale() < 0.85
            assert sent > 17000
    finally:
        set_model_token_scale(1.0)
    print("OK  суммаризация узнаёт масштаб до нарезки истории")


def test_bind_modes():
    from web.netbind import host_for_mode, is_tailscale_ip, saved_mode, share_urls, split_addresses

    assert is_tailscale_ip("100.96.1.2")
    assert is_tailscale_ip("100.64.0.1")
    assert is_tailscale_ip("100.127.255.255")
    assert not is_tailscale_ip("100.63.1.1")
    assert not is_tailscale_ip("100.128.0.1")
    assert not is_tailscale_ip("192.168.0.9")
    assert host_for_mode("local") == "127.0.0.1"
    assert host_for_mode("lan") == "0.0.0.0"
    assert host_for_mode("tailscale") == "0.0.0.0"
    assert saved_mode({}) == "lan"
    assert saved_mode({"lan_access": False}) == "local"
    assert saved_mode({"bind_mode": "tailscale", "lan_access": False}) == "tailscale"
    lan, tailscale = split_addresses(["127.0.0.1", "192.168.0.9", "100.64.0.8", "169.254.1.1"])
    assert lan == ["192.168.0.9"]
    assert tailscale == ["100.64.0.8"]
    urls = share_urls("tailscale", 8765, {"lan": ["192.168.0.9"], "tailscale": ["100.64.0.8"]})
    assert urls["local"] == "http://127.0.0.1:8765"
    assert urls["share"] == ["http://100.64.0.8:8765"]
    print("OK  режим запуска отличает Wi-Fi от Tailscale")


def test_preset_switch_updates_connection():
    import tempfile

    with tempfile.TemporaryDirectory() as folder:
        tmp = Path(folder)
        _use_tmp(tmp)
        app = create_app()

        def _offline(*_args, **_kwargs):
            raise OSError("offline")

        app.state.session._api_post = _offline
        client = TestClient(app)
        saved = client.put(
            "/api/settings",
            json={
                "api_url": "http://localhost:1234/v1/chat/completions",
                "api_key": "",
                "model": "gemma",
                "active_api_preset": "Local",
                "api_presets": [
                    {
                        "name": "Local",
                        "api_url": "http://localhost:1234/v1/chat/completions",
                        "api_key": "",
                        "model": "gemma",
                    },
                    {
                        "name": "Remote",
                        "api_url": "http://example.test/v1/chat/completions",
                        "api_key": "secret",
                        "model": "other",
                    },
                ],
            },
        )
        assert saved.status_code == 200, saved.text
        state = client.get("/api/state").json()
        assert state["presets"]["active"] == "Local"
        assert [item["name"] for item in state["presets"]["items"]] == ["Local", "Remote"]
        assert "api_key" not in state["presets"]["items"][1]
        switched = client.post("/api/presets/activate", json={"name": "Remote"})
        assert switched.status_code == 200, switched.text
        body = switched.json()
        assert body["active"] == "Remote"
        assert "secret" not in json.dumps(body)
        settings = client.get("/api/settings").json()
        assert settings["model"] == "other"
        assert settings["api_url"] == "http://example.test/v1/chat/completions"
        assert settings["api_key"] == "secret"
        assert settings["active_api_preset"] == "Remote"
        missing = client.post("/api/presets/activate", json={"name": "Nope"})
        assert missing.status_code == 404
    print("OK  список моделей переключает сохранённую конфигурацию")


def test_model_switch_keeps_summary_bar_scaled():
    """Смена модели не рисует шкалу сырым счётчиком и помнит уже измеренный масштаб."""
    import tempfile

    from dungeon.tokens import calibration_sample, raw_count_tokens, set_model_token_scale

    class _UsageResponse(_Response):
        def __init__(self, usage):
            self._usage = usage

        def json(self):
            return {"usage": self._usage}

    set_model_token_scale(1.0)
    try:
        with tempfile.TemporaryDirectory() as folder:
            tmp = Path(folder)
            _use_tmp(tmp)
            app = create_app()
            session = app.state.session
            client = TestClient(app)
            assert client.post("/api/worlds", json={"name": "Camp"}).status_code == 200
            assert client.post("/api/worlds/open", json={"name": "Camp"}).status_code == 200
            session.history = ["Игрок: " + ("тёмный коридор тянется дальше. " * 40)]
            session.covered_count = 0
            session.model = "alpha"
            set_model_token_scale(0.75)
            session._remember_token_scale()
            saved = client.put(
                "/api/settings",
                json={
                    "model": "alpha",
                    "summary_enabled": False,
                    "memory_enabled": False,
                    "active_api_preset": "Alpha",
                    "api_presets": [
                        {
                            "name": "Alpha",
                            "api_url": "http://127.0.0.1:9/v1/chat/completions",
                            "api_key": "",
                            "model": "alpha",
                        },
                        {
                            "name": "Beta",
                            "api_url": "http://127.0.0.1:9/v1/chat/completions",
                            "api_key": "",
                            "model": "beta",
                        },
                    ],
                },
            )
            assert saved.status_code == 200, saved.text
            used_a, budget_a, _ratio_a = session.context_fill_state()
            set_model_token_scale(1.0)
            used_raw, budget_raw, _ratio_raw = session.context_fill_state()
            set_model_token_scale(0.75)
            session._remember_token_scale()
            assert used_a < used_raw
            assert budget_a > budget_raw
            sample_raw = raw_count_tokens(calibration_sample())
            calls = []

            def post(payload, **_kwargs):
                calls.append(payload.get("model"))
                return _UsageResponse({"prompt_tokens": int(sample_raw * 0.8)})

            session._api_post = post
            switched = client.post("/api/presets/activate", json={"name": "Beta"})
            assert switched.status_code == 200, switched.text
            assert calls == ["beta"]
            fill = client.get("/api/state").json()["fill"]
            assert fill["used"] < used_raw
            assert fill["budget"] > budget_raw
            back = client.post("/api/presets/activate", json={"name": "Alpha"})
            assert back.status_code == 200, back.text
            assert calls == ["beta"]
            restored = client.get("/api/state").json()["fill"]
            assert restored["used"] == used_a
            assert restored["budget"] == budget_a
    finally:
        set_model_token_scale(1.0)
    print("OK  смена модели не раздувает шкалу до сырого счёта")


def test_finished_reply_is_settled_before_processing_ends():
    """Финал хода уже содержит обе реплики и закрытый черновик, пока processing ещё истинен."""
    import tempfile

    from dungeon.i18n import DM_PREFIX, PLAYER_PREFIX

    with tempfile.TemporaryDirectory() as folder:
        tmp = Path(folder)
        _use_tmp(tmp)
        app = create_app()
        session = app.state.session
        client = TestClient(app)
        assert client.post("/api/worlds", json={"name": "Camp"}).status_code == 200
        session.processing = True
        session.history.append(f"{PLAYER_PREFIX} осмотреться")
        session.start_dm_stream()
        session.append_to_dm_stream("Тропа ")
        session.history.append(f"{DM_PREFIX} Тропа вывела к реке")
        session.finalize_dm_stream("Тропа вывела к реке")
        assert session.processing is True
        done = client.get("/api/state").json()
        assert done["streaming"] is False
        assert done["draft"] == ""
        assert any(row["kind"] == "player" and row["text"] == "осмотреться" for row in done["history"])
        assert any(row["kind"] == "dm" and row["text"] == "Тропа вывела к реке" for row in done["history"])
        assert done["fill"]["label"]
    print("OK  финал хода закрывает черновик до конца обработки")


def test_world_language_marks_and_english_token_scale():
    """Русский и английский миры помечены отдельно, и у английского свой масштаб."""
    import re
    import tempfile

    import dungeon.tokens as tokens
    from dungeon.storage import read_world_language
    from dungeon.tokens import calibration_sample, model_token_scale, raw_count_tokens, set_model_token_scale

    english = calibration_sample("en")
    assert raw_count_tokens(english) >= 1000
    assert raw_count_tokens(calibration_sample("ru")) >= 1000
    assert not re.search(r"[а-яёА-ЯЁ]", english)

    class _CharEncoder:
        def encode(self, text, disallowed_special=()):
            return [1] * max(1, len(text))

    tokens._TOKENIZER = _CharEncoder()
    tokens._TOKENIZER_LOADED = True
    tokens._TOKENIZER_IS_TARGET = False
    try:
        latin = "The road led across a dark field toward a distant fire. "
        cyrillic = "Ночь была тихой, и дорога вела через тёмное поле. "
        assert tokens.raw_count_tokens(latin) == len(latin)
        assert tokens.raw_count_tokens(cyrillic) < len(cyrillic)
    finally:
        tokens._TOKENIZER = None
        tokens._TOKENIZER_LOADED = False
        tokens._TOKENIZER_IS_TARGET = False

    set_model_token_scale(1.0)
    try:
        with tempfile.TemporaryDirectory() as folder:
            tmp = Path(folder)
            _use_tmp(tmp)
            app = create_app()
            session = app.state.session
            client = TestClient(app)
            assert client.post("/api/worlds", json={"name": "Camp"}).status_code == 200
            assert (tmp / "Camp" / "language.txt").read_text(encoding="utf-8").strip() == "ru"
            shore = tmp / "Shore"
            shore.mkdir()
            (shore / "introduction.txt").write_text("A quiet harbor at dawn.", encoding="utf-8")
            assert read_world_language(shore) == "en"
            session.model = "alpha"
            set_model_token_scale(0.75)
            session._remember_token_scale()
            calls = []

            class _UsageResponse(_Response):
                def __init__(self, usage):
                    self._usage = usage

                def json(self):
                    return {"usage": self._usage}

            def post(payload, **_kwargs):
                text = payload["messages"][0]["content"]
                calls.append(text)
                assert "Ночь" not in text
                raw = raw_count_tokens(text)
                return _UsageResponse({"prompt_tokens": int(raw * 0.9)})

            session._api_post = post
            session.language = "en"
            assert client.post("/api/worlds", json={"name": "Harbor"}).status_code == 200
            assert (tmp / "Harbor" / "language.txt").read_text(encoding="utf-8").strip() == "en"
            assert len(calls) == 1
            assert calls[0].startswith("The night was quiet")
            assert model_token_scale() > 0.9
            assert abs(model_token_scale() - 0.75) > 0.05
            assert client.post("/api/worlds/open", json={"name": "Camp"}).status_code == 200
            assert len(calls) == 1
            assert abs(model_token_scale() - 0.75) < 0.001
            worlds = client.get("/api/worlds").json()["worlds"]
            assert [item["name"] for item in worlds] == ["Camp", "Harbor", "Shore"]
            assert [item["language"] for item in worlds] == ["ru", "en", "en"]
    finally:
        set_model_token_scale(1.0)
    print("OK  миры помечены языком, английский масштаб не берётся из русской пробы")


def test_prompt_limits_and_scene_look():
    import tempfile

    from dungeon.config import apply_image_look
    from dungeon.i18n import t

    styled = apply_image_look("a knight on a road --ar 16:9 --v 7", "anime")
    assert styled.index("anime style") < styled.index("--ar")
    assert apply_image_look(styled, "anime") == styled
    assert "anime style, cel shading" in t("en", "prompt.scene_look.anime")
    assert "photorealistic, realistic skin" in t("ru", "prompt.scene_look.realism")

    with tempfile.TemporaryDirectory() as folder:
        tmp = Path(folder)
        _use_tmp(tmp)
        app = create_app()
        session = app.state.session
        client = TestClient(app)
        view = client.get("/api/settings").json()
        assert view["response_limits"]["prompt.memory_index"] == 350
        assert view["response_limits"]["prompt.scene_image"] == 700
        assert view["response_limits"]["prompt.summary"] == 1000
        assert view["response_limits"]["prompt.card_desc_gen"] == 400
        prompts = [item for group in view["prompts"] for item in group["prompts"]]
        assert next(item for item in prompts if item["key"] == "prompt.memory_index")["limit"] == 350
        assert "limit" not in next(item for item in prompts if item["key"] == "prompt.continue")

        updated = client.put(
            "/api/settings",
            json={"response_limits": {"prompt.memory_index": 120, "prompt.scene_image": 900, "prompt.summary": "нет"}},
        )
        assert updated.status_code == 200, updated.text
        limits = updated.json()["response_limits"]
        assert limits["prompt.memory_index"] == 120
        assert limits["prompt.scene_image"] == 900
        assert limits["prompt.summary"] == 1000
        assert client.put("/api/settings", json={"response_limits": {"prompt.memory_index": 0}}).json()["response_limits"]["prompt.memory_index"] == 1

        assert client.post("/api/worlds", json={"name": "Camp"}).status_code == 200
        history = ["Игрок: осмотреться", "Мастер: Тропа вывела к реке."]
        (tmp / "Camp" / "history.json").write_text(json.dumps(history, ensure_ascii=False), encoding="utf-8")
        assert client.post("/api/worlds/open", json={"name": "Camp"}).status_code == 200
        assert session._summary_history_budget()[2] == 1000
        options = client.put("/api/scene/options", json={"image_prompt_style": "flux", "image_look": "anime"})
        assert options.status_code == 200, options.text
        assert options.json()["image_prompt_style"] == "flux"
        assert options.json()["image_look"] == "anime"
        calls = []

        def post(payload, **_kwargs):
            calls.append(payload)
            return _Response()

        def finish_read(_response, _key, on_delta=None):
            return '{"prompt": "a river path --ar 16:9", "negative_prompt": "blurry"}', False

        session._api_post = post
        session._read_response = finish_read
        session.response_limits["prompt.scene_image"] = 900
        assert client.post(
            "/api/scene",
            json={"image_prompt_style": "midjourney", "image_look": "realism"},
        ).status_code == 200
        deadline = time.time() + 3
        scene = None
        while time.time() < deadline:
            scene = client.get("/api/scene").json()["scene"]
            if scene and scene.get("prompt"):
                break
            time.sleep(0.05)
        assert calls, "промпт сцены не ушёл в модель"
        sent = calls[-1]["messages"][0]["content"]
        assert calls[-1]["max_tokens"] == 900
        assert "СТИЛЬ ИЗОБРАЖЕНИЯ: реализм" in sent
        assert "photorealistic, realistic skin" in sent
        assert scene["style"] == "midjourney"
        assert scene["look"] == "realism"
        assert "photorealistic, realistic skin" in scene["prompt"]
        assert scene["prompt"].index("photorealistic") < scene["prompt"].index("--ar")
        assert scene["negative"] == "blurry"
        stored = json.loads((tmp / "settings.json").read_text(encoding="utf-8"))
        assert stored["image_look"] == "realism"
        assert stored["image_prompt_style"] == "midjourney"
        assert stored["response_limits"]["prompt.scene_image"] == 900
    print("OK  лимиты промптов меняются, стиль дописывается в промпт сцены")


if __name__ == "__main__":
    test_file_save_and_summary_threshold()
    test_history_opens_on_the_tail()
    test_turn_and_stop()
    test_direction_turn()
    test_player_line_is_visible_before_the_reply()
    test_reply_tokens_follow_model_usage()
    test_resume_sees_partial_reply_and_finished_jobs()
    test_state_is_not_cached()
    test_context_scale_follows_model_prompt()
    test_first_turn_learns_scale_before_packing()
    test_summary_learns_scale_before_packing()
    test_lan_setting_roundtrip()
    test_world_export_and_import()
    test_bind_modes()
    test_preset_switch_updates_connection()
    test_model_switch_keeps_summary_bar_scaled()
    test_finished_reply_is_settled_before_processing_ends()
    test_world_language_marks_and_english_token_scale()
    test_prompt_limits_and_scene_look()
    print("ALL WEB TESTS PASSED")
