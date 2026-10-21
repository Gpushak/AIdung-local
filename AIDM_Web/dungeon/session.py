from threading import Thread

import tkinter as tk

from tkinter import messagebox

from .ai_engine import ACTION

from .config import BASE_DIR

from .i18n import (
    INTRO_PREFIX,
    intro_text,
    is_dm_msg,
    is_player_msg,
    player_text,
)

from .memory import (
    count_completed_turns,
    load_memory_bank,
    save_memory_bank,
    sync_memory_bank_after_undo,
)

from .story_cards import load_story_cards

from .storage import (
    CorruptedDataError,
    clamp_summary_cursor,
    default_summary_cursor,
    ensure_introduction_in_history,
    format_introduction_history,
    get_world_list,
    load_world_config,
    read_summary_cursor,
    save_history,
    save_summary_cursor,
)

class SharedTurnMixin:
    """Общие для окна и браузера шаги хода и границы суммаризации."""

    def _introduction_cursor_delta(self, before, after):
        """Сдвиг границы, если вступление вставили или убрали в начале истории."""
        if len(after) == len(before) + 1 and after and after[0].startswith(INTRO_PREFIX):
            return 1
        if len(before) == len(after) + 1 and before and before[0].startswith(INTRO_PREFIX):
            return -1
        return 0

    def _load_summary_cursor(self, raw_history):
        intro_delta = self._introduction_cursor_delta(raw_history, self.history)
        stored = read_summary_cursor(self.current_world_path)
        if stored is None:
            self.covered_count = default_summary_cursor(self.current_world_path, len(self.history))
        else:
            if stored > 0:
                stored += intro_delta
            self.covered_count = clamp_summary_cursor(stored, len(self.history))
        save_summary_cursor(self.current_world_path, self.covered_count)

    def note_history_revised(self, index):
        """Правка уже сжатой реплики снимает отметку с неё и со всего, что после.

        Саммари описывает старый текст, а граница — это префикс. Откатить её
        к изменённому сообщению, иначе новый текст так и останется «покрытым».
        """
        if index < self.covered_count:
            self.covered_count = max(0, int(index))
            if self.current_world_path:
                save_summary_cursor(self.current_world_path, self.covered_count)

    def _dispatch_turn(self, target, args=(), kwargs=None):
        kwargs = kwargs or {}
        if self.memory_enabled:
            self.turns_since_memory += 1
            self.update_memory_label()
        self.begin_action_turn()
        Thread(target=target, args=args, kwargs=kwargs, daemon=True).start()


class SessionMixin(SharedTurnMixin):
    def handle_input_enter(self, event):
        if event.state & 0x1:
            return
        self.send_action()
        return "break"

    def initialize_world(self):
        worlds = get_world_list()
        if not worlds:
            if messagebox.askyesno(self.tr("dialog.no_worlds_title"), self.tr("dialog.no_worlds_q")):
                self.create_world_dialog()
            else:
                self.add_system_message(self.tr("msg.welcome"))
        else:
            self.load_world(worlds[0])

    def load_world(self, world_name):
        world_path = BASE_DIR / world_name
        if not world_path.exists():
            return

        # Сначала читаем и проверяем данные, и только потом меняем состояние:
        # при повреждённом файле текущий мир должен остаться нетронутым.
        try:
            _, loaded_history, restored = load_world_config(world_name)
        except CorruptedDataError as e:
            messagebox.showerror(
                self.tr("dialog.corrupt_title"),
                self.tr("dialog.corrupt_history", name=world_name, file=e.path.name, detail=e.detail),
            )
            return

        self.current_world_path = world_path
        self.world_name = world_name
        self.last_sent_prompt = None
        self.history = ensure_introduction_in_history(world_path, loaded_history)
        if self.history != loaded_history:
            save_history(world_path, self.history)
        self._load_summary_cursor(loaded_history)
        self.memory_bank = load_memory_bank(world_path)
        self.story_cards = load_story_cards(world_path)
        current_turns = count_completed_turns(self.history)
        self.turns_since_memory = current_turns - self.memory_bank.get("last_indexed_turn", 0)

        self.refresh_chat_display()
        if restored:
            self.add_system_message(self.tr("msg.history_restored"))
        self.add_system_message(self.tr("msg.world_loaded", name=world_name))
        self.update_memory_label()
        self.update_context_indicator()

        self.refresh_world_combobox()
        self.world_var.set(self.world_name)

    def undo_action(self):
        if self.is_busy() or not self.history or not self.current_world_path:
            return
        self.history.pop()
        self.covered_count = clamp_summary_cursor(self.covered_count, len(self.history))
        save_history(self.current_world_path, self.history)
        save_summary_cursor(self.current_world_path, self.covered_count)
        self.memory_bank, self.turns_since_memory = sync_memory_bank_after_undo(self.history, self.memory_bank)
        save_memory_bank(self.current_world_path, self.memory_bank)
        self.refresh_chat_display()
        self.update_context_indicator()
        self.update_memory_label()
        self.add_system_message(self.tr("msg.undone"))

    def rewind_last_reply(self):
        """Убирает последний ответ мастера и не считает новый ответ уже сжатым.

        Если граница стояла на конце истории, удалённый ответ выпадает из
        покрытого префикса. Иначе следующий ответ занял бы его место и
        больше никогда не попал бы в хронику.
        """
        if self.history and is_dm_msg(self.history[-1]):
            self.history.pop()
        self.covered_count = clamp_summary_cursor(self.covered_count, len(self.history))
        if self.current_world_path:
            save_summary_cursor(self.current_world_path, self.covered_count)
        if self.history and is_player_msg(self.history[-1]):
            return player_text(self.history[-1])
        return ""

    def regenerate_action(self):
        if self.is_busy() or not self.history or not self.current_world_path:
            return

        last_player_input = self.rewind_last_reply()
        save_history(self.current_world_path, self.history)
        self.refresh_chat_display()
        self.update_context_indicator()

        self.begin_action_turn()
        Thread(target=self.process_action, args=(last_player_input,), daemon=True).start()

    def begin_action_turn(self):
        """Отмечает ход как выполняющийся и выдаёт ему свежий флаг отмены."""
        self.processing = True
        self._begin_operation(ACTION)
        self.refresh_busy_state()

    def on_send_or_stop(self):
        """Кнопка отправки: во время генерации она работает как «Стоп»."""
        if self.is_busy():
            self.request_stop_generation()
        else:
            self.send_action()

    def request_stop_generation(self):
        stopped = self.request_stop()
        if stopped:
            self.add_system_message(self.tr("msg.stop_requested"))
            self.refresh_busy_state()

    def handle_escape(self, event=None):
        if self.is_busy():
            self.request_stop_generation()
            return "break"

    def send_action(self):
        if self.is_busy() or not self.current_world_path:
            return
        user_input = self.input_field.get("1.0", tk.END).strip()
        self.input_field.delete("1.0", tk.END)

        if user_input:
            self.add_player_message(user_input)

        self._dispatch_turn(self.process_action, (user_input,))

    def sync_introduction_to_history(self, intro_text):
        before = list(self.history)
        intro_msg = format_introduction_history(intro_text)
        if self.history and self.history[0].startswith(INTRO_PREFIX):
            if intro_msg:
                self.history[0] = intro_msg
            else:
                self.history.pop(0)
        elif intro_msg:
            self.history.insert(0, intro_msg)
        delta = self._introduction_cursor_delta(before, self.history)
        if self.covered_count > 0 and delta:
            self.covered_count += delta
        self.covered_count = clamp_summary_cursor(self.covered_count, len(self.history))
        save_history(self.current_world_path, self.history)
        if self.current_world_path:
            save_summary_cursor(self.current_world_path, self.covered_count)
        self.refresh_chat_display()
        self.update_context_indicator()

