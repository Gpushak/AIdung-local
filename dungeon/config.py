import sys
from pathlib import Path

from .i18n import default_templates

DEFAULT_API_URL = "http://localhost:1234/v1/chat/completions"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).parent / "worlds"
else:
    BASE_DIR = PROJECT_ROOT / "worlds"

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
STORY_CARDS_LABEL = "Story cards"

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
