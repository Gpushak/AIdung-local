import codecs
import json
import re
from datetime import datetime
from threading import Thread

import requests

from .config import API_URL, WORLD_FILES
from .memory import (
    count_completed_turns,
    format_memory_block,
    get_turn_messages,
    parse_memory_index_response,
    retrieve_relevant_memories,
    save_memory_bank,
)
from .story_cards import format_all_cards_for_summary, format_story_cards_block, retrieve_relevant_cards
from .storage import save_history
from .text_utils import clean_dm_response, clean_stream_chunk
from .tokens import count_tokens


class AIEngineMixin:
    def run_memory_indexing(self, force=False):
        if self.memory_indexing:
            return
        if not self.memory_enabled and not force:
            return
        self.memory_indexing = True
        try:
            if not self.current_world_path:
                return

            current_turns = count_completed_turns(self.history)
            last_indexed = self.memory_bank.get("last_indexed_turn", 0)
            new_turns = current_turns - last_indexed

            if not force and new_turns < self.memory_interval:
                return

            if force and new_turns == 0:
                self.root.after(0, lambda: self.add_system_message("🧠 Нет новых ходов для индексации."))
                return

            chunk_size = new_turns if force else self.memory_interval
            turn_start = last_indexed + 1
            turn_end = last_indexed + chunk_size
            messages = get_turn_messages(self.history, turn_start, turn_end)

            if not messages:
                return

            fallback_text = "\n".join(messages)
            prompt = f"""Проанализируй фрагмент текстовой RPG-сессии.
Сделай:
1. summary — 1-3 предложения, только ключевые события и факты (имена, предметы, решения)
2. keys — до 3 ключевых слов для поиска, только самые важные! (имена NPC, локации, предметы, события)
3. location — текущая локация или null
4. npcs — список упомянутых NPC

ФРАГМЕНТ:
{fallback_text}

Ответь ТОЛЬКО валидным JSON:
{{"summary": "...", "keys": ["...", "..."], "location": "...", "npcs": ["..."]}}"""

            payload = {
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": 350,
                "stream": False,
            }
            response = requests.post(API_URL, json=payload, timeout=120)
            response.raise_for_status()
            raw = response.json()["choices"][0]["message"]["content"].strip()
            parsed = parse_memory_index_response(raw, fallback_text)

            entry = {
                "id": f"mem_{len(self.memory_bank['entries']) + 1:03d}",
                "turn_start": turn_start,
                "turn_end": turn_end,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                **parsed,
            }
            self.memory_bank["entries"].append(entry)
            self.memory_bank["last_indexed_turn"] = turn_end
            save_memory_bank(self.current_world_path, self.memory_bank)

            keys_preview = ", ".join(entry.get("keys", [])[:4]) or "—"
            self.root.after(
                0,
                lambda: self.add_system_message(
                    f"🧠 Память [{entry['id']}]: {entry['summary'][:80]}... (ключи: {keys_preview})"
                ),
            )
            self.root.after(0, self.update_memory_label)

        except requests.exceptions.ConnectionError:
            self.root.after(0, lambda: self.add_system_message("❌ Банк памяти: сервер ИИ недоступен."))
        except Exception as e:
            err_msg = str(e)
            self.root.after(0, lambda msg=err_msg: self.add_system_message(f"⚠️ Ошибка индексации памяти: {msg}"))
        finally:
            self.memory_indexing = False

    def process_action(self, user_input):
        try:
            if user_input and (not self.history or f"Игрок: {user_input}" != self.history[-1]):
                self.history.append(f"Игрок: {user_input}")

            context = ""
            for fname in WORLD_FILES:
                if fname == "summary.txt":
                    continue
                path = self.current_world_path / fname
                if path.exists():
                    content = path.read_text(encoding="utf-8").strip()
                    if content:
                        context += f"=== {fname} ===\n{content}\n"

            summary_path = self.current_world_path / "summary.txt"
            summary_content = summary_path.read_text(encoding="utf-8").strip() if summary_path.exists() else ""
            if summary_content:
                context += f"=== Сжатая хроника прошлых событий (summary.txt) ===\n{summary_content}\n"

            user_content = user_input if user_input else "(Продолжай повествование.)"

            preview_msgs = []
            preview_tokens = 0
            for msg in reversed(self.history):
                msg_tokens = count_tokens(msg) + 1
                if preview_tokens + msg_tokens > 400:
                    break
                preview_msgs.insert(0, msg)
                preview_tokens += msg_tokens
            retrieval_query = user_content + "\n" + "\n".join(preview_msgs)

            if self.memory_enabled:
                relevant_memories = retrieve_relevant_memories(
                    retrieval_query, self.memory_bank, top_k=self.memory_top_k
                )
                memory_block = format_memory_block(relevant_memories)
                if memory_block:
                    context += memory_block

            relevant_cards = retrieve_relevant_cards(
                retrieval_query, self.story_cards, top_k=self.memory_top_k
            )
            cards_block = format_story_cards_block(relevant_cards)
            if cards_block:
                context += cards_block

            system_base_text = f"{context}\nИСТОРИЯ ТЕКУЩЕЙ ИГРОВОЙ СЕССИИ:\n"
            static_tokens = count_tokens(system_base_text)
            user_tokens = count_tokens(user_content)
            safety_buffer = 200

            available_history_tokens = (
                self.context_size - self.max_tokens - static_tokens - user_tokens - safety_buffer
            )
            if available_history_tokens < 300:
                available_history_tokens = 300

            short_history = []
            current_history_tokens = 0

            history_pool = self.history[:-1] if user_input else self.history
            for msg in reversed(history_pool):
                msg_tokens = count_tokens(msg) + 1
                if current_history_tokens + msg_tokens <= available_history_tokens:
                    short_history.insert(0, msg)
                    current_history_tokens += msg_tokens
                else:
                    break

            history_text = "\n".join(short_history)
            system_final_content = f"""{context}\nИСТОРИЯ ТЕКУЩЕЙ ИГРОВОЙ СЕССИИ:\n{history_text}"""
            prompt_tokens = count_tokens(system_final_content) + count_tokens(user_content)

            self.last_sent_prompt = {
                "system": system_final_content,
                "user": user_content,
                "tokens": prompt_tokens,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

            payload = {
                "messages": [
                    {"role": "system", "content": system_final_content},
                    {"role": "user", "content": user_content},
                ],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "stream": self.stream_mode,
                "stop": ["\nИгрок:", "Игрок:", "<|im_end|>", "<|eot_id|>", "```", "---"],
            }

            if self.stream_mode:
                response = requests.post(API_URL, json=payload, stream=True, timeout=120)
                response.raise_for_status()

                self.root.after(0, self.start_dm_stream)
                raw_narration = ""
                decoder = codecs.getincrementaldecoder("utf-8")("ignore")
                buffer = ""

                for chunk in response.iter_content(chunk_size=None):
                    if not chunk:
                        continue
                    buffer += decoder.decode(chunk)

                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        if not line or not line.startswith("data: "):
                            continue
                        json_str = line[6:]
                        if json_str == "[DONE]":
                            break

                        try:
                            data = json.loads(json_str)
                            content = data["choices"][0].get("delta", {}).get("content", "")
                            if content:
                                content = clean_stream_chunk(content)
                                if content:
                                    raw_narration += content
                                    self.root.after(0, lambda c=content: self.append_to_dm_stream(c))
                        except:
                            pass
                ai_text = raw_narration.strip()
            else:
                response = requests.post(API_URL, json=payload, timeout=120)
                response.raise_for_status()
                ai_text = response.json()["choices"][0]["message"]["content"].strip()
                self.root.after(0, self.start_dm_stream)

            if not ai_text:
                self.root.after(0, lambda: self.add_system_message("⚠️ Модель вернула пустой ответ."))
                return

            final_narration = clean_dm_response(ai_text)

            self.root.after(0, lambda f=final_narration: self.finalize_dm_stream(f))

            self.history.append(f"Мастер: {final_narration}")
            save_history(self.current_world_path, self.history)

            completion_tokens = count_tokens(final_narration)
            total_tokens = prompt_tokens + completion_tokens

            self.root.after(
                0,
                lambda p=prompt_tokens, c=completion_tokens, t=total_tokens: self.add_system_message(
                    f"📊 Токены: Контекст: {p} | Ответ: {c} | Всего: {t}/{self.context_size}"
                ),
            )

            if self.summary_enabled and self.turns_since_summary >= self.summary_interval:
                self.turns_since_summary = 0
                self.root.after(0, lambda: self.add_system_message("📝 ИИ пересматривает хронологию..."))
                Thread(target=self.generate_global_summary, daemon=True).start()

            if self.memory_enabled and self.turns_since_memory >= self.memory_interval:
                self.turns_since_memory = 0
                self.root.after(0, self.update_memory_label)
                Thread(target=self.run_memory_indexing, daemon=True).start()

        except requests.exceptions.ConnectionError:
            self.root.after(0, lambda: self.add_system_message("❌ Ошибка: Локальный сервер ИИ не запущен!"))
        except Exception as e:
            err_msg = str(e)
            self.root.after(0, lambda msg=err_msg: self.add_system_message(f"❌ Ошибка: {msg}"))
        finally:
            self.root.after(0, self.processing_end)

    def generate_global_summary(self):
        try:
            if not self.current_world_path:
                return

            summary_path = self.current_world_path / "summary.txt"
            old_summary = (
                summary_path.read_text(encoding="utf-8").strip() if summary_path.exists() else "Отсутствует."
            )

            story_cards_content = format_all_cards_for_summary(self.story_cards)

            prompt_template_base = f"""Перед тобой история текстовой ролевой игры, её старое краткое содержание и карточки истории.
Твоя задача: составить обновленное, чистое и емкое КРАТКОЕ СОДЕРЖАНИЕ (summary).
ПРАВИЛА:
1. Сформируй кратую исторую в хронологическомы порядке.
2. Игнорируй мелкую рутину, лишние диалоги.
3. Пиши структурированно, лаконично.
4. Обязательно учти информацию из СТАРОГО краткого содержания.
5. УЧТИ ИНФОРМАЦИЮ ИЗ КАРТОЧЕК ИСТОРИИ.

КАРТОЧКИ ИСТОРИИ:
{story_cards_content}

СТАРОЕ КРАТКОЕ СОДЕРЖАНИЕ:
{old_summary}

АКТУАЛЬНАЯ ИСТОРИЯ ИГРЫ:

Выдай только текст нового краткого содержания простым текстом без лишних *, вступлений и Markdown."""

            summary_max_tokens = 1000
            base_prompt_tokens = count_tokens(prompt_template_base)
            safety_buffer = 400

            available_summary_history = (
                self.context_size - summary_max_tokens - base_prompt_tokens - safety_buffer
            )
            if available_summary_history < 800:
                available_summary_history = 800

            short_history = []
            current_history_tokens = 0

            for msg in reversed(self.history):
                msg_tokens = count_tokens(msg) + 1
                if current_history_tokens + msg_tokens <= available_summary_history:
                    short_history.insert(0, msg)
                    current_history_tokens += msg_tokens
                else:
                    break

            history_text = "\n".join(short_history)

            prompt = f"""Перед тобой история текстовой ролевой игры, её старое краткое содержание и карточки истории.
Твоя задача: составить обновленное, чистое и емкое КРАТКОЕ СОДЕРЖАНИЕ (summary).
ПРАВИЛА:
1. Сформируй кратую исторую в хронологическомы порядке.
2. Игнорируй мелкую рутину.
3. Пиши лаконично, тезисно.
4. Учти СТАРОЕ краткое содержание.

КАРТОЧКИ ИСТОРИИ:
{story_cards_content}

СТАРОЕ КРАТКОЕ СОДЕРЖАНИЕ:
{old_summary}

АКТУАЛЬНАЯ ИСТОРИЯ ИГРЫ:
{history_text}

Выдай только текст нового краткого содержания простым текстом без лишних *, вступлений и Markdown."""

            payload = {
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": summary_max_tokens,
                "stream": False,
            }
            response = requests.post(API_URL, json=payload, timeout=180)
            response.raise_for_status()
            new_summary = response.json()["choices"][0]["message"]["content"].strip()
            new_summary = new_summary.replace("```json", "").replace("```", "").strip()

            if new_summary:
                summary_path.write_text(new_summary, encoding="utf-8")
                self.root.after(
                    0, lambda: self.add_system_message("✨ Краткое содержание мира успешно синхронизировано!")
                )
                self.root.after(0, self.update_summary_label)

        except Exception as e:
            err_msg = str(e)
            self.root.after(
                0, lambda msg=err_msg: self.add_system_message(f"⚠️ Не удалось автоматически обновить саммари: {msg}")
            )
