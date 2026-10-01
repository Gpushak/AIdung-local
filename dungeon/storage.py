import json
import os
import shutil
from pathlib import Path

from .config import (
    BASE_DIR,
    DEFAULT_API_URL,
    DEFAULT_IMAGE_STYLE,
    IMAGE_PROMPT_STYLES,
    INTRODUCTION_FILE,
    SETTINGS_FILE,
    WORLD_FILES,
)
from .i18n import INTRO_PREFIX


class CorruptedDataError(Exception):
    """Файл данных повреждён и не читается даже из резервной копии."""

    def __init__(self, path, detail=""):
        self.path = Path(path)
        self.detail = detail
        super().__init__(f"{self.path.name}: {detail}" if detail else self.path.name)


def backup_path(path):
    return Path(path).with_name(Path(path).name + ".bak")


def atomic_write_text(path, text):
    """Пишет файл атомарно.

    Сначала содержимое попадает во временный файл и принудительно сбрасывается
    на диск, затем прошлое содержимое копируется в .bak, и только потом
    временный файл переименовывается на место. Поэтому обрыв записи
    (сбой питания, кончившееся место) не оставит ни пустого, ни обрезанного
    файла: старая версия останется целой в .bak.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    if path.exists():
        try:
            shutil.copy2(path, backup_path(path))
        except OSError:
            # Резервная копия — лучшее усилие; запись не должна падать из-за неё
            pass
    os.replace(tmp, path)


def atomic_write_json(path, payload):
    atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2))


def read_json_with_backup(path, default):
    """Читает JSON, а при повреждении пробует резервную копию.

    Возвращает пару (данные, восстановлено_ли_из_бэкапа). Если не читается ни
    один из файлов — бросает CorruptedDataError вместо молчаливой подстановки
    пустого значения: потерять историю кампании без предупреждения нельзя.
    """
    path = Path(path)
    first_error = None
    for candidate, is_backup in ((path, False), (backup_path(path), True)):
        if not candidate.exists():
            continue
        try:
            with open(candidate, "r", encoding="utf-8") as f:
                return json.load(f), is_backup
        except (OSError, ValueError) as e:
            first_error = e
    if first_error is not None:
        raise CorruptedDataError(path, str(first_error))
    return default, False


def format_introduction_history(intro_text):
    intro_text = intro_text.strip()
    return f"{INTRO_PREFIX} {intro_text}" if intro_text else None


def ensure_introduction_in_history(world_path, history):
    world_path = Path(world_path)
    history = list(history)
    intro_path = world_path / INTRODUCTION_FILE
    if not intro_path.exists():
        return history

    intro_text = intro_path.read_text(encoding="utf-8").strip()
    intro_msg = format_introduction_history(intro_text)

    if not intro_msg:
        if history and history[0].startswith(INTRO_PREFIX):
            return history[1:]
        return history

    if history and history[0].startswith(INTRO_PREFIX):
        history[0] = intro_msg
    else:
        history.insert(0, intro_msg)
    return history


def get_world_list():
    if not BASE_DIR.exists():
        BASE_DIR.mkdir()
    return [d.name for d in BASE_DIR.iterdir() if d.is_dir()]


def load_world_config(world_name):
    """Читает файлы мира и историю.

    Возвращает (files_content, history, restored_from_backup). При повреждении
    истории без возможности восстановления бросает CorruptedDataError — вызывающий
    код обязан сообщить игроку, а не затихотно начать новую кампанию.
    """
    world_path = Path(BASE_DIR) / str(world_name)
    files_content = {}
    for fname in WORLD_FILES:
        path = world_path / fname
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                files_content[fname] = f.read()
        else:
            files_content[fname] = ""

    history_path = world_path / "history.json"
    history, restored = read_json_with_backup(history_path, [])
    if not isinstance(history, list):
        raise CorruptedDataError(history_path, "ожидался список сообщений")
    return files_content, history, restored


def save_world_files(world_path, files_content):
    world_path = Path(world_path)
    world_path.mkdir(parents=True, exist_ok=True)
    for fname, content in files_content.items():
        atomic_write_text(world_path / fname, content)


def save_history(world_path, history):
    atomic_write_json(Path(world_path) / "history.json", history)


def normalize_api_presets(presets):
    if not isinstance(presets, list):
        return []
    normalized = []
    for preset in presets:
        if not isinstance(preset, dict):
            continue
        name = str(preset.get("name", "")).strip()
        if not name:
            continue
        normalized.append(
            {
                "name": name,
                "api_url": str(preset.get("api_url", "")),
                "api_key": str(preset.get("api_key", "")),
                "model": str(preset.get("model", "")),
            }
        )
    return normalized


def load_global_settings():
    defaults = {
        "api_url": DEFAULT_API_URL,
        "api_key": "",
        "model": "",
        "active_api_preset": "",
        "api_presets": [],
        "temperature": 0.7,
        "max_tokens": 300,
        "context_size": 16384,
        "summary_interval": 10,
        "memory_interval": 5,
        "memory_top_k": 5,
        "stream_mode": True,
        "summary_enabled": True,
        "memory_enabled": True,
        "image_prompt_style": DEFAULT_IMAGE_STYLE,
        "language": "ru",
    }
    # Настройки тоже читаем с попыткой отката на .bak: потерять сохранённые
    # API-ключи из-за битого JSON неприятно, а дефолты работают и без них.
    if SETTINGS_FILE.exists():
        try:
            saved, _ = read_json_with_backup(SETTINGS_FILE, None)
            if isinstance(saved, dict):
                defaults.update(saved)
        except CorruptedDataError:
            pass
    defaults["api_presets"] = normalize_api_presets(defaults.get("api_presets", []))
    active_preset = defaults.get("active_api_preset", "")
    if active_preset and not any(p["name"] == active_preset for p in defaults["api_presets"]):
        defaults["active_api_preset"] = ""
    if defaults.get("image_prompt_style") not in IMAGE_PROMPT_STYLES:
        defaults["image_prompt_style"] = DEFAULT_IMAGE_STYLE
    return defaults


def save_global_settings(settings):
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    atomic_write_json(SETTINGS_FILE, settings)
