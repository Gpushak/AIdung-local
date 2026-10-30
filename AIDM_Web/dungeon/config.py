import re
import sys
from pathlib import Path

from .i18n import default_templates

DEFAULT_API_URL = "http://localhost:1234/v1/chat/completions"

# Форматы промптов для генерации изображений. По умолчанию — Stable Diffusion,
# так как это самая распространённая локальная модель.
IMAGE_PROMPT_STYLES = ("sd", "midjourney", "flux", "generic")
DEFAULT_IMAGE_STYLE = "sd"

# Визуальный стиль дописывается в готовый промпт. none — ничего не добавлять.
IMAGE_LOOKS = ("none", "anime", "realism", "painting", "cinematic")
DEFAULT_IMAGE_LOOK = "none"
IMAGE_LOOK_SUFFIX = {
    "anime": "anime style, cel shading, clean lineart, expressive eyes, vibrant colors",
    "realism": "photorealistic, realistic skin, natural lighting, lifelike proportions, detailed materials",
    "painting": "oil painting, visible brushstrokes, painterly light, fine art",
    "cinematic": "cinematic still, dramatic lighting, shallow depth of field, film color grade",
}

# Сколько токенов можно отдать на ответ вспомогательного промпта.
DEFAULT_RESPONSE_LIMITS = {
    "prompt.memory_index": 350,
    "prompt.summary": 1000,
    "prompt.scene_image": 700,
    "prompt.card_desc_gen": 400,
}
RESPONSE_LIMIT_MAX = 16384

def clamp_response_limits(raw):
    """Полная таблица лимитов: неизвестные и пустые значения остаются встроенными."""
    result = dict(DEFAULT_RESPONSE_LIMITS)
    if not isinstance(raw, dict):
        return result
    for key in DEFAULT_RESPONSE_LIMITS:
        if key not in raw:
            continue
        try:
            value = int(raw[key])
        except (TypeError, ValueError):
            continue
        result[key] = min(RESPONSE_LIMIT_MAX, max(1, value))
    return result


def response_token_limit(limits, key) -> int:
    """Лимит ответа для одного промпта. Неизвестный ключ остаётся на своём встроенном значении."""
    return clamp_response_limits(limits).get(key, DEFAULT_RESPONSE_LIMITS.get(key, 300))


def apply_image_look(prompt, look):
    """Дописывает фразу стиля в промпт. Параметры Midjourney остаются в конце."""
    suffix = IMAGE_LOOK_SUFFIX.get(look, "")
    text = (prompt or "").strip()
    if not suffix or not text or suffix.lower() in text.lower():
        return text
    match = re.search(r"\s--[A-Za-z]", text)
    if match:
        head = text[: match.start()].rstrip(" ,.")
        return f"{head}, {suffix}{text[match.start() :]}"
    return text.rstrip(" ,.") + ", " + suffix


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _worlds_dir():
    # У собранного exe миры лежат рядом с программой, чтобы папку можно было отдать zip-архивом.
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "worlds"
    return PROJECT_ROOT / "worlds"


BASE_DIR = _worlds_dir()

SETTINGS_FILE = BASE_DIR / "settings.json"

WORLD_FILES = {
    "introduction.txt": "introduction.txt",
    "ai_instructions.txt": "ai_instructions.txt",
    "plot_basics.txt": "plot_basics.txt",
    "author_notes.txt": "author_notes.txt",
    "summary.txt": "summary.txt",
}

INTRODUCTION_FILE = "introduction.txt"

DEFAULT_TEMPLATES = default_templates("ru")
STORY_CARDS_KEY = "__story_cards__"

COLORS = {
    "accent": "#e6b450",
    "player_color": "#8bc34a",
    "dm_color": "#DBBA5F",
    "system_color": "#61afef",
    "button_hover": "#d4a340",
    "danger": "#d9534f",
    "danger_hover": "#c9302c",
    "listbox_bg": "#2b2b2b",
    "listbox_sel": "#3a3a3a",
}

WINDOW_SIZE = "900x1200"
