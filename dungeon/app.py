from threading import Thread

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox

from .ai_engine import AIEngineMixin
from .config import BASE_DIR, COLORS, WINDOW_SIZE, WINDOW_TITLE
from .dialogs import DialogMixin
from .memory import count_completed_turns, load_memory_bank, save_memory_bank, sync_memory_bank_after_undo
from .storage import (
    get_world_list,
    load_global_settings,
    load_world_config,
    save_global_settings,
    save_history,
)


class DungeonApp(DialogMixin, AIEngineMixin):
    def __init__(self, root):
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.geometry(WINDOW_SIZE)

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.current_world_path = None
        self.world_name = None
        self.history = []

        settings = load_global_settings()
        self.temperature = settings["temperature"]
        self.max_tokens = settings["max_tokens"]
        self.context_size = settings["context_size"]
        self.summary_interval = settings["summary_interval"]
        self.memory_interval = settings["memory_interval"]
        self.memory_top_k = settings["memory_top_k"]
        self.stream_mode = settings["stream_mode"]
        self.turns_since_summary = 0
        self.turns_since_memory = 0
        self.memory_bank = {"last_indexed_turn": 0, "entries": []}

        self.processing = False
        self.dm_stream_start_index = None
        self.last_sent_prompt = None
        self.memory_indexing = False

        self.create_widgets()
        self.initialize_world()
        self.update_summary_label()
        self.update_memory_label()

    def on_closing(self):
        if self.current_world_path:
            save_history(self.current_world_path, self.history)
        self.root.destroy()

    def save_global_settings(self):
        save_global_settings(
            {
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "context_size": self.context_size,
                "summary_interval": self.summary_interval,
                "memory_interval": self.memory_interval,
                "memory_top_k": self.memory_top_k,
                "stream_mode": self.stream_mode,
            }
        )

    def refresh_world_combobox(self):
        worlds = get_world_list()
        if not worlds:
            worlds = ["Нет миров"]

        self.world_combobox.configure(values=worlds)

        if self.world_name and self.world_name in worlds:
            self.world_var.set(self.world_name)
        elif worlds and worlds[0] != "Нет миров":
            first_world = worlds[0]
            self.world_var.set(first_world)
            self.load_world(first_world)
        else:
            self.world_var.set("Нет миров")

    def on_world_selected(self, selected):
        if selected and selected != "Нет миров" and selected != self.world_name:
            if self.current_world_path:
                save_history(self.current_world_path, self.history)
            self.load_world(selected)

    def create_widgets(self):
        main_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        main_frame.pack(fill=ctk.BOTH, expand=True, padx=15, pady=15)

        title_label = ctk.CTkLabel(
            main_frame,
            text="🐉 AI DUNGEON MASTER 🐉",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=COLORS["accent"],
        )
        title_label.pack(pady=(0, 15))

        info_frame = ctk.CTkFrame(main_frame, height=40)
        info_frame.pack(fill=ctk.X, pady=(0, 10))

        self.world_var = ctk.StringVar()
        self.world_combobox = ctk.CTkOptionMenu(
            info_frame, variable=self.world_var, command=self.on_world_selected, width=200
        )
        self.world_combobox.pack(side=ctk.LEFT, padx=10, pady=5)

        add_world_btn = ctk.CTkButton(info_frame, text="➕", width=30, command=self.create_world_dialog)
        add_world_btn.pack(side=ctk.LEFT, padx=5, pady=5)

        self.status_label = ctk.CTkLabel(info_frame, text="● Готов", text_color=COLORS["player_color"])
        self.status_label.pack(side=ctk.RIGHT, padx=10, pady=5)

        self.summary_label = ctk.CTkLabel(info_frame, text="До суммаризации: -", text_color="gray")
        self.summary_label.pack(side=ctk.RIGHT, padx=10, pady=5)

        self.memory_label = ctk.CTkLabel(info_frame, text="До памяти: -", text_color="gray")
        self.memory_label.pack(side=ctk.RIGHT, padx=10, pady=5)

        top_button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        top_button_frame.pack(fill=ctk.X, pady=(0, 10))

        top_commands = [
            ("📁 Файлы мира", self.open_world_files),
            ("🔄 Миры", self.manage_worlds),
            ("⚙️ Настройки ИИ", self.open_ai_settings),
            ("❌ Выйти", self.quit_app),
        ]
        for text, cmd in top_commands:
            btn = ctk.CTkButton(top_button_frame, text=text, command=cmd, fg_color="transparent", border_width=1)
            btn.pack(side=ctk.LEFT, padx=5)

        self.text_area = ctk.CTkTextbox(main_frame, wrap=tk.WORD, font=ctk.CTkFont(family="Arial", size=14))
        self.text_area.pack(fill=ctk.BOTH, expand=True, pady=(0, 10))

        self.text_area._textbox.tag_config("player", foreground=COLORS["player_color"], font=("Arial", 14, "bold"))
        self.text_area._textbox.tag_config("dm", foreground=COLORS["dm_color"], font=("Arial", 14))
        self.text_area._textbox.tag_config("system", foreground=COLORS["system_color"], font=("Arial", 12, "italic"))
        self.text_area.configure(state="disabled")

        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill=ctk.X, pady=(0, 10))

        btn_args = {"height": 30, "font": ctk.CTkFont(size=12)}
        ctk.CTkButton(
            button_frame,
            text="⏪ Отменить ход",
            command=self.undo_action,
            fg_color=COLORS["danger"],
            hover_color=COLORS["danger_hover"],
            **btn_args,
        ).pack(side=ctk.RIGHT, padx=5)
        ctk.CTkButton(button_frame, text="📝 Суммаризация", command=self.force_summary, **btn_args).pack(
            side=ctk.RIGHT, padx=5
        )
        ctk.CTkButton(button_frame, text="✏️ Изменить", command=self.edit_last_dm_message, **btn_args).pack(
            side=ctk.RIGHT, padx=5
        )
        ctk.CTkButton(button_frame, text="📋 Промпт", command=self.show_last_prompt, **btn_args).pack(
            side=ctk.RIGHT, padx=5
        )
        ctk.CTkButton(button_frame, text="🧠 Память", command=self.show_memory_bank, **btn_args).pack(
            side=ctk.RIGHT, padx=5
        )
        ctk.CTkButton(button_frame, text="🔁 Реролл", command=self.regenerate_action, **btn_args).pack(
            side=ctk.RIGHT, padx=5
        )

        input_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        input_frame.pack(fill=ctk.X)

        self.input_field = ctk.CTkTextbox(input_frame, height=70, wrap=tk.WORD, font=ctk.CTkFont(size=14))
        self.input_field.pack(side=ctk.LEFT, fill=ctk.X, expand=True, padx=(0, 10))
        self.input_field.bind("<Return>", self.handle_input_enter)
        self.input_field.bind("<Button-3>", self.show_context_menu)
        self.input_field.focus()

        self.send_button = ctk.CTkButton(
            input_frame,
            text="▶ Отправить",
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
                else:
                    self.text_area.insert(tk.END, f"\n{msg}\n", "system")
        self.text_area.configure(state="disabled")
        self.text_area.see(tk.END)

    def update_summary_label(self):
        if not self.current_world_path:
            self.summary_label.configure(text="До суммаризации: -")
            return
        remaining = max(0, self.summary_interval - self.turns_since_summary)
        color = COLORS["accent"] if remaining <= 2 else "gray"
        self.summary_label.configure(text=f"До сумм.: {remaining}", text_color=color)

    def update_memory_label(self):
        if not self.current_world_path:
            self.memory_label.configure(text="До памяти: -")
            return
        remaining = max(0, self.memory_interval - self.turns_since_memory)
        color = COLORS["accent"] if remaining <= 1 else "gray"
        entries_count = len(self.memory_bank.get("entries", []))
        self.memory_label.configure(text=f"Память: {entries_count} | до инд.: {remaining}", text_color=color)

    def initialize_world(self):
        worlds = get_world_list()
        if not worlds:
            if messagebox.askyesno("Нет миров", "У вас нет ни одного мира. Создать новый?"):
                self.create_world_dialog()
            else:
                self.add_system_message("Добро пожаловать! Создайте новый мир через кнопку «🔄 Миры».")
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
        _, self.history = load_world_config(world_name)
        self.memory_bank = load_memory_bank(world_path)
        current_turns = count_completed_turns(self.history)
        self.turns_since_memory = current_turns - self.memory_bank.get("last_indexed_turn", 0)

        self.refresh_chat_display()
        self.add_system_message(f"✅ Мир '{world_name}' загружен.")
        self.update_summary_label()
        self.update_memory_label()

        self.refresh_world_combobox()
        self.world_var.set(self.world_name)

    def undo_action(self):
        if self.processing or not self.history or not self.current_world_path:
            return
        self.history.pop()
        if self.turns_since_summary > 0:
            self.turns_since_summary -= 1
        save_history(self.current_world_path, self.history)
        self.memory_bank, self.turns_since_memory = sync_memory_bank_after_undo(self.history, self.memory_bank)
        save_memory_bank(self.current_world_path, self.memory_bank)
        self.refresh_chat_display()
        self.update_summary_label()
        self.update_memory_label()
        self.add_system_message("⏪ Последнее сообщение удалено.")

    def regenerate_action(self):
        if self.processing or not self.history or not self.current_world_path:
            return

        if self.history[-1].startswith("Мастер:"):
            self.history.pop()

        last_player_input = ""
        if self.history and self.history[-1].startswith("Игрок:"):
            last_player_input = self.history[-1][len("Игрок:") :].strip()

        save_history(self.current_world_path, self.history)
        self.refresh_chat_display()

        self.processing = True
        self.send_button.configure(state="disabled", text="⏳ Думаю...")
        self.status_label.configure(text="● Generation...", text_color=COLORS["system_color"])
        Thread(target=self.process_action, args=(last_player_input,), daemon=True).start()

    def send_action(self):
        if self.processing or not self.current_world_path:
            return
        user_input = self.input_field.get("1.0", tk.END).strip()
        self.input_field.delete("1.0", tk.END)

        if user_input:
            self.add_player_message(user_input)

        self.turns_since_summary += 1
        self.turns_since_memory += 1
        self.update_summary_label()
        self.update_memory_label()
        self.processing = True
        self.send_button.configure(state="disabled", text="⏳ Думаю...")
        self.status_label.configure(text="● Generation...", text_color=COLORS["system_color"])
        Thread(target=self.process_action, args=(user_input,), daemon=True).start()

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

    def processing_end(self):
        self.processing = False
        self.send_button.configure(state="normal", text="▶ Отправить")
        self.status_label.configure(text="● Готов", text_color=COLORS["player_color"])
        self.input_field.focus()

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
        menu.add_command(label="Копировать", command=lambda: event.widget.event_generate("<<Copy>>"))
        menu.add_command(label="Вставить", command=lambda: event.widget.event_generate("<<Paste>>"))
        menu.add_command(label="Вырезать", command=lambda: event.widget.event_generate("<<Cut>>"))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
