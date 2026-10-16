from datetime import datetime

import requests

from .api_stream import ACTION, DeltaBatcher
from .i18n import DM_PREFIX, PLAYER_PREFIX, localize_history, t
from .storage import save_history
from .text_utils import StreamThinkFilter, clean_dm_response, clean_stream_chunk
from .tokens import count_tokens, history_window_budget, reply_tokens, summary_due


class TurnMixin:
    def process_action(self, user_input="", direction_hint=None):
        self._last_api_usage = None
        try:
            if direction_hint:
                direction_hint = direction_hint.strip()
                history_label = direction_hint
                if direction_hint and (
                    not self.history or f"{PLAYER_PREFIX} {history_label}" != self.history[-1]
                ):
                    self.history.append(f"{PLAYER_PREFIX} {history_label}")
                user_content = t(self.language, "prompt.direction", hint=direction_hint)
            else:
                if user_input and (not self.history or f"{PLAYER_PREFIX} {user_input}" != self.history[-1]):
                    self.history.append(f"{PLAYER_PREFIX} {user_input}")
                user_content = user_input if user_input else t(self.language, "prompt.continue")

            retrieval_query = self._retrieval_query(user_content)
            context = self._static_context_text(retrieval_query)

            system_base_text = f"{context}\n{t(self.language, 'prompt.history_header')}\n"
            static_tokens = count_tokens(system_base_text)
            user_tokens = count_tokens(user_content)
            # Пол в 300 токенов здесь намеренный: ход не должен остаться без истории.
            # Полоса считает тот же остаток без пола и без текста игрока.
            available_history_tokens = history_window_budget(
                self.context_size, self.max_tokens, static_tokens, user_tokens
            )

            short_history = []
            current_history_tokens = 0

            history_pool = self.history[:-1] if (user_input or direction_hint) else self.history
            for msg in reversed(history_pool):
                msg_tokens = count_tokens(msg) + 1
                if current_history_tokens + msg_tokens <= available_history_tokens:
                    short_history.insert(0, msg)
                    current_history_tokens += msg_tokens
                else:
                    break

            history_text = "\n".join(localize_history(self.language, short_history))
            system_final_content = f"""{context}\n{t(self.language, 'prompt.history_header')}\n{history_text}"""
            prompt_tokens = count_tokens(system_final_content) + count_tokens(user_content)

            self.last_sent_prompt = {
                "system": system_final_content,
                "user": user_content,
                "tokens": prompt_tokens,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

            payload = self._api_payload(
                messages=[
                    {
                        "role": "system",
                        "content": system_final_content
                        + "\n\n"
                        + t(
                            self.language,
                            "prompt.no_reasoning",
                        ),
                    },
                    {"role": "user", "content": user_content},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                # Поток запрашивается всегда: только так ответ можно прервать
                # кнопкой остановки. stream_mode теперь управляет показом.
                stream=True,
                stop=[
                    f"\n{PLAYER_PREFIX}",
                    PLAYER_PREFIX,
                    f"\n{t(self.language, 'hist.player')}",
                    t(self.language, "hist.player"),
                    "<|im_end|>",
                    "<|eot_id|>",
                    "```",
                    "---",
                    "<think>",
                    "</think>",
                ],
            )

            response = self._api_post(payload, stream=True, timeout=180)
            response.raise_for_status()

            # Заголовок Мастера рисуем только после успешного ответа: иначе
            # при ошибке подключения осталась бы висящая метка в логе.
            self.root.after(0, self.start_dm_stream)

            think_filter = StreamThinkFilter()
            # Дельты копятся и уходят в Tk пачками — см. DeltaBatcher
            batcher = DeltaBatcher(
                lambda chunk: self.root.after(0, lambda c=chunk: self.append_to_dm_stream(c))
            )

            def on_delta(delta):
                content = clean_stream_chunk(think_filter.feed(delta))
                if content and self.stream_mode:
                    batcher.add(content)
                return content

            ai_text, cancelled = self._read_response(response, ACTION, on_delta)
            # Хвост, накопившийся за последние 50 мс, показываем сразу
            batcher.flush_now()

            if not ai_text:
                # Пустой ответ: убираем заголовок Мастера, чтобы не оставлять
                # висящий курсор в логе, и сообщаем причину.
                self.root.after(0, self.abort_dm_stream)
                key = "msg.action_stopped" if cancelled else "msg.empty_model"
                self.root.after(0, lambda k=key: self.add_system_message(self.tr(k)))
                return

            final_narration = clean_dm_response(ai_text)

            self.root.after(0, lambda f=final_narration: self.finalize_dm_stream(f))

            self.history.append(f"{DM_PREFIX} {final_narration}")
            save_history(self.current_world_path, self.history)

            if cancelled:
                # Частичный ответ сохраняем в истории, но фоновые задачи не
                # запускаем — пользователь явно попросил остановиться.
                self.root.after(0, lambda: self.add_system_message(self.tr("msg.action_stopped")))
                return

            completion_tokens = reply_tokens(getattr(self, "_last_api_usage", None), final_narration)
            total_tokens = prompt_tokens + completion_tokens

            self.root.after(0, self.update_context_indicator)

            self.root.after(
                0,
                lambda p=prompt_tokens, c=completion_tokens, t=total_tokens: self.add_system_message(
                    self.tr("msg.tokens", p=p, c=c, t=t, ctx=self.context_size)
                ),
            )

            _used, _budget, fill_ratio = self.context_fill_state()
            self._schedule_summary_after_turn = summary_due(
                fill_ratio, self.summary_fill_percent, self.summary_enabled
            )
            if self._schedule_summary_after_turn:
                self.root.after(0, lambda: self.add_system_message(self.tr("msg.reviewing")))

            self._schedule_memory_after_turn = (
                self.memory_enabled and self.turns_since_memory >= self.memory_interval
            )
            if self._schedule_memory_after_turn:
                self.turns_since_memory = 0
                self.root.after(0, self.update_memory_label)

        except requests.exceptions.ConnectionError:
            self.root.after(0, lambda: self.add_system_message(self.tr("msg.no_server")))
        except Exception as e:
            err_msg = str(e)
            self.root.after(0, lambda msg=err_msg: self.add_system_message(self.tr("msg.error", msg=msg)))
        finally:
            self.root.after(0, self._finish_player_turn)

    def _finish_player_turn(self):
        self.processing = False
        self._end_operation(ACTION)
        # В том числе после остановки: обрыв ответа уже в истории, полоса должна его учесть.
        self.update_context_indicator()
        if self._schedule_summary_after_turn:
            self._schedule_summary_after_turn = False
            self.start_global_summary()
        if self._schedule_memory_after_turn:
            self._schedule_memory_after_turn = False
            self.start_memory_indexing()
        self.refresh_busy_state()
