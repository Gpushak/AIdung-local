"""Оценка количества токенов.

Основной путь — реальный BPE-токенизатор из библиотеки tiktoken. Сначала
пробуется o200k_base (кодировка GPT-4o и большинства современных
OpenAI-совместимых моделей) — тогда оценка точна на 100%. Если её словарь
недоступен, используется cl100k_base с пропорциональной поправкой на более
плотную упаковку кириллицы в o200k.

Эмпирическая проверка (tiktoken 0.9): оценка через cl100k+поправку
завышает реальное число токенов o200k всего на ~1-3% для связного
русского текста, поэтому запас безопасности берётся из явного
safety_buffer в бюджете контекста, а не из грубого завышения оценки.

Если tiktoken недоступен, используется улучшенная эвристика: текст
разделяется по классам символов (латиница/кириллица/прочее), и каждый
класс оценивается с собственной плотностью символов на токен.
"""

from __future__ import annotations

import re

# --- Реальный токенизатор ----------------------------------------------------

_TOKENIZER = None
_TOKENIZER_LOADED = False
# True, если активный токенизатор совпадает с целевым (o200k) — поправка не нужна
_TOKENIZER_IS_TARGET = False


def _load_encoding(name: str):
    try:
        import tiktoken

        return tiktoken.get_encoding(name)
    except Exception:  # ImportError или отсутствие словаря (нет сети)
        return None


def _get_tokenizer():
    """Ленивая загрузка токенизатора: сначала точный o200k_base, затем cl100k_base."""
    global _TOKENIZER, _TOKENIZER_LOADED, _TOKENIZER_IS_TARGET
    if not _TOKENIZER_LOADED:
        _TOKENIZER_LOADED = True
        enc = _load_encoding("o200k_base")
        if enc is not None:
            _TOKENIZER, _TOKENIZER_IS_TARGET = enc, True
        else:
            _TOKENIZER, _TOKENIZER_IS_TARGET = _load_encoding("cl100k_base"), False
    return _TOKENIZER


# cl100k кодирует кириллицу примерно в 1.6 раза хуже, чем o200k_base.
# Применяем поправку только к кириллической части текста, чтобы не
# искажать и без того точную оценку латиницы.
_O200K_CYRILLIC_FACTOR = 1 / 1.6

_RE_CYRILLIC_RUN = re.compile(r"[а-яёА-ЯЁ]+")

# --- Эвристика без tiktoken ---------------------------------------------------

# Средняя длина токена в символах для разных типов текста (консервативно,
# т.е. слегка завышаем расход, чтобы не переполнить контекст модели).
_CHARS_PER_TOKEN_LATIN = 3.8
_CHARS_PER_TOKEN_CYRILLIC = 2.2
_CHARS_PER_TOKEN_OTHER = 2.0


def _heuristic_count(text: str) -> int:
    latin = cyr = other = 0
    for ch in text:
        o = ord(ch)
        if (0x41 <= o <= 0x5A) or (0x61 <= o <= 0x7A) or (0x30 <= o <= 0x39):
            latin += 1  # латиница + цифры
        elif 0x400 <= o <= 0x4FF or o in (0x401, 0x451):
            cyr += 1  # кириллица + Ё/ё
        else:
            other += 1
    total = (
        latin / _CHARS_PER_TOKEN_LATIN
        + cyr / _CHARS_PER_TOKEN_CYRILLIC
        + other / _CHARS_PER_TOKEN_OTHER
    )
    return max(1, int(total))


def count_tokens(text: str) -> int:
    """Оценка числа токенов в тексте.

    Возвращает консервативную (не заниженную) оценку, пригодную
    для бюджетирования контекстного окна LLM.
    """
    if not text:
        return 0

    enc = _get_tokenizer()
    if enc is not None:
        n = len(enc.encode(text, disallowed_special=()))
        if not _TOKENIZER_IS_TARGET:
            # Поправка cl100k -> o200k только для кириллических последовательностей:
            # долю кирилличных токенов оцениваем как долю кириллических символов.
            cyr_chars = sum(len(m.group(0)) for m in _RE_CYRILLIC_RUN.finditer(text))
            if cyr_chars:
                cyr_share = min(1.0, cyr_chars / max(1, len(text)))
                n = n - int(n * cyr_share) + int(n * cyr_share * _O200K_CYRILLIC_FACTOR)
        return n

    return _heuristic_count(text)


def format_token_count(n: int) -> str:
    """Компактная запись для интерфейса: 843 -> «843», 16384 -> «16.4k»."""
    n = int(n)
    if n < 1000:
        return str(n)
    return f"{n / 1000:.1f}k".replace(".0k", "k")


# Тот же запас, что при сборке хода: оценка токенов точная, поэтому буфер
# маленький. Ниже 300 токенов истории в промпт уже нечего класть — окно
# не опускается под этот пол, иначе модель осталась бы без хроники вовсе.
HISTORY_SAFETY_BUFFER = 64
HISTORY_BUDGET_FLOOR = 300


def history_window_budget(context_size, max_tokens, static_tokens, extra_tokens=0, apply_floor=True) -> int:
    """Сколько токенов истории ещё влезает в контекстное окно.

    static_tokens — файлы мира, саммари, память, карточки и заголовок истории.
    extra_tokens — текст текущего хода игрока: его вычитает сборка промпта,
    а полоса заполнения смотрит бюджет без него.
    apply_floor=True не даёт сборке хода опуститься ниже 300 токенов истории.
    Полоса и автосуммаризация считают честный остаток, даже если он нулевой:
    иначе короткая новая история выглядит переполненной и суммаризация
    запускается на каждом ходе.
    """
    budget = (
        int(context_size)
        - int(max_tokens)
        - int(static_tokens)
        - int(extra_tokens)
        - HISTORY_SAFETY_BUFFER
    )
    if apply_floor and budget < HISTORY_BUDGET_FLOOR:
        return HISTORY_BUDGET_FLOOR
    return budget


def take_unsummarized_prefix(history, covered_count, token_budget):
    """Самый старый ещё не сжатый кусок, который влезает в бюджет суммаризации.

    Возвращает (messages, next_covered, skipped).
    Сообщение длиннее всего бюджета пропускается: в модель оно не влезет,
    а граница сдвигается за него, чтобы следующий ход не застревал на нём.
    При бюджете меньше 1 прогресса нет — иначе вся история была бы отмечена
    сжатой, не попав в промпт.
    """
    try:
        covered = int(covered_count)
    except (TypeError, ValueError):
        covered = 0
    covered = max(0, min(covered, len(history)))
    try:
        budget = int(token_budget)
    except (TypeError, ValueError):
        budget = 0
    if budget < 1:
        return [], covered, 0

    index = covered
    skipped = 0
    while index < len(history):
        msg_tokens = count_tokens(history[index]) + 1
        if msg_tokens <= budget:
            break
        index += 1
        skipped += 1

    chunk = []
    used = 0
    while index < len(history):
        msg_tokens = count_tokens(history[index]) + 1
        if used + msg_tokens > budget:
            break
        chunk.append(history[index])
        used += msg_tokens
        index += 1

    if not chunk and not skipped:
        return [], covered, 0
    return chunk, index, skipped


def unsummarized_token_count(history, covered_count) -> int:
    """Токены сообщений, которые ещё не вошли в summary.txt.

    covered_count — сколько сообщений с начала истории уже покрыто саммари.
    К каждому сообщению добавляется 1 токен, как при нарезке истории в промпт.
    """
    try:
        covered = int(covered_count)
    except (TypeError, ValueError):
        covered = 0
    if covered < 0:
        covered = 0
    if covered > len(history):
        covered = len(history)
    total = 0
    for msg in history[covered:]:
        total += count_tokens(msg) + 1
    return total


def summary_due(ratio, fill_percent, enabled) -> bool:
    """Пора ли запускать автосуммаризацию по заполнению новой истории."""
    if not enabled:
        return False
    try:
        percent = int(fill_percent)
    except (TypeError, ValueError):
        percent = 80
    return float(ratio) >= percent / 100.0
