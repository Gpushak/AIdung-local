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


if __name__ == "__main__":
    test_file_save_and_summary_threshold()
    test_history_opens_on_the_tail()
    test_turn_and_stop()
    test_direction_turn()
    test_lan_setting_roundtrip()
    test_world_export_and_import()
    test_bind_modes()
    print("ALL WEB TESTS PASSED")
