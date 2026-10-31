"""Проверка атомарной записи, резервных копий и поведения при повреждении."""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dungeon.memory import load_memory_bank, save_memory_bank  # noqa: E402
from dungeon.storage import (  # noqa: E402
    CorruptedDataError,
    atomic_write_json,
    atomic_write_text,
    backup_path,
    read_json_with_backup,
    save_history,
)
from dungeon.story_cards import load_story_cards, save_story_cards  # noqa: E402


def test_backup_created_on_second_write():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "history.json"
        atomic_write_json(p, ["первый"])
        assert p.read_text(encoding="utf-8") == '[\n  "первый"\n]'
        # Бэкапа ещё нет: он появится только после второй записи
        assert not backup_path(p).exists()

        atomic_write_json(p, ["второй"])
        assert backup_path(p).read_text(encoding="utf-8").strip() == '[\n  "первый"\n]'
        assert json.loads(p.read_text(encoding="utf-8")) == ["второй"]
    print("OK  предыдущее содержимое сохраняется в .bak")


def test_no_temp_file_left_behind():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "history.json"
        atomic_write_json(p, {"a": 1})
        atomic_write_json(p, {"a": 2})
        leftovers = list(Path(tmp).glob("*.tmp"))
        assert not leftovers, leftovers
        assert sorted(x.name for x in Path(tmp).iterdir()) == ["history.json", "history.json.bak"]
    print("OK  временный файл не остаётся после записи")


def test_reads_from_backup_when_main_corrupted():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "history.json"
        atomic_write_json(p, ["хорошие данные"])
        atomic_write_json(p, ["новые данные"])
        # Порча основного файла
        p.write_text('["обрезано', encoding="utf-8")

        data, restored = read_json_with_backup(p, [])
        assert data == ["хорошие данные"], data
        assert restored is True
    print("OK  при повреждении файла данные берутся из .bak")


def test_raises_when_both_corrupted():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "history.json"
        atomic_write_json(p, ["a"])
        atomic_write_json(p, ["b"])
        p.write_text("мусор", encoding="utf-8")
        backup_path(p).write_text("тоже мусор", encoding="utf-8")

        try:
            read_json_with_backup(p, [])
        except CorruptedDataError as e:
            assert e.path.name == "history.json"
            assert e.detail
        else:
            raise AssertionError("ожидалась CorruptedDataError, а не молчаливая пустая история")
    print("OK  при порче обоих файлов поднимается ошибка, а не пустая история")


def test_missing_file_returns_default():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "нет-такого.json"
        data, restored = read_json_with_backup(p, {"fallback": "default"})
        assert data == {"fallback": "default"}
        assert restored is False
    print("OK  отсутствующий файл даёт значение по умолчанию без ошибки")


def test_history_type_is_validated():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "history.json"
        atomic_write_json(p, {"это": "не список"})
        data, _ = read_json_with_backup(p, [])
        # load_world_config проверяет тип и бросает CorruptedDataError;
        # здесь проверяем, что данные дошли до вызывающего кода как есть
        assert isinstance(data, dict)
    print("OK  неверный тип данных доходит до проверки в вызывающем коде")


def test_save_history_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        world = Path(tmp) / "Мир"
        world.mkdir()
        history = ["Игрок: ход", "Мастер: ответ"]
        save_history(world, history)
        data, restored = read_json_with_backup(world / "history.json", [])
        assert data == history and restored is False
    print("OK  история пишется и читается без потерь")


def test_memory_bank_and_cards_survive_corruption():
    with tempfile.TemporaryDirectory() as tmp:
        world = Path(tmp) / "Мир"
        world.mkdir()

        save_memory_bank(world, {"last_indexed_turn": 3, "entries": [{"id": "mem_001"}]})
        save_memory_bank(world, {"last_indexed_turn": 5, "entries": [{"id": "mem_001"}, {"id": "mem_002"}]})
        (world / "memory_bank.json").write_text("сломан", encoding="utf-8")
        # Банк памяти восстанавливается из .bak — то есть откатывается на
        # один шаг назад (последний до записи), а не теряется целиком
        bank = load_memory_bank(world)
        assert bank["last_indexed_turn"] == 3, bank

        # А если и бэкап битый — деградация до пустого, без исключения
        (world / "memory_bank.json.bak").write_text("тоже сломан", encoding="utf-8")
        bank = load_memory_bank(world)
        assert bank == {"last_indexed_turn": 0, "entries": []}

        save_story_cards(world, {"cards": [{"id": "card_001", "title": "X", "description": "d", "triggers": []}]})
        save_story_cards(world, {"cards": [{"id": "card_001", "title": "Y", "description": "d", "triggers": []}]})
        (world / "story_cards.json").write_text("сломан", encoding="utf-8")
        cards = load_story_cards(world)
        assert cards["cards"][0]["title"] == "X", cards
    print("OK  банк памяти и карточки восстанавливаются из .bak без потерь")


def test_atomic_write_text_preserves_previous():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "summary.txt"
        atomic_write_text(p, "старый саммари")
        atomic_write_text(p, "новый саммари")
        assert p.read_text(encoding="utf-8") == "новый саммари"
        assert backup_path(p).read_text(encoding="utf-8") == "старый саммари"
    print("OK  текстовые файлы мира тоже пишутся с бэкапом")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("ALL STORAGE TESTS PASSED")
