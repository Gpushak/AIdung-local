"""Проверка пакетной выдачи дельт и индикатора контекста."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dungeon.ai_engine import DeltaBatcher  # noqa: E402
from dungeon.tokens import format_token_count  # noqa: E402
from tkhelpers import close_tk_window  # noqa: E402


def test_batcher_coalesces_into_few_flushes():
    """Много дельт подряд должны попасть в интерфейс пачками, а не по одной."""
    flushes = []
    batcher = DeltaBatcher(flushes.append)

    for i in range(500):
        batcher.add(f"токен{i} ")
        # Симулируем быстрый поток: между дельтами почти нет времени
    batcher.flush_now()

    assert len(flushes) <= 3, f"слишком много выдач: {len(flushes)}"
    total = "".join(flushes)
    assert total.count("токен") == 500, "часть текста потерялась"
    print(f"OK  500 дельт схлопнулись в {len(flushes)} выдач вместо 500")


def test_batcher_preserves_order():
    flushes = []
    batcher = DeltaBatcher(flushes.append)
    for ch in "abcdefghij":
        batcher.add(ch)
        time.sleep(0.001)
    batcher.flush_now()
    assert "".join(flushes) == "abcdefghij", flushes
    print("OK  порядок дельт не нарушается")


def test_batcher_flushes_slowly_arriving_deltas():
    """Первая дельта уходит сразу, следующая — с паузой тоже сразу."""
    flushes = []
    batcher = DeltaBatcher(flushes.append)
    batcher.add("a")
    # Первая дельта показывается без задержки — так текст появляется мгновенно
    assert flushes == ["a"], flushes
    # Пауза длиннее интервала — следующая дельта тоже не ждёт
    time.sleep(DeltaBatcher.FLUSH_INTERVAL + 0.02)
    batcher.add("b")
    assert flushes == ["a", "b"], flushes
    batcher.flush_now()
    assert "".join(flushes) == "ab"
    print("OK  редкая дельта не ждёт следующую")


def test_batcher_no_flush_when_empty():
    flushes = []
    batcher = DeltaBatcher(flushes.append)
    batcher.flush_now()
    assert flushes == []
    print("OK  пустой буфер не вызывает интерфейс")


def test_format_token_count():
    assert format_token_count(0) == "0"
    assert format_token_count(843) == "843"
    assert format_token_count(999) == "999"
    assert format_token_count(1000) == "1k"
    assert format_token_count(16384) == "16.4k"
    assert format_token_count(131072) == "131.1k"
    print("OK  числа токенов форматируются компактно")


def test_context_indicator_updates():
    import customtkinter as ctk

    from dungeon.app import DungeonApp

    ctk.set_appearance_mode("Dark")
    root = ctk.CTk()
    root.withdraw()
    app = DungeonApp(root)
    app.context_size = 1000

    app.update_context_indicator(500)
    assert app.context_tokens == 500
    assert "500" in app.context_label.cget("text")

    # Переполнение не должно ломать полоску
    app.update_context_indicator(5000)
    assert app.context_tokens == 5000
    assert app.context_label.cget("text")  # текст есть

    # Сброс
    app.update_context_indicator(0)
    assert app.context_tokens == 0

    close_tk_window(app.root)
    print("OK  индикатор контекста обновляется и не ломается на переполнении")


def test_stream_is_read_incrementally():
    """Поток должен приходить по частям, а не одним куском в конце.

    С chunk_size=None urllib3 копит данные в буфер до конца ответа, и весь
    «потоковый» режим превращался в одноразовую вставку в самом конце.
    """
    import json as _json
    import time as _time

    from dungeon.ai_engine import STREAM_CHUNK_SIZE, _iter_response_deltas

    frames = [
        ("data: " + _json.dumps({"choices": [{"delta": {"content": f"часть{i} "}}]}) + "\n\n").encode("utf-8")
        for i in range(20)
    ]

    class SlowResponse:
        """Отдаёт по одному фрейму с задержкой, как живой сервер."""

        def __init__(self):
            self.sent = 0

        def iter_content(self, chunk_size=None):
            assert chunk_size is not None, "chunk_size=None копит поток до конца"
            for frame in frames:
                for i in range(0, len(frame), chunk_size):
                    yield frame[i : i + chunk_size]
                self.sent += 1
                _time.sleep(0.01)

        def close(self):
            pass

    response = SlowResponse()
    first = None
    started = _time.monotonic()
    for delta in _iter_response_deltas(response):
        if first is None:
            first = _time.monotonic() - started
        if response.sent >= 3:
            break

    assert STREAM_CHUNK_SIZE is not None and STREAM_CHUNK_SIZE > 1
    # Первая порция должна прийти заметно раньше конца потока
    assert first is not None, "поток не начал отдавать данные"
    assert first < 0.5, f"первые данные пришли слишком поздно: {first:.2f}s"
    print("OK  поток читается инкрементально, а не копится до конца")


def test_reads_data_in_chunks_of_configured_size():
    """Парсер обязан запрашивать у HTTP-клиента порции, а не весь ответ целиком."""
    import json as _json

    from dungeon.ai_engine import STREAM_CHUNK_SIZE, _iter_response_deltas

    seen = []

    class R:
        def iter_content(self, chunk_size=None):
            seen.append(chunk_size)
            frame = ("data: " + _json.dumps({"choices": [{"delta": {"content": "x"}}]}) + "\n\n").encode("utf-8")
            yield frame

        def close(self):
            pass

    list(_iter_response_deltas(R()))
    assert seen == [STREAM_CHUNK_SIZE], seen
    assert seen[0] is not None, "chunk_size=None отключает потоковую выдачу"
    print("OK  парсер запрашивает порции заданного размера")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("ALL STREAM/CONTEXT TESTS PASSED")
