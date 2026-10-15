import tkinter as tk

from .config import COLORS

from .i18n import (
    dm_text,
    intro_text,
    is_dm_msg,
    is_intro_msg,
    is_player_msg,
    player_text,
)

class ChatMixin:
    def handle_text_shortcut(self, event):
        """Обрабатывает Ctrl-сочетания по физическому коду клавиши."""
        key_commands = {
            65: "select_all",
            67: "copy",
            86: "paste",
            88: "cut",
        }
        command = key_commands.get(event.keycode)
        if command is None:
            return

        target = event.widget._textbox if hasattr(event.widget, "_textbox") else event.widget
        if command == "select_all":
            self.select_all_text(target)
        elif command == "copy":
            self.copy_selected_text(target)
        else:
            virtual_event = {"paste": "<<Paste>>", "cut": "<<Cut>>"}[command]
            target.event_generate(virtual_event)
        return "break"

    def copy_selected_text(self, target):
        try:
            selected_text = target.selection_get()
        except tk.TclError:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(selected_text)

    def select_all_text(self, target):
        target.tag_add(tk.SEL, "1.0", "end-1c")
        target.mark_set(tk.INSERT, "1.0")
        target.see(tk.INSERT)

    def refresh_chat_display(self):
        self.text_area.configure(state="normal")
        self.text_area.delete("1.0", tk.END)
        if self.history:
            for msg in self.history:
                if is_player_msg(msg):
                    text = player_text(msg)
                    if text:
                        self.text_area.insert(tk.END, f"\n🎮 {text}\n", "player")
                elif is_dm_msg(msg):
                    self.text_area.insert(tk.END, f"\n📜 {dm_text(msg)}\n", "dm")
                elif is_intro_msg(msg):
                    self.text_area.insert(tk.END, f"\n📖 {intro_text(msg)}\n", "intro")
                else:
                    self.text_area.insert(tk.END, f"\n{msg}\n", "system")
        self.text_area.configure(state="disabled")
        self.text_area.see(tk.END)

    def start_dm_stream(self):
        self.text_area.configure(state="normal")
        self.text_area.insert(tk.END, f"\n{self.tr('hist.dm')} ", "dm")
        self.stream_start_index = self.text_area.index("end-1c")
        self.text_area.configure(state="disabled")
        self.text_area.see(tk.END)

    def append_to_dm_stream(self, chunk):
        self.text_area.configure(state="normal")
        self.text_area.insert(tk.END, chunk, "dm")
        self.text_area.configure(state="disabled")
        self.text_area.see(tk.END)

    def abort_dm_stream(self):
        """Убирает заголовок Мастера, если ответ не удалось получить."""
        self.text_area.configure(state="normal")
        if self.stream_start_index:
            self.text_area.delete(self.stream_start_index, tk.END)
            self.stream_start_index = None
        self.text_area.configure(state="disabled")
        self.text_area.see(tk.END)

    def finalize_dm_stream(self, final_text):
        self.text_area.configure(state="normal")
        if self.stream_start_index:
            self.text_area.delete(self.stream_start_index, tk.END)
        self.text_area.insert(tk.END, f"{final_text}\n", "dm")
        self.text_area.configure(state="disabled")
        self.stream_start_index = None
        self.text_area.see(tk.END)

    def is_busy(self):
        return (
            self.processing or self.memory_indexing or self.summary_indexing or self.scene_prompt_running
        )

    def refresh_busy_state(self):
        if self.processing:
            status_text = self.tr("status.generating")
            lock_input = True
        elif self.summary_indexing and self.memory_indexing:
            status_text = self.tr("status.summary_memory")
            lock_input = False
        elif self.summary_indexing:
            status_text = self.tr("status.summary")
            lock_input = False
        elif self.memory_indexing:
            status_text = self.tr("status.memory")
            lock_input = False
        elif self.scene_prompt_running:
            status_text = self.tr("status.scene_prompt")
            lock_input = False
        else:
            self.send_button.configure(
                state="normal",
                text=self.tr("btn.send"),
                fg_color=COLORS["accent"],
                hover_color=COLORS["button_hover"],
                text_color="black",
            )
            self.input_field.configure(state="normal")
            self.status_label.configure(text=self.tr("ready"), text_color=COLORS["player_color"])
            self.input_field.focus()
            return

        # Во время генерации та же кнопка служит остановкой
        self.send_button.configure(
            state="normal",
            text=self.tr("btn.stop"),
            fg_color=COLORS["danger"],
            hover_color=COLORS["danger_hover"],
            text_color="white",
        )
        if lock_input:
            self.input_field.configure(state="disabled")
        else:
            self.input_field.configure(state="normal")
        self.status_label.configure(text=status_text, text_color=COLORS["system_color"])

    def processing_end(self):
        self.processing = False
        self.refresh_busy_state()

    def add_system_message(self, message):
        self.text_area.configure(state="normal")
        self.text_area.insert(tk.END, f"\n{message}\n", "system")
        self.text_area.configure(state="disabled")
        self.text_area.see(tk.END)

    def add_player_message(self, message):
        self.text_area.configure(state="normal")
        self.text_area.insert(tk.END, f"\n🎮 {message}\n", "player")
        self.text_area.configure(state="disabled")
        self.text_area.see(tk.END)

    def show_context_menu(self, event):
        menu = tk.Menu(self.root, tearoff=0)
        target = event.widget._textbox if hasattr(event.widget, "_textbox") else event.widget
        menu.add_command(label=self.tr("menu.select_all"), command=lambda: self.select_all_text(target))
        menu.add_command(label=self.tr("menu.copy"), command=lambda: self.copy_selected_text(target))
        menu.add_command(label=self.tr("menu.paste"), command=lambda: target.event_generate("<<Paste>>"))
        menu.add_command(label=self.tr("menu.cut"), command=lambda: target.event_generate("<<Cut>>"))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
