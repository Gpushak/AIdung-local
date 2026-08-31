import json
from pathlib import Path

from .config import BASE_DIR, DEFAULT_API_URL, INTRODUCTION_FILE, SETTINGS_FILE, WORLD_FILES
from .i18n import INTRO_PREFIX


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
    world_path = Path(BASE_DIR) / str(world_name)
    files_content = {}
    for fname in WORLD_FILES:
        path = world_path / fname
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                files_content[fname] = f.read()
        else:
            files_content[fname] = ""

    history = []
    history_path = world_path / "history.json"
    if history_path.exists():
        try:
            with open(history_path, "r", encoding="utf-8") as f:
                history = json.load(f)
        except:
            history = []
    return files_content, history


def save_world_files(world_path, files_content):
    world_path = Path(world_path)
    world_path.mkdir(parents=True, exist_ok=True)
    for fname, content in files_content.items():
        path = world_path / fname
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)


def save_history(world_path, history):
    world_path = Path(world_path)
    history_path = world_path / "history.json"
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


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
        "language": "ru",
    }
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                defaults.update(saved)
        except:
            pass
    defaults["api_presets"] = normalize_api_presets(defaults.get("api_presets", []))
    active_preset = defaults.get("active_api_preset", "")
    if active_preset and not any(p["name"] == active_preset for p in defaults["api_presets"]):
        defaults["active_api_preset"] = ""
    return defaults


def save_global_settings(settings):
    if not BASE_DIR.exists():
        BASE_DIR.mkdir()
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f)
