from threading import Thread

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox

from .ai_engine import AIEngineMixin
from .config import BASE_DIR, COLORS, INTRODUCTION_FILE, WINDOW_SIZE
from .dialogs import DialogMixin
from .i18n import (
    DM_PREFIX,
    INTRO_PREFIX,
    PLAYER_PREFIX,
    dm_text,
    intro_text,
    is_dm_msg,
    is_intro_msg,
    is_player_msg,
    normalize_lang,
    player_text,
    t,
)
from .memory import count_completed_turns, load_memory_bank, save_memory_bank, sync_memory_bank_after_undo
from .story_cards import load_story_cards
from .storage import (
    ensure_introduction_in_history,
    format_introduction_history,
    get_world_list,
    load_global_settings,
    load_world_config,
    save_global_settings,
    save_history,
)


class DungeonApp(DialogMixin, AIEngineMixin):
    def __init__(self, root):
        self.root = root
        settings = load_global_settings()
        self.language = normalize_lang(settings.get("language", "ru"))
        self.root.title(t(self.language, "window_title"))
        self.root.geometry(WINDOW_SIZE)

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.current_world_path = None
        self.world_name = None
        self.history = []

        self.api_url = settings["api_url"]
        self.api_key = settings.get("api_key", "")
        self.model = settings.get("model", "")
        self.active_api_preset = settings.get("active_api_preset", "")
        self.api_presets = settings.get("api_presets", [])
        self.temperature = settings["temperature"]
        self.max_tokens = settings["max_tokens"]
        self.context_size = settings["context_size"]
        self.summary_interval = settings["summary_interval"]
        self.memory_interval = settings["memory_interval"]
        self.memory_top_k = settings["memory_top_k"]
        self.stream_mode = settings["stream_mode"]
        self.summary_enabled = settings.get("summary_enabled", True)
        self.memory_enabled = settings.get("memory_enabled", True)
        self.turns_since_summary = 0
        self.turns_since_memory = 0
        self.memory_bank = {"last_indexed_turn": 0, "entries": []}
        self.story_cards = {"cards": []}

        self.processing = False
        self.dm_stream_start_index = None
        self.last_sent_prompt = None
        self.memory_indexing = False
        self.summary_indexing = False
        self._schedule_summary_after_turn = False
        self._schedule_memory_after_turn = False

        self.create_widgets()
        self.initialize_world()
        self.update_toggle_buttons()
        self.update_summary_label()
        self.update_memory_label()

    def on_closing(self):
        if self.current_world_path:
            save_history(self.current_world_path, self.history)
        self.root.destroy()

    def tr(self, key, **kwargs):
        return t(self.language, key, **kwargs)

    def world_file_label(self, fname):
        if fname == STORY_CARDS_KEY:
            return self.tr("world_file.story_cards")
        return self.tr(f"world_file.{fname}")

    def on_language_selected(self, value):
        new_lang = "en" if str(value).upper().startswith("EN") else "ru"
        if new_lang == self.language:
            return
        self.language = new_lang
        self.save_global_settings()
        self.apply_language()
        self.add_system_message(self.tr("msg.language_changed", lang_name=self.tr(f"lang.{new_lang}")))

    def apply_language(self):
        self.root.title(self.tr("window_title"))
        if hasattr(self, "title_label"):
            self.title_label.configure(text=self.tr("app_title"))
        if hasattr(self, "lang_var"):
            self.lang_var.set("EN" if self.language == "en" else "RU")
        for btn, key in getattr(self, "top_command_buttons", []):
            btn.configure(text=self.tr(key))
        for btn, key in getattr(self, "action_buttons", []):
            btn.configure(text=self.tr(key))
        if hasattr(self, "send_button"):
            self.send_button.configure(text=self.tr("btn.send"))
        if hasattr(self, "update_toggle_buttons"):
            self.update_toggle_buttons()
        if hasattr(self, "update_summary_label"):
            self.update_summary_label()
        if hasattr(self, "update_memory_label"):
            self.update_memory_label()
        if hasattr(self, "refresh_busy_state"):
            self.refresh_busy_state()
        if hasattr(self, "refresh_world_combobox"):
            self.refresh_world_combobox()

    def save_global_settings(self):
        save_global_settings(
            {
                "api_url": self.api_url,
                "api_key": self.api_key,
                "model": self.model,
                "active_api_preset": self.active_api_preset,
                "api_presets": self.api_presets,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "context_size": self.context_size,
                "summary_interval": self.summary_interval,
                "memory_interval": self.memory_interval,
                "memory_top_k": self.memory_top_k,
                "stream_mode": self.stream_mode,
                "summary_enabled": self.summary_enabled,
                "memory_enabled": self.memory_enabled,
                "language": self.language,
            }
        )

    def refresh_world_combobox(self):
        worlds = get_world_list()
        if not worlds:
            worlds = [self.tr("no_worlds")]

        self.world_combobox.configure(values=worlds)

        if self.world_name and self.world_name in worlds:
            self.world_var.set(self.world_name)
        elif worlds and worlds[0] != self.tr("no_worlds"):
            first_world = worlds[0]
            self.world_var.set(first_world)
            self.load_world(first_world)
        else:
            self.world_var.set(self.tr("no_worlds"))

    def on_world_selected(self, selected):
        if selected and selected != self.tr("no_worlds") and selected != self.world_name:
            if self.current_world_path:
                save_history(self.current_world_path, self.history)
            self.load_world(selected)

    def create_widgets(self):
        main_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        main_frame.pack(fill=ctk.BOTH, expand=True, padx=15, pady=15)

        title_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        title_frame.pack(pady=(0, 15))

        self.lang_var = ctk.StringVar(value="EN" if self.language == "en" else "RU")
        self.language_menu = ctk.CTkOptionMenu(
            title_frame,
            variable=self.lang_var,
            values=["RU", "EN"],
            command=self.on_language_selected,
            width=80,
        )
        self.language_menu.pack(side=ctk.RIGHT, padx=(10, 0))

        self.title_label = ctk.CTkLabel(
            title_frame,
            text=self.tr("app_title"),
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=COLORS["accent"],
        )
        self.title_label.pack(side=ctk.LEFT)

        info_frame = ctk.CTkFrame(main_frame, height=40)
        info_frame.pack(fill=ctk.X, pady=(0, 10))

        self.world_var = ctk.StringVar()
        self.world_combobox = ctk.CTkOptionMenu(
            info_frame, variable=self.world_var, command=self.on_world_selected, width=200
        )
        self.world_combobox.pack(side=ctk.LEFT, padx=10, pady=5)

        add_world_btn = ctk.CTkButton(info_frame, text="➕", width=30, command=self.create_world_dialog)
        add_world_btn.pack(side=ctk.LEFT, padx=5, pady=5)

        self.status_label = ctk.CTkLabel(info_frame, text=self.tr("ready"), text_color=COLORS["player_color"])
        self.status_label.pack(side=ctk.RIGHT, padx=10, pady=5)

        self.summary_toggle_btn = ctk.CTkButton(
            info_frame,
            text="",
            width=105,
            height=28,
            command=self.toggle_summary,
            font=ctk.CTkFont(size=11),
        )
        self.summary_toggle_btn.pack(side=ctk.RIGHT, padx=5, pady=5)

        self.summary_label = ctk.CTkLabel(info_frame, text=self.tr("summary_until"), text_color="gray")
        self.summary_label.pack(side=ctk.RIGHT, padx=5, pady=5)

        self.memory_toggle_btn = ctk.CTkButton(
            info_frame,
            text="",
            width=115,
            height=28,
            command=self.toggle_memory,
            font=ctk.CTkFont(size=11),
        )
        self.memory_toggle_btn.pack(side=ctk.RIGHT, padx=5, pady=5)

        self.memory_label = ctk.CTkLabel(info_frame, text=self.tr("memory_until"), text_color="gray")
        self.memory_label.pack(side=ctk.RIGHT, padx=5, pady=5)

        top_button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        top_button_frame.pack(fill=ctk.X, pady=(0, 10))

        self.top_command_buttons = []
        top_commands = [
            ("btn.world_files", self.open_world_files),
            ("btn.cards", self.open_story_cards_editor),
            ("btn.worlds", self.manage_worlds),
            ("btn.ai_settings", self.open_ai_settings),
            ("btn.quit", self.quit_app),
        ]
        for key, cmd in top_commands:
            btn = ctk.CTkButton(top_button_frame, text=self.tr(key), command=cmd, fg_color="transparent", border_width=1)
            btn.pack(side=ctk.LEFT, padx=5)
            self.top_command_buttons.append((btn, key))

        self.text_area = ctk.CTkTextbox(main_frame, wrap=tk.WORD, font=ctk.CTkFont(family="Arial", size=14))
        self.text_area.pack(fill=ctk.BOTH, expand=True, pady=(0, 10))
        self.text_area.bind("<Button-3>", self.show_context_menu)
        self.text_area.bind("<Control-KeyPress>", self.handle_text_shortcut)

        self.text_area._textbox.tag_config("player", foreground=COLORS["player_color"], font=("Arial", 14, "bold"))
        self.text_area._textbox.tag_config("dm", foreground=COLORS["dm_color"], font=("Arial", 14))
        self.text_area._textbox.tag_config("intro", foreground=COLORS["accent"], font=("Arial", 14, "italic"))
        self.text_area._textbox.tag_config("system", foreground=COLORS["system_color"], font=("Arial", 12, "italic"))
        self.text_area.configure(state="disabled")

        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill=ctk.X, pady=(0, 10))

        btn_args = {"height": 28, "font": ctk.CTkFont(size=11)}
        row1 = ctk.CTkFrame(button_frame, fg_color="transparent")
        row1.pack(fill=ctk.X, pady=(0, 4))
        row2 = ctk.CTkFrame(button_frame, fg_color="transparent")
        row2.pack(fill=ctk.X)

        self.action_buttons = []
        row1_commands = [
            ("btn.next", self.prompt_next_turn),
            ("btn.reroll", self.regenerate_action),
            ("btn.edit", self.edit_last_dm_message),
            ("btn.prompt", self.show_last_prompt),
        ]
        row2_commands = [
            ("btn.summary", self.force_summary),
            ("btn.memory", self.show_memory_bank),
            ("btn.undo", self.undo_action),
        ]

        for key, cmd in row1_commands:
            btn = ctk.CTkButton(row1, text=self.tr(key), command=cmd, **btn_args)
            btn.pack(side=ctk.LEFT, padx=3, expand=True, fill=ctk.X)
            self.action_buttons.append((btn, key))

        for key, cmd in row2_commands:
            btn_kwargs = dict(btn_args)
            if cmd == self.undo_action:
                btn_kwargs.update(fg_color=COLORS["danger"], hover_color=COLORS["danger_hover"])
            btn = ctk.CTkButton(row2, text=self.tr(key), command=cmd, **btn_kwargs)
            btn.pack(side=ctk.LEFT, padx=3, expand=True, fill=tk.X)
            self.action_buttons.append((btn, key))

        input_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        input_frame.pack(fill=ctk.X)

        self.input_field = ctk.CTkTextbox(input_frame, height=70, wrap=tk.WORD, font=ctk.CTkFont(size=14))
        self.input_field.pack(side=ctk.LEFT, fill=ctk.X, expand=True, padx=(0, 10))
        self.input_field.bind("<Return>", self.handle_input_enter)
        self.input_field.bind("<Button-3>", self.show_context_menu)
        self.input_field.bind("<Control-KeyPress>", self.handle_text_shortcut)
        self.input_field.focus()

        self.send_button = ctk.CTkButton(
            input_frame,
            text=self.tr("btn.send"),
            command=self.send_action,
            fg_color=COLORS["accent"],
            hover_color=COLORS["button_hover"],
            text_color="black",
            font=ctk.CTkFont(weight="bold"),
            width=120,
            height=70,
        )
        self.send_button.pack(side=ctk.RIGHT)

    def handle_input_enter(self, event):
        if event.state & 0x1:
            return
        self.send_action()
        return "break"

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
                if msg.startswith("Игрок:"):
                    player_text = msg[len("Игрок:") :].strip()
                    if player_text:
                        self.text_area.insert(tk.END, f"\n🎮 {player_text}\n", "player")
                elif msg.startswith("Мастер:"):
                    dm_text = msg[len("Мастер:") :].strip()
                    self.text_area.insert(tk.END, f"\n📜 {dm_text}\n", "dm")
                elif msg.startswith(INTRODUCTION_PREFIX):
                    intro_text = msg[len(INTRODUCTION_PREFIX) :].strip()
                    self.text_area.insert(tk.END, f"\n📖 {intro_text}\n", "intro")
                else:
                    self.text_area.insert(tk.END, f"\n{msg}\n", "system")
        self.text_area.configure(state="disabled")
        self.text_area.see(tk.END)

    def update_toggle_buttons(self):
        if self.summary_enabled:
            self.summary_toggle_btn.configure(
                text=self.tr("toggle.summary_on"),
                fg_color=COLORS["player_color"],
                hover_color=COLORS["player_color"],
            )
        else:
            self.summary_toggle_btn.configure(text=self.tr("toggle.summary_off"), fg_color="gray40", hover_color="gray50")

        if self.memory_enabled:
            self.memory_toggle_btn.configure(
                text=self.tr("toggle.memory_on"),
                fg_color=COLORS["player_color"],
                hover_color=COLORS["player_color"],
            )
        else:
            self.memory_toggle_btn.configure(text=self.tr("toggle.memory_off"), fg_color="gray40", hover_color="gray50")

    def toggle_summary(self):
        self.summary_enabled = not self.summary_enabled
        self.save_global_settings()
        self.update_toggle_buttons()
        self.update_summary_label()
        state = self.tr("summary_enabled_word" if self.summary_enabled else "summary_disabled_word")
        self.add_system_message(self.tr("msg.summary_toggled", state=state))

    def toggle_memory(self):
        self.memory_enabled = not self.memory_enabled
        self.save_global_settings()
        self.update_toggle_buttons()
        self.update_memory_label()
        state = self.tr("memory_enabled_word" if self.memory_enabled else "memory_disabled_word")
        self.add_system_message(self.tr("msg.memory_toggled", state=state))

    def update_summary_label(self):
        if not self.current_world_path:
            self.summary_label.configure(text=self.tr("summary_until"))
            return
        if not self.summary_enabled:
            self.summary_label.configure(text=self.tr("summary.off"), text_color="gray")
            return
        remaining = max(0, self.summary_interval - self.turns_since_summary)
        color = COLORS["accent"] if remaining <= 2 else "gray"
        self.summary_label.configure(text=self.tr("summary.until", n=remaining), text_color=color)

    def update_memory_label(self):
        if not self.current_world_path:
            self.memory_label.configure(text=self.tr("memory_until"))
            return
        if not self.memory_enabled:
            entries_count = len(self.memory_bank.get("entries", []))
            self.memory_label.configure(text=self.tr("memory.off", n=entries_count), text_color="gray")
            return
        remaining = max(0, self.memory_interval - self.turns_since_memory)
        color = COLORS["accent"] if remaining <= 1 else "gray"
        entries_count = len(self.memory_bank.get("entries", []))
        self.memory_label.configure(text=self.tr("memory.until", n=entries_count, remaining=remaining), text_color=color)

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

        self.current_world_path = world_path
        self.world_name = world_name
        self.turns_since_summary = 0
        self.last_sent_prompt = None
        _, loaded_history = load_world_config(world_name)
        self.history = ensure_introduction_in_history(world_path, loaded_history)
        if self.history != loaded_history:
            save_history(world_path, self.history)
        self.memory_bank = load_memory_bank(world_path)
        self.story_cards = load_story_cards(world_path)
        current_turns = count_completed_turns(self.history)
        self.turns_since_memory = current_turns - self.memory_bank.get("last_indexed_turn", 0)

        self.refresh_chat_display()
        self.add_system_message(self.tr("msg.world_loaded", name=world_name))
        self.update_summary_label()
        self.update_memory_label()

        self.refresh_world_combobox()
        self.world_var.set(self.world_name)

    def undo_action(self):
        if self.is_busy() or not self.history or not self.current_world_path:
            return
        self.history.pop()
        if self.summary_enabled and self.turns_since_summary > 0:
            self.turns_since_summary -= 1
        save_history(self.current_world_path, self.history)
        self.memory_bank, self.turns_since_memory = sync_memory_bank_after_undo(self.history, self.memory_bank)
        save_memory_bank(self.current_world_path, self.memory_bank)
        self.refresh_chat_display()
        self.update_summary_label()
        self.update_memory_label()
        self.add_system_message(self.tr("msg.undone"))

    def regenerate_action(self):
        if self.is_busy() or not self.history or not self.current_world_path:
            return

        if self.history[-1].startswith("Мастер:"):
            self.history.pop()

        last_player_input = ""
        if self.history and self.history[-1].startswith("Игрок:"):
            last_player_input = self.history[-1][len("Игрок:") :].strip()

        save_history(self.current_world_path, self.history)
        self.refresh_chat_display()

        self.processing = True
        self.refresh_busy_state()
        Thread(target=self.process_action, args=(last_player_input,), daemon=True).start()

    def send_action(self):
        if self.is_busy() or not self.current_world_path:
            return
        user_input = self.input_field.get("1.0", tk.END).strip()
        self.input_field.delete("1.0", tk.END)

        if user_input:
            self.add_player_message(user_input)

        self._dispatch_turn(self.process_action, (user_input,))

    def _dispatch_turn(self, target, args=(), kwargs=None):
        kwargs = kwargs or {}
        if self.summary_enabled:
            self.turns_since_summary += 1
        if self.memory_enabled:
            self.turns_since_memory += 1
        if self.summary_enabled:
            self.update_summary_label()
        if self.memory_enabled:
            self.update_memory_label()
        self.processing = True
        self.refresh_busy_state()
        Thread(target=target, args=args, kwargs=kwargs, daemon=True).start()

    def sync_introduction_to_history(self, intro_text):
        intro_msg = format_introduction_history(intro_text)
        if self.history and self.history[0].startswith(INTRODUCTION_PREFIX):
            if intro_msg:
                self.history[0] = intro_msg
            else:
                self.history.pop(0)
        elif intro_msg:
            self.history.insert(0, intro_msg)
        save_history(self.current_world_path, self.history)
        self.refresh_chat_display()

    def start_dm_stream(self):
        self.text_area.configure(state="normal")
        self.text_area.insert(tk.END, "\nМастер: ", "dm")
        self.stream_start_index = self.text_area.index("end-1c")
        self.text_area.configure(state="disabled")
        self.text_area.see(tk.END)

    def append_to_dm_stream(self, chunk):
        self.text_area.configure(state="normal")
        self.text_area.insert(tk.END, chunk, "dm")
        self.text_area.configure(state="disabled")
        self.text_area.see(tk.END)

    def finalize_dm_stream(self, final_text):
        self.text_area.configure(state="normal")
        if hasattr(self, "stream_start_index"):
            self.text_area.delete(self.stream_start_index, tk.END)
        self.text_area.insert(tk.END, f"{final_text}\n", "dm")
        self.text_area.configure(state="disabled")
        self.text_area.see(tk.END)

    def is_busy(self):
        return self.processing or self.memory_indexing or self.summary_indexing

    def refresh_busy_state(self):
        if self.processing:
            btn_text = self.tr("busy.thinking")
            status_text = self.tr("status.generating")
            lock_input = True
        elif self.summary_indexing and self.memory_indexing:
            btn_text = self.tr("busy.background")
            status_text = self.tr("status.summary_memory")
            lock_input = False
        elif self.summary_indexing:
            btn_text = self.tr("busy.summary")
            status_text = self.tr("status.summary")
            lock_input = False
        elif self.memory_indexing:
            btn_text = self.tr("busy.memory")
            status_text = self.tr("status.memory")
            lock_input = False
        else:
            self.send_button.configure(state="normal", text=self.tr("btn.send"))
            self.input_field.configure(state="normal")
            self.status_label.configure(text=self.tr("ready"), text_color=COLORS["player_color"])
            self.input_field.focus()
            return

        self.send_button.configure(state="disabled", text=btn_text)
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
