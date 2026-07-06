import json

from .config import BASE_DIR, SETTINGS_FILE, WORLD_FILES


def get_world_list():
    if not BASE_DIR.exists():
        BASE_DIR.mkdir()
    return [d.name for d in BASE_DIR.iterdir() if d.is_dir()]


def load_world_config(world_name):
    world_path = BASE_DIR / world_name
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
    world_path.mkdir(parents=True, exist_ok=True)
    for fname, content in files_content.items():
        path = world_path / fname
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)


def save_history(world_path, history):
    history_path = world_path / "history.json"
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def load_global_settings():
    defaults = {
        "temperature": 0.9,
        "max_tokens": 400,
        "context_size": 24576,
        "summary_interval": 10,
        "memory_interval": 5,
        "memory_top_k": 5,
        "stream_mode": True,
    }
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                defaults.update(saved)
        except:
            pass
    return defaults


def save_global_settings(settings):
    if not BASE_DIR.exists():
        BASE_DIR.mkdir()
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f)
