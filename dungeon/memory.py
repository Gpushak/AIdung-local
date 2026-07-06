import json
import re

MEMORY_BANK_FILE = "memory_bank.json"


def load_memory_bank(world_path):
    path = world_path / MEMORY_BANK_FILE
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "entries" in data:
                    return data
        except:
            pass
    return {"last_indexed_turn": 0, "entries": []}


def save_memory_bank(world_path, bank):
    path = world_path / MEMORY_BANK_FILE
    with open(path, "w", encoding="utf-8") as f:
        json.dump(bank, f, ensure_ascii=False, indent=2)


def count_completed_turns(history):
    turns = 0
    i = 0
    while i < len(history) - 1:
        if history[i].startswith("Игрок:") and history[i + 1].startswith("Мастер:"):
            turns += 1
            i += 2
        else:
            i += 1
    return turns


def get_turn_messages(history, turn_start, turn_end):
    """Возвращает сообщения для ходов turn_start..turn_end (1-based, включительно)."""
    messages = []
    current_turn = 0
    i = 0
    while i < len(history):
        if history[i].startswith("Игрок:"):
            chunk = [history[i]]
            if i + 1 < len(history) and history[i + 1].startswith("Мастер:"):
                chunk.append(history[i + 1])
                current_turn += 1
                if turn_start <= current_turn <= turn_end:
                    messages.extend(chunk)
                i += 2
                continue
        i += 1
    return messages


def retrieve_relevant_memories(query, bank, top_k=5, min_score=1):
    query_lower = query.lower()
    query_words = set(re.findall(r"[\w\u0400-\u04ff]+", query_lower))
    scored = []
    for entry in bank.get("entries", []):
        score = 0
        for key in entry.get("keys", []):
            key_lower = key.lower()
            if key_lower in query_lower:
                score += 3
            elif key_lower in query_words:
                score += 2
        for npc in entry.get("npcs", []):
            if npc.lower() in query_lower:
                score += 2
        location = entry.get("location")
        if location and location.lower() in query_lower:
            score += 2
        if score >= min_score:
            scored.append((score, entry))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [entry for _, entry in scored[:top_k]]


def format_memory_block(memories):
    if not memories:
        return ""
    block = "=== РЕЛЕВАНТНЫЕ ВОСПОМИНАНИЯ (банк памяти) ===\n"
    for mem in memories:
        keys = ", ".join(mem.get("keys", []))
        block += f"[{mem['id']}] ({keys}): {mem['summary']}\n"
    return block + "\n"


def parse_memory_index_response(raw, fallback_text):
    cleaned = raw.replace("```json", "").replace("```", "").strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group())
            return {
                "summary": str(data.get("summary", fallback_text[:200])).strip(),
                "keys": [str(k).strip() for k in data.get("keys", []) if str(k).strip()],
                "location": data.get("location") or None,
                "npcs": [str(n).strip() for n in data.get("npcs", []) if str(n).strip()],
            }
        except:
            pass
    return {"summary": fallback_text[:200], "keys": [], "location": None, "npcs": []}


def sync_memory_bank_after_undo(history, memory_bank):
    current_turns = count_completed_turns(history)
    while memory_bank.get("entries") and memory_bank["entries"][-1].get("turn_end", 0) > current_turns:
        memory_bank["entries"].pop()
    if memory_bank.get("entries"):
        memory_bank["last_indexed_turn"] = memory_bank["entries"][-1]["turn_end"]
    else:
        memory_bank["last_indexed_turn"] = 0
    turns_since_memory = current_turns - memory_bank.get("last_indexed_turn", 0)
    return memory_bank, turns_since_memory
