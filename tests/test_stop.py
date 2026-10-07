"""Проверка чтения потока и прерывания генерации без GUI и сети."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dungeon.ai_engine import ACTION, AIEngineMixin, _iter_response_deltas  # noqa: E402
from dungeon.text_utils import StreamThinkFilter, clean_dm_response  # noqa: E402


class FakeResponse:
    """Отдаёт заранее заданные куски тела и считает закрытия."""

    def __init__(self, chunks):
        self.chunks = chunks
        self.closed = False

    def iter_content(self, chunk_size=None):
        for chunk in self.chunks:
            yield chunk

    def close(self):
        self.closed = True


class FakeApp(AIEngineMixin):
    """Минимальный носитель состояния, нужного _read_response."""

    def __init__(self):
        self._cancel_events = {}


def sse(*deltas):
    lines = []
    for delta in deltas:
        payload = {"choices": [{"delta": {"content": delta}}]}
        lines.append(f"data: {json.dumps(payload, ensure_ascii=False)}\n")
    return "".join(lines).encode("utf-8")


def test_sse_deltas_split_across_chunks():
    raw = sse("Привет", ", ", "мир")
    # Каждый символ отдельным сетевым чанком — проверяем инкрементальный разбор
    response = FakeResponse([raw[i : i + 1] for i in range(len(raw))])
    assert "".join(_iter_response_deltas(response)) == "Привет, мир"


def test_sse_done_marker_stops_reading():
    raw = sse("начало") + b"data: [DONE]\n"
    response = FakeResponse([raw])
    assert "".join(_iter_response_deltas(response)) == "начало"


def test_last_line_without_newline_is_kept():
    last = b'data: {"choices":[{"delta":{"content":"' + "второй".encode("utf-8") + b'"}}]}'
    raw = sse("первый") + last
    response = FakeResponse([raw])
    assert "".join(_iter_response_deltas(response)) == "первыйвторой"


def test_plain_json_fallback_when_server_ignores_stream():
    body = json.dumps({"choices": [{"message": {"content": "Обычный ответ"}}]}, ensure_ascii=False)
    response = FakeResponse([body.encode("utf-8")])
    assert "".join(_iter_response_deltas(response)) == "Обычный ответ"


def test_multimodal_content_parts():
    payload = {"choices": [{"delta": {"content": [{"type": "text", "text": "часть1"}, {"type": "text", "text": "часть2"}]}}]}
    raw = f"data: {json.dumps(payload, ensure_ascii=False)}\n".encode("utf-8")
    assert "".join(_iter_response_deltas(FakeResponse([raw]))) == "часть1часть2"


def test_read_response_stops_on_cancel_and_closes():
    app = FakeApp()
    app._begin_operation(ACTION)
    # Пользователь жмёт «Стоп» до чтения первой дельты
    app._cancel_events[ACTION].set()
    response = FakeResponse([sse("до", "после")])
    text, cancelled = app._read_response(response, ACTION)
    assert text == ""
    assert cancelled is True
    assert response.closed is True


def test_read_response_collects_all_when_not_cancelled():
    app = FakeApp()
    app._begin_operation(ACTION)
    response = FakeResponse([sse("всё ", "слова")])
    text, cancelled = app._read_response(response, ACTION)
    assert text == "всё слова"
    assert cancelled is False


def test_request_stop_reports_and_marks_operation():
    app = FakeApp()
    app._begin_operation(ACTION)
    assert app.request_stop(ACTION) == [ACTION]
    assert app.is_cancelled(ACTION) is True
    # Повторное нажатие ничего не возвращает и не падает
    assert app.request_stop(ACTION) == []


def test_request_stop_without_operations_is_noop():
    app = FakeApp()
    assert app.request_stop() == []


def test_end_operation_clears_flag():
    app = FakeApp()
    app._begin_operation(ACTION)
    app._end_operation(ACTION)
    assert app.is_cancelled(ACTION) is False


def test_begin_operation_resets_previous_cancel():
    app = FakeApp()
    app._begin_operation(ACTION)
    app.request_stop(ACTION)
    app._end_operation(ACTION)
    # Новый запуск той же операции не должен остаться «залипшим» в остановленном
    app._begin_operation(ACTION)
    assert app.is_cancelled(ACTION) is False
    response = FakeResponse([sse("свежий ответ")])
    text, cancelled = app._read_response(response, ACTION)
    assert (text, cancelled) == ("свежий ответ", False)


def test_think_filter_removes_reasoning_in_stream():
    f = StreamThinkFilter()
    out = f.feed("<think>секрет</think>") + f.feed("Ответ")
    assert out == "Ответ"
    # Блок размышления вырезается; многоточие — штатная метка обрезанного
    # ответа в fix_truncated_text, а не следствие reasoning-фильтра.
    assert "<think>" not in clean_dm_response("Ответ.<think>запасное</think>")
    assert "запасное" not in clean_dm_response("Ответ.<think>запасное</think>")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"OK  {name}")
    print("ALL TESTS PASSED")
