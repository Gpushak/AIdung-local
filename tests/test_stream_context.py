"""Проверка пакетной выдачи дельт и индикатора контекста."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dungeon.ai_engine import DeltaBatcher  # noqa: E402
from dungeon.config import COLORS  # noqa: E402
from dungeon.i18n import INTRO_PREFIX  # noqa: E402
from dungeon.storage import (  # noqa: E402
    clamp_summary_cursor,
    clamp_summary_fill_percent,
    default_summary_cursor,
    read_summary_cursor,
    save_summary_cursor,
)
from dungeon.tokens import (  # noqa: E402
    HISTORY_BUDGET_FLOOR,
    count_tokens,
    format_token_count,
    history_window_budget,
    summary_due,
    take_unsummarized_prefix,
    unsummarized_token_count,
)
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


def test_history_budget_matches_turn_window():
    """Бюджет истории — окно минус ответ, статику и запас, но не ниже пола."""
    assert history_window_budget(16384, 300, 1000, 0) == 16384 - 300 - 1000 - 64
    # Ход дополнительно вычитает текст игрока
    assert history_window_budget(16384, 300, 1000, 40) == 16384 - 300 - 1000 - 40 - 64
    assert history_window_budget(500, 300, 1000, 0) == 300
    raw = history_window_budget(500, 300, 1000, 0, apply_floor=False)
    assert raw < HISTORY_BUDGET_FLOOR
    assert raw == 500 - 300 - 1000 - 64
    print("OK  бюджет истории совпадает со сборкой хода")


def test_summary_takes_oldest_uncovered_prefix():
    history = ["раз", "два", "три", "четыре"]
    costs = [count_tokens(msg) + 1 for msg in history]
    whole = sum(costs)
    chunk, nxt, skipped = take_unsummarized_prefix(history, 0, whole)
    assert chunk == history and nxt == 4 and skipped == 0

    first_two = costs[0] + costs[1]
    chunk, nxt, skipped = take_unsummarized_prefix(history, 0, first_two)
    assert chunk == ["раз", "два"] and nxt == 2 and skipped == 0

    chunk, nxt, skipped = take_unsummarized_prefix(history, 2, costs[2])
    assert chunk == ["три"] and nxt == 3 and skipped == 0

    huge = "слово " * 400
    mixed = [huge, "коротко", "ещё"]
    budget = count_tokens("коротко") + 1
    chunk, nxt, skipped = take_unsummarized_prefix(mixed, 0, budget)
    assert skipped == 1 and chunk == ["коротко"] and nxt == 2

    chunk, nxt, skipped = take_unsummarized_prefix(history, 1, 0)
    assert chunk == [] and nxt == 1 and skipped == 0
    print("OK  суммаризация берёт старый непокрытый кусок и не отмечает хвост")


def test_unsummarized_tokens_start_at_cursor():
    history = ["аа", "ббб", "в"]
    whole = sum(count_tokens(msg) + 1 for msg in history)
    tail = count_tokens("в") + 1
    assert unsummarized_token_count(history, 0) == whole
    assert unsummarized_token_count(history, 2) == tail
    assert unsummarized_token_count(history, 99) == 0
    assert unsummarized_token_count(history, -5) == whole
    print("OK  в заполнение входит только история после границы саммари")


def test_summary_due_uses_fill_percent():
    assert summary_due(0.8, 80, True)
    assert summary_due(0.79, 80, True) is False
    assert summary_due(1.5, 80, False) is False
    assert summary_due(0.5, 50, True)
    assert clamp_summary_fill_percent(10) == 50
    assert clamp_summary_fill_percent(100) == 95
    assert clamp_summary_fill_percent("80") == 80
    assert clamp_summary_fill_percent("нет") == 80
    print("OK  автосуммаризация стартует на пороге заполнения")


def test_summary_cursor_migration():
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        world = Path(tmp)
        assert read_summary_cursor(world) is None
        assert default_summary_cursor(world, 4) == 0
        (world / "summary.txt").write_text("уже сжатая хроника", encoding="utf-8")
        assert default_summary_cursor(world, 4) == 4
        (world / "summary.txt").write_text("  \n", encoding="utf-8")
        assert default_summary_cursor(world, 4) == 0
        save_summary_cursor(world, 2)
        assert read_summary_cursor(world) == 2
        assert clamp_summary_cursor(9, 4) == 4
        assert clamp_summary_cursor(-3, 4) == 0
        (world / "summary_state.json").write_text("{", encoding="utf-8")
        assert read_summary_cursor(world) is None
    print("OK  старый мир получает границу по summary.txt, битый файл не затирает её нулём молча")


def test_context_indicator_shows_fill_since_summary():
    import tempfile
    from pathlib import Path

    import customtkinter as ctk

    from dungeon.app import DungeonApp

    ctk.set_appearance_mode("Dark")
    root = ctk.CTk()
    root.withdraw()
    app = DungeonApp(root)
    app.language = "ru"
    app.context_size = 8000
    app.max_tokens = 300
    app.summary_fill_percent = 80
    app.memory_enabled = False
    app.story_cards = {"cards": []}
    app.memory_bank = {"last_indexed_turn": 0, "entries": []}

    with tempfile.TemporaryDirectory() as tmp:
        world = Path(tmp)
        app.current_world_path = world
        app.history = ["Игрок: раз", "Мастер: два", "Игрок: три"]
        app.covered_count = 1
        app.update_context_indicator()

        used = unsummarized_token_count(app.history, 1)
        assert app.context_tokens == used
        assert used > 0
        assert used < unsummarized_token_count(app.history, 0)
        label = app.context_label.cget("text")
        assert format_token_count(used) in label
        assert "С суммаризации" in label
        assert "1" in app.summary_label.cget("text") or "%" in app.summary_label.cget("text")

        app.covered_count = len(app.history)
        app.update_context_indicator()
        assert app.context_tokens == 0
        assert app.context_ratio == 0
        assert "0%" in app.summary_label.cget("text")

        # Переполнение не должно ломать полоску и красит её в красный
        app.covered_count = 0
        app.context_size = 2000
        app.summary_fill_percent = 80
        app.history = ["слово " * 8000]
        app.update_context_indicator()
        assert app.context_tokens > app.context_budget, (app.context_tokens, app.context_budget)
        assert app.context_ratio >= 0.8
        assert _color_is(app.context_label.cget("text_color"), COLORS["danger"])
        assert _color_is(app.summary_label.cget("text_color"), COLORS["danger"])

    close_tk_window(app.root)
    print("OK  индикатор показывает историю с последней суммаризации и не ломается на переполнении")


def _color_is(actual, expected):
    if isinstance(actual, (list, tuple)):
        actual = actual[0] if actual else ""
    return str(actual).lower() == str(expected).lower()


def test_summary_cursor_advances_on_success_and_undo_clamps():
    import tempfile
    from pathlib import Path

    import customtkinter as ctk

    from dungeon.app import DungeonApp

    ctk.set_appearance_mode("Dark")
    root = ctk.CTk()
    root.withdraw()
    app = DungeonApp(root)
    app.memory_bank = {"last_indexed_turn": 0, "entries": []}

    with tempfile.TemporaryDirectory() as tmp:
        world = Path(tmp)
        app.current_world_path = world
        app.history = ["Игрок: а", "Мастер: б"]
        app.covered_count = 0
        # Пока саммари не записано, граница не двигается
        assert app.covered_count == 0
        app._remember_summarized_history(2)
        assert app.covered_count == 2
        assert read_summary_cursor(world) == 2

        app.undo_action()
        assert app.history == ["Игрок: а"]
        assert app.covered_count == 1
        assert read_summary_cursor(world) == 1

        app.history = ["Игрок: а"]
        app.covered_count = 1
        app.sync_introduction_to_history("давным-давно")
        assert app.history[0].startswith(INTRO_PREFIX)
        assert app.covered_count == 2
        assert read_summary_cursor(world) == 2

        app.sync_introduction_to_history("   ")
        assert app.covered_count == 1
        assert not app.history[0].startswith(INTRO_PREFIX)

        app.covered_count = 0
        app.sync_introduction_to_history("ещё раз")
        assert app.covered_count == 0

        app.history = ["Игрок: а", "Мастер: б", "Игрок: в", "Мастер: г"]
        app.covered_count = 0
        app._remember_summarized_history(2)
        assert app.covered_count == 2
        assert read_summary_cursor(world) == 2

        app.history = ["Игрок: а", "Мастер: б"]
        app.covered_count = 2
        save_summary_cursor(world, 2)
        player = app.rewind_last_reply()
        assert player == "а"
        assert app.history == ["Игрок: а"]
        assert app.covered_count == 1
        assert read_summary_cursor(world) == 1

        app.history = ["Игрок: старое", "Мастер: два", "Игрок: три"]
        app.covered_count = 3
        app.note_history_revised(0)
        assert app.covered_count == 0
        assert read_summary_cursor(world) == 0
        app.covered_count = 3
        app.note_history_revised(1)
        assert app.covered_count == 1

        app.context_size = 100
        available, _, _ = app._summary_history_budget()
        assert available < 800

        app.context_size = 400
        app.max_tokens = 300
        app.history = ["Игрок: раз"]
        app.covered_count = 0
        app.update_context_indicator()
        assert app.context_budget < HISTORY_BUDGET_FLOOR or app.context_ratio == 1.0
        assert app.context_ratio > app.context_tokens / HISTORY_BUDGET_FLOOR

    close_tk_window(app.root)
    print("OK  граница саммари сдвигается после успеха, отмены хода и правки вступления")


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
