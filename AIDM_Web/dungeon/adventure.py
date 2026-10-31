"""Проверки d20, карточка героя и автокарточки встреч. Только веб."""

import json
import random
import re

from .i18n import t
from .storage import CorruptedDataError, atomic_write_json, atomic_write_text, read_json_with_backup
from .story_cards import next_card_id

HERO_FILE = "hero.json"
MODE_FILE = "mode.txt"
ADVENTURE_MODE = "adventure"
SANDBOX_MODE = "sandbox"
ALLOWED_DC = (10, 13, 16, 19)
STAT_KEYS = (
    "strength",
    "dexterity",
    "constitution",
    "intelligence",
    "wisdom",
    "charisma",
)

_JSON_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


def roll_d20():
    """Кубик кидает программа, не модель."""
    return random.randint(1, 20)


def accepted_dc(value):
    """Сложность только из набора 10 / 13 / 16 / 19. Остальные числа отбрасываются."""
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    if number in ALLOWED_DC:
        return number
    return None


def roll_succeeds(roll, dc):
    """1 — провал, 20 — успех. Иначе успех, если результат не ниже сложности."""
    try:
        rolled = int(roll)
        target = int(dc)
    except (TypeError, ValueError):
        return False
    if rolled == 1:
        return False
    if rolled == 20:
        return True
    return rolled >= target


def _flag(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "да"}
    return False


def extract_json_object(text):
    if not isinstance(text, str):
        return None
    raw = _JSON_FENCE.sub("", text.strip()).strip()
    candidates = [raw]
    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        candidates.append(raw[start : end + 1])
    for candidate in candidates:
        try:
            data = json.loads(candidate)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(data, dict):
            return data
    return None


def parse_check(data):
    """None, если проверки нет или сложность вне набора."""
    if not isinstance(data, dict) or not _flag(data.get("needed")):
        return None
    dc = accepted_dc(data.get("dc", data.get("difficulty")))
    if dc is None:
        return None
    name = str(data.get("name") or "").strip() or "d20"
    return {"name": name, "dc": dc}


def format_roll_fact(lang, name, dc, roll, success):
    return t(
        lang,
        "check.fact",
        name=name,
        dc=dc,
        roll=roll,
        result=t(lang, "check.success" if success else "check.fail"),
    )


def clamp_stat(value, default=10):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return min(30, max(1, number))


def normalize_hero(payload):
    if not isinstance(payload, dict):
        raise ValueError("hero")
    name = str(payload.get("name") or "").strip()
    if not name:
        raise ValueError("name")
    source = payload.get("stats") if isinstance(payload.get("stats"), dict) else payload
    hero = {
        "name": name,
        "appearance": str(payload.get("appearance") or payload.get("look") or "").strip(),
        "equipment": str(payload.get("equipment") or payload.get("gear") or "").strip(),
    }
    for key in STAT_KEYS:
        hero[key] = clamp_stat(source.get(key, payload.get(key, 10)))
    return hero


def hero_is_ready(hero):
    return isinstance(hero, dict) and bool(str(hero.get("name") or "").strip())


def load_hero(world_path):
    try:
        data, _ = read_json_with_backup(world_path / HERO_FILE, None)
    except CorruptedDataError:
        return None
    if not isinstance(data, dict):
        return None
    return data


def save_hero(world_path, hero):
    atomic_write_json(world_path / HERO_FILE, hero)


def write_mode_mark(world_path):
    """Метка мира приключения. У песочницы файла нет."""
    atomic_write_text(world_path / MODE_FILE, ADVENTURE_MODE + "\n")


def format_hero_block(hero, lang):
    if not hero_is_ready(hero):
        return ""
    values = {key: hero.get(key, 10) for key in STAT_KEYS}
    return t(
        lang,
        "prompt.hero_block",
        name=str(hero.get("name") or "").strip(),
        appearance=str(hero.get("appearance") or "").strip() or t(lang, "prompt.none"),
        equipment=str(hero.get("equipment") or "").strip() or t(lang, "prompt.none"),
        **values,
    )


def hero_summary(hero, lang):
    return format_hero_block(hero, lang) or t(lang, "prompt.none")


def parse_followup(data):
    if not isinstance(data, dict):
        return {"equipment": "", "appearance": "", "stats": {}, "characters": []}
    stats_raw = data.get("stats") if isinstance(data.get("stats"), dict) else {}
    stats = {}
    for key in STAT_KEYS:
        if key in stats_raw:
            stats[key] = clamp_stat(stats_raw[key])
    characters = []
    raw_people = data.get("characters") if isinstance(data.get("characters"), list) else []
    for item in raw_people:
        if not isinstance(item, dict):
            continue
        triggers = item.get("triggers") if isinstance(item.get("triggers"), list) else []
        characters.append(
            {
                "name": str(item.get("name") or item.get("title") or "").strip(),
                "description": str(item.get("description") or "").strip(),
                "triggers": [str(part).strip() for part in triggers if str(part).strip()],
                "returns": _flag(item.get("returns") or item.get("recurring") or item.get("will_return")),
                "conflict": _flag(item.get("conflict")),
            }
        )
    return {
        "equipment": str(data.get("equipment") or data.get("gear") or "").strip(),
        "appearance": str(data.get("appearance") or data.get("look") or "").strip(),
        "stats": stats,
        "characters": characters,
    }


def changed_stats(hero, proposed):
    current = hero if isinstance(hero, dict) else {}
    changes = {}
    for key, value in (proposed or {}).items():
        if key not in STAT_KEYS:
            continue
        if clamp_stat(current.get(key, 10)) != value:
            changes[key] = value
    return changes


def cards_with_characters(cards_data, characters):
    """Новая карточка — только именной персонаж, который вернётся или в конфликте."""
    cards = [dict(card) for card in (cards_data or {}).get("cards") or []]
    titles = {str(card.get("title") or "").strip().casefold() for card in cards}
    added = []
    for person in characters or []:
        name = str(person.get("name") or "").strip()
        if not name or not (person.get("returns") or person.get("conflict")):
            continue
        if name.casefold() in titles:
            continue
        triggers = list(person.get("triggers") or []) or [name]
        cards.append(
            {
                "id": next_card_id(cards),
                "title": name,
                "description": person.get("description") or "",
                "triggers": triggers,
            }
        )
        titles.add(name.casefold())
        added.append(cards[-1])
    return {"cards": cards}, added
