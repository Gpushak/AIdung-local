import json
import re

STORY_CARDS_FILE = "story_cards.json"


def default_story_cards():
    return {
        "cards": [
            {
                "id": "card_001",
                "title": "Главный герой",
                "description": (
                    "Имя: Арион\nКласс: Воин\nОружие: Длинный меч и щит\nНавыки: Атлетика, Выживание"
                ),
                "triggers": ["арион", "герой", "воин", "игрок"],
            }
        ]
    }


def load_story_cards(world_path):
    path = world_path / STORY_CARDS_FILE
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "cards" in data:
                    return data
        except Exception:
            pass
    return migrate_from_characters_txt(world_path)


def save_story_cards(world_path, cards_data):
    path = world_path / STORY_CARDS_FILE
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cards_data, f, ensure_ascii=False, indent=2)


def migrate_from_characters_txt(world_path):
    characters_path = world_path / "characters.txt"
    if characters_path.exists():
        content = characters_path.read_text(encoding="utf-8").strip()
        if content:
            return {
                "cards": [
                    {
                        "id": "card_001",
                        "title": "Персонажи (миграция)",
                        "description": content,
                        "triggers": [],
                    }
                ]
            }
    return default_story_cards()


def next_card_id(cards):
    max_num = 0
    for card in cards:
        match = re.search(r"card_(\d+)", card.get("id", ""))
        if match:
            max_num = max(max_num, int(match.group(1)))
    return f"card_{max_num + 1:03d}"


def parse_triggers(text):
    if not text or not text.strip():
        return []
    parts = re.split(r"[,;\n]+", text)
    return [p.strip() for p in parts if p.strip()]


def format_triggers(triggers):
    return ", ".join(triggers)


def retrieve_relevant_cards(query, cards_data, top_k=5, min_score=1):
    query_lower = query.lower()
    query_words = set(re.findall(r"[\w\u0400-\u04ff]+", query_lower))
    scored = []
    always_include = []

    for card in cards_data.get("cards", []):
        triggers = card.get("triggers", [])
        if not triggers:
            always_include.append(card)
            continue

        score = 0
        for trigger in triggers:
            trigger_lower = trigger.lower()
            if trigger_lower in query_lower:
                score += 3
            elif trigger_lower in query_words:
                score += 2

        if score >= min_score:
            scored.append((score, card))

    scored.sort(key=lambda x: x[0], reverse=True)
    matched = [card for _, card in scored[:top_k]]

    seen_ids = {card["id"] for card in matched}
    for card in always_include:
        if card["id"] not in seen_ids:
            matched.append(card)

    return matched


def format_story_cards_block(cards):
    if not cards:
        return ""
    block = "=== РЕЛЕВАНТНЫЕ КАРТОЧКИ ИСТОРИИ ===\n"
    for card in cards:
        triggers = format_triggers(card.get("triggers", []))
        trigger_hint = f" (триггеры: {triggers})" if triggers else " (всегда активна)"
        block += f"[{card['title']}]{trigger_hint}\n{card.get('description', '')}\n\n"
    return block


def format_all_cards_for_summary(cards_data):
    cards = cards_data.get("cards", [])
    if not cards:
        return "Информация отсутствует."
    lines = []
    for card in cards:
        lines.append(f"=== {card.get('title', 'Без названия')} ===\n{card.get('description', '')}")
    return "\n\n".join(lines)
