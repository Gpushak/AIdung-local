#!/usr/bin/env python3

# Возможные дополнения: 
# Система "Банк памяти"- ИИ каждые 5 сообщений делает супер краткий пересказ событий и действий за последние 5 сообщений и отправялет это в банк памяти вместе с ключем/ключами для того, чтобы ИИ сам мог подтянуть нужный фрагмент истории по необходимости.
import os
import sys
import json
import re
import requests
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from pathlib import Path
from threading import Thread
import shutil
from datetime import datetime
import codecs

# ======== ИНИЦИАЛИЗАЦИЯ ТОКЕНИЗАТОРА (tiktoken) ========
try:
    import tiktoken
    TOKENIZER = tiktoken.get_encoding("cl100k_base")
except ImportError:
    TOKENIZER = None

def count_tokens(text: str) -> int:
    """Возвращает количество токенов с поправкой на современные локальные модели."""
    if TOKENIZER:
        return int(len(TOKENIZER.encode(text)) / 1.65)
    return int(len(text) / 3.5)

# ======== НАСТРОЙКИ ========
API_URL = "http://localhost:1234/v1/chat/completions"
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent / "worlds"
else:
    BASE_DIR = Path(__file__).parent / "worlds"
SETTINGS_FILE = BASE_DIR / "settings.json"

WORLD_FILES = {
    "ai_instructions.txt": "Инструкции ИИ",
    "plot_basics.txt": "Основы сюжета",
    "author_notes.txt": "Авторские пометки",
    "characters.txt": "Персонажи",
    "summary.txt": "Краткое содержание"
}

COLORS = {
    'accent': '#e6b450',
    'player_color': '#8bc34a',
    'dm_color': "#DBBA5F", # цвет текста чата
    'system_color': '#61afef',
    'button_hover': '#d4a340',
    'danger': '#d9534f',
    'danger_hover': '#c9302c',
    'listbox_bg': '#2b2b2b',
    'listbox_sel': '#3a3a3a'
}

DEFAULT_TEMPLATES = {
    "ai_instructions.txt": """Ты - ИИ мастер, который предоставляет любой контент для ролевых игр.
Инструкции, которые ты (Мастер) обязан соблюдать при написании:
- '!!' Двигай сюжет, не зацикливайся на одной сцене.
- '!' Отдавайте предпочтение действиям и диалогам, а не описаниям. 
- '!' Не описывайте окружающую обстановку, освещение, погоду, звуки или жестикуляцию персонажей, если это напрямую не влияет на текущее действие.
- '!' Избегайте повторяющегося эмоционального повествования.
- '!' Пишите скорее как сценарий фильма, чем как роман.
- Будьте конкретны, описательны и изобретательны.
- Избегайте повторений и обобщений.
- Старайтесь развивать историю, даже если пользователь бездействует.
- Обычно говорите от второго лица (например, "О смотрит на вас"). Но используйте слова от третьего лица, если вам кажется, что история развивается именно так.
- Никогда не принимайте решения и не пишите за пользователя. Если ввод заканчивается на середине предложения, продолжайте с того места, где он был прерван.
- Подробно опишите внешность и характерные черты персонажей.
""",
    "plot_basics.txt": "Мир фэнтези.\nВы искатель приключений.\nУ вас есть меч и щит.\nВы носите легкую кожаную броню.",
    "author_notes.txt": "Стиль написания: Приключение, комедия, фэнтези.",
    "characters.txt": "Главный герой:\n- Имя: Арион\n- Класс: Воин\n- Оружие: Длинный меч и щит\n- Навыки: Атлетика, Выживание",
    "summary.txt": ""
}

# ======== ФУНКЦИИ ДЛЯ МИРОВ ========
def get_world_list():
    if not BASE_DIR.exists():
        BASE_DIR.mkdir()
    return [d.name for d in BASE_DIR.iterdir() if d.is_dir()]

def load_world_config(world_name):
    world_path = BASE_DIR / world_name
    files_content = {}
    for fname in WORLD_FILES:
        path = world_path / fname
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                files_content[fname] = f.read()
        else:
            files_content[fname] = ""
            
    history = []
    history_path = world_path / "history.json"
    if history_path.exists():
        try:
            with open(history_path, 'r', encoding='utf-8') as f:
                history = json.load(f)
        except:
            history = []
    return files_content, history

def save_world_files(world_path, files_content):
    world_path.mkdir(parents=True, exist_ok=True)
    for fname, content in files_content.items():
        path = world_path / fname
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

def save_history(world_path, history):
    history_path = world_path / "history.json"
    with open(history_path, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

# ======== КЛАСС ПРИЛОЖЕНИЯ ========
class DungeonApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🐉 AI Dungeon Master")
        self.root.geometry("800x1000")
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.current_world_path = None
        self.world_name = None
        self.history = []
        
        self.temperature = 0.9
        self.max_tokens = 400
        self.context_size = 24576
        self.summary_interval = 10
        self.stream_mode = True
        self.turns_since_summary = 0
        
        self.load_global_settings()
        
        self.processing = False
        self.dm_stream_start_index = None
        self.last_sent_prompt = None
        
        self.create_widgets()
        self.initialize_world()
        self.update_summary_label()

    def on_closing(self):
        if self.current_world_path:
            save_history(self.current_world_path, self.history)
        self.root.destroy()

    def load_global_settings(self):
        if SETTINGS_FILE.exists():
            try:
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    s = json.load(f)
                    self.temperature = s.get("temperature", 0.9)
                    self.max_tokens = s.get("max_tokens", 400)
                    self.context_size = s.get("context_size", 24576)
                    self.summary_interval = s.get("summary_interval", 10)
                    self.stream_mode = s.get("stream_mode", True)
            except: pass

    def save_global_settings(self):
        if not BASE_DIR.exists(): BASE_DIR.mkdir()
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "context_size": self.context_size,
                "summary_interval": self.summary_interval,
                "stream_mode": self.stream_mode
            }, f)

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

        title_label = ctk.CTkLabel(main_frame, text="🐉 AI DUNGEON MASTER 🐉", font=ctk.CTkFont(size=20, weight="bold"), text_color=COLORS['accent'])
        title_label.pack(pady=(0, 15))

        # --- INFO FRAME ---
        info_frame = ctk.CTkFrame(main_frame, height=40)
        info_frame.pack(fill=ctk.X, pady=(0, 10))
        
        self.world_var = ctk.StringVar()
        self.world_combobox = ctk.CTkOptionMenu(
            info_frame, 
            variable=self.world_var,
            command=self.on_world_selected,
            width=200
        )
        self.world_combobox.pack(side=ctk.LEFT, padx=10, pady=5)
        
        add_world_btn = ctk.CTkButton(info_frame, text="➕", width=30, command=self.create_world_dialog)
        add_world_btn.pack(side=ctk.LEFT, padx=5, pady=5)

        self.status_label = ctk.CTkLabel(info_frame, text="● Готов", text_color=COLORS['player_color'])
        self.status_label.pack(side=ctk.RIGHT, padx=10, pady=5)

        self.summary_label = ctk.CTkLabel(info_frame, text="До суммаризации: -", text_color="gray")
        self.summary_label.pack(side=ctk.RIGHT, padx=10, pady=5)

        # --- TOP BUTTONS ---
        top_button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        top_button_frame.pack(fill=ctk.X, pady=(0, 10))
        
        top_commands = [
            ("📁 Файлы мира", self.open_world_files),
            ("🔄 Миры", self.manage_worlds),
            ("⚙️ Настройки ИИ", self.open_ai_settings),
            ("❌ Выйти", self.quit_app)
        ]
        for text, cmd in top_commands:
            btn = ctk.CTkButton(top_button_frame, text=text, command=cmd, fg_color="transparent", border_width=1)
            btn.pack(side=ctk.LEFT, padx=5)

        # --- CHAT AREA ---
        self.text_area = ctk.CTkTextbox(main_frame, wrap=tk.WORD, font=ctk.CTkFont(family='Arial', size=14))
        self.text_area.pack(fill=ctk.BOTH, expand=True, pady=(0, 10))
        
        # Настройка тегов в базовом tk.Text, который находится внутри CTkTextbox
        # Исправленный код
        self.text_area._textbox.tag_config('player', foreground=COLORS['player_color'], font=('Arial', 14, 'bold'))
        self.text_area._textbox.tag_config('dm', foreground=COLORS['dm_color'], font=('Arial', 14))
        self.text_area._textbox.tag_config('system', foreground=COLORS['system_color'], font=('Arial', 12, 'italic'))
        self.text_area.configure(state='disabled')

        # --- ACTION BUTTONS ---
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill=ctk.X, pady=(0, 10))

        btn_args = {"height": 30, "font": ctk.CTkFont(size=12)}
        undo_btn = ctk.CTkButton(button_frame, text="⏪ Отменить ход", command=self.undo_action, fg_color=COLORS['danger'], hover_color=COLORS['danger_hover'], **btn_args)
        undo_btn.pack(side=ctk.RIGHT, padx=5)

        summary_btn = ctk.CTkButton(button_frame, text="📝 Суммаризация", command=self.force_summary, **btn_args)
        summary_btn.pack(side=ctk.RIGHT, padx=5)

        edit_btn = ctk.CTkButton(button_frame, text="✏️ Изменить", command=self.edit_last_dm_message, **btn_args)
        edit_btn.pack(side=ctk.RIGHT, padx=5)

        prompt_btn = ctk.CTkButton(button_frame, text="📋 Промпт", command=self.show_last_prompt, **btn_args)
        prompt_btn.pack(side=ctk.RIGHT, padx=5)

        regen_btn = ctk.CTkButton(button_frame, text="🔁 Реролл", command=self.regenerate_action, **btn_args)
        regen_btn.pack(side=ctk.RIGHT, padx=5)

        # --- INPUT AREA ---
        input_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        input_frame.pack(fill=ctk.X)

        self.input_field = ctk.CTkTextbox(input_frame, height=70, wrap=tk.WORD, font=ctk.CTkFont(size=14))
        self.input_field.pack(side=ctk.LEFT, fill=ctk.X, expand=True, padx=(0, 10))
        self.input_field.bind('<Return>', self.handle_input_enter)
        self.input_field.bind('<Button-3>', self.show_context_menu)
        self.input_field.focus()

        self.send_button = ctk.CTkButton(input_frame, text="▶ Отправить", command=self.send_action, fg_color=COLORS['accent'], hover_color=COLORS['button_hover'], text_color="black", font=ctk.CTkFont(weight="bold"), width=120, height=70)
        self.send_button.pack(side=ctk.RIGHT)

    def handle_input_enter(self, event):
        if event.state & 0x1: return
        self.send_action()
        return "break"

    def refresh_chat_display(self):
        self.text_area.configure(state='normal')
        self.text_area.delete("1.0", tk.END)
        if self.history:
            for msg in self.history:
                if msg.startswith("Игрок:"):
                    player_text = msg[len("Игрок:"):].strip()
                    if player_text:
                        self.text_area.insert(tk.END, f"\n🎮 {player_text}\n", 'player')
                elif msg.startswith("Мастер:"):
                    dm_text = msg[len("Мастер:"):].strip()
                    self.text_area.insert(tk.END, f"\n📜 {dm_text}\n", 'dm')
                else:
                    self.text_area.insert(tk.END, f"\n{msg}\n", 'system')
        self.text_area.configure(state='disabled')
        self.text_area.see(tk.END)

    def update_summary_label(self):
        if not self.current_world_path:
            self.summary_label.configure(text="До суммаризации: -")
            return
        remaining = max(0, self.summary_interval - self.turns_since_summary)
        color = COLORS['accent'] if remaining <= 2 else "gray"
        self.summary_label.configure(text=f"До сумм.: {remaining}", text_color=color)

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
        if not world_path.exists(): return
        
        self.current_world_path = world_path
        self.world_name = world_name
        self.turns_since_summary = 0
        self.last_sent_prompt = None
        _, self.history = load_world_config(world_name)
        
        self.refresh_chat_display()
        self.add_system_message(f"✅ Мир '{world_name}' загружен.")
        self.update_summary_label()
        
        self.refresh_world_combobox()
        self.world_var.set(self.world_name)

    def manage_worlds(self):
        win = ctk.CTkToplevel(self.root)
        win.title("🔄 Управление мирами")
        win.geometry("500x400")
        win.transient(self.root)
        win.grab_set()

        ctk.CTkLabel(win, text="Ваши миры:", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        
        # Стандартный Listbox выглядит нормально, если стилизовать
        listbox = tk.Listbox(win, bg=COLORS['listbox_bg'], fg="white", selectbackground=COLORS['listbox_sel'], 
                             relief=tk.FLAT, font=('Arial', 12), highlightthickness=0, borderwidth=0)
        listbox.pack(fill=ctk.BOTH, expand=True, padx=20, pady=(0,10))
        
        for w in get_world_list(): listbox.insert(tk.END, w)

        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.pack(fill=ctk.X, padx=20, pady=10)

        def switch_to_world():
            sel = listbox.curselection()
            if not sel: return
            name = listbox.get(sel[0])
            win.destroy()
            self.load_world(name)

        def delete_world():
            sel = listbox.curselection()
            if not sel: return
            name = listbox.get(sel[0])
            if messagebox.askyesno("Удалить мир", f"Удалить мир '{name}' безвозвратно?"):
                shutil.rmtree(BASE_DIR / name)
                listbox.delete(sel[0])
                if self.world_name == name:
                    self.current_world_path = None
                    self.world_name = None
                    self.refresh_world_combobox()
                    self.history = []
                    self.turns_since_summary = 0
                    self.update_summary_label()
                    self.refresh_chat_display()

        ctk.CTkButton(btn_frame, text="Загрузить", command=switch_to_world).pack(side=ctk.LEFT, padx=5)
        ctk.CTkButton(btn_frame, text="Удалить", command=delete_world, fg_color=COLORS['danger'], hover_color=COLORS['danger_hover']).pack(side=ctk.LEFT, padx=5)
        ctk.CTkButton(btn_frame, text="Создать", command=lambda: [win.destroy(), self.create_world_dialog()]).pack(side=ctk.LEFT, padx=5)
        ctk.CTkButton(btn_frame, text="Закрыть", command=win.destroy, fg_color="gray").pack(side=ctk.RIGHT, padx=5)

    def create_world_dialog(self):
        win = ctk.CTkToplevel(self.root)
        win.title("🔄 Создать новый мир")
        win.geometry("750x600")
        win.transient(self.root)
        win.grab_set()

        ctk.CTkLabel(win, text="Название мира (папка):").pack(pady=(10,0))
        name_entry = ctk.CTkEntry(win, width=300)
        name_entry.pack(pady=5)
        name_entry.insert(0, "Новый мир")

        tabview = ctk.CTkTabview(win)
        tabview.pack(fill=ctk.BOTH, expand=True, padx=15, pady=5)
        tabs = {}
        
        for fname, desc in WORLD_FILES.items():
            tab = tabview.add(desc)
            text_widget = ctk.CTkTextbox(tab, wrap=tk.WORD)
            text_widget.pack(fill=ctk.BOTH, expand=True, padx=5, pady=5)
            text_widget.insert("1.0", DEFAULT_TEMPLATES.get(fname, ""))
            text_widget.bind('<Button-3>', self.show_context_menu)
            tabs[fname] = text_widget

        def apply_new_world():
            name = name_entry.get().strip()
            if not name or (BASE_DIR / name).exists():
                messagebox.showerror("Ошибка", "Некорректное или занятое имя")
                return
            content = {fname: w.get("1.0", tk.END).strip() for fname, w in tabs.items()}
            save_world_files(BASE_DIR / name, content)
            save_history(BASE_DIR / name, [])
            win.destroy()
            self.load_world(name)
            self.refresh_world_combobox()

        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.pack(fill=ctk.X, pady=15, padx=15)
        ctk.CTkButton(btn_frame, text="✅ Создать", command=apply_new_world, fg_color=COLORS['accent'], text_color="black").pack(side=ctk.LEFT, padx=5)
        ctk.CTkButton(btn_frame, text="❌ Отмена", command=win.destroy, fg_color="gray").pack(side=ctk.RIGHT, padx=5)

    def open_world_files(self):
        if not self.current_world_path: return
        win = ctk.CTkToplevel(self.root)
        win.title("📁 Файлы мира")
        win.geometry("800x550")
        win.transient(self.root)
        win.grab_set()

        self.current_editing_file = None
        self.current_editing_file_index = None
        self.file_editor_original_content = ""
        self.files_window = win

        left_frame = ctk.CTkFrame(win, width=200)
        left_frame.pack(side=ctk.LEFT, fill=ctk.Y, padx=10, pady=10)
        left_frame.pack_propagate(False)
        
        ctk.CTkLabel(left_frame, text="Выберите файл:", font=ctk.CTkFont(weight="bold")).pack(pady=5)
        
        self.file_listbox = tk.Listbox(left_frame, bg=COLORS['listbox_bg'], fg="white", selectbackground=COLORS['listbox_sel'], 
                                       relief=tk.FLAT, font=('Arial', 11), highlightthickness=0, borderwidth=0)
        self.file_listbox.pack(fill=ctk.BOTH, expand=True, padx=5, pady=5)
        for fname, desc in WORLD_FILES.items():
            self.file_listbox.insert(tk.END, f"{desc}")

        right_frame = ctk.CTkFrame(win)
        right_frame.pack(side=ctk.RIGHT, fill=ctk.BOTH, expand=True, padx=(0, 10), pady=10)
        
        self.file_editor = ctk.CTkTextbox(right_frame, wrap=tk.WORD, font=ctk.CTkFont(size=14))
        self.file_editor.pack(fill=ctk.BOTH, expand=True, padx=10, pady=10)
        self.file_editor.bind('<Button-3>', self.show_context_menu)
        
        # Биндим на внутренний text widget для отслеживания изменений
        self.file_editor._textbox.bind('<<Modified>>', self.on_file_editor_modified)

        btn_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        btn_frame.pack(fill=ctk.X, pady=10, padx=10)
        
        ctk.CTkButton(btn_frame, text="💾 Сохранить", command=self.save_current_file).pack(side=ctk.LEFT, padx=5)
        self.unsaved_label = ctk.CTkLabel(btn_frame, text="", text_color=COLORS['accent'])
        self.unsaved_label.pack(side=ctk.LEFT, padx=10)

        self.file_listbox.bind('<<ListboxSelect>>', self.on_file_select)
        win.protocol("WM_DELETE_WINDOW", self.close_files_window)

        if self.file_listbox.size() > 0:
            self.file_listbox.selection_set(0)
            self._load_file_into_editor(0)

    def on_file_editor_modified(self, event):
        self.file_editor._textbox.edit_modified(False)
        self.update_unsaved_indicator()

    def has_unsaved_file_changes(self):
        if not hasattr(self, 'file_editor') or self.current_editing_file is None:
            return False
        current_content = self.file_editor.get("1.0", tk.END).strip()
        return current_content != self.file_editor_original_content.strip()

    def update_unsaved_indicator(self):
        if not hasattr(self, 'unsaved_label') or not self.unsaved_label.winfo_exists(): return
        if self.has_unsaved_file_changes():
            self.unsaved_label.configure(text="● Есть несохранённые изменения")
        else:
            self.unsaved_label.configure(text="")

    def _load_file_into_editor(self, index):
        fname = list(WORLD_FILES.keys())[index]
        path = self.current_world_path / fname
        content = path.read_text(encoding='utf-8') if path.exists() else ""
        self.file_editor.delete("1.0", tk.END)
        self.file_editor.insert("1.0", content)
        self.file_editor._textbox.edit_modified(False)
        self.current_editing_file = fname
        self.current_editing_file_index = index
        self.file_editor_original_content = content
        self.update_unsaved_indicator()

    def on_file_select(self, event):
        sel = self.file_listbox.curselection()
        if not sel: return
        new_index = sel[0]

        if new_index == self.current_editing_file_index: return
        if not self.has_unsaved_file_changes():
            self._load_file_into_editor(new_index)
            return

        old_fname = self.current_editing_file
        choice = messagebox.askyesnocancel("Внимание", f"В файле «{WORLD_FILES.get(old_fname, old_fname)}» есть изменения. Сохранить?")
        if choice is None:
            self.file_listbox.selection_clear(0, tk.END)
            self.file_listbox.selection_set(self.current_editing_file_index)
            return
        elif choice:
            self.save_current_file()

        self._load_file_into_editor(new_index)

    def close_files_window(self):
        if self.has_unsaved_file_changes():
            choice = messagebox.askyesnocancel("Внимание", "Есть несохранённые изменения. Сохранить перед закрытием?")
            if choice is None: return
            elif choice: self.save_current_file()
        self.files_window.destroy()

    def save_current_file(self):
        if not getattr(self, 'current_editing_file', None): return
        content = self.file_editor.get("1.0", tk.END)
        (self.current_world_path / self.current_editing_file).write_text(content, encoding='utf-8')
        self.file_editor_original_content = content.strip()
        self.file_editor._textbox.edit_modified(False)
        self.update_unsaved_indicator()
        self.add_system_message(f"✅ Файл {self.current_editing_file} сохранён")

    def open_ai_settings(self):
        win = ctk.CTkToplevel(self.root)
        win.title("⚙️ Настройки ИИ")
        win.geometry("450x550")
        win.transient(self.root)
        win.grab_set()

        stream_var = ctk.BooleanVar(value=self.stream_mode)
        ctk.CTkCheckBox(win, text="Потоковый ответ (Streaming)", variable=stream_var).pack(anchor=tk.W, padx=20, pady=(20, 10))

        # Тепмпература
        ctk.CTkLabel(win, text="Температура (0.0 - 2.0):").pack(anchor=tk.W, padx=20)
        temp_val_lbl = ctk.CTkLabel(win, text=f"{self.temperature:.1f}", text_color=COLORS['accent'])
        temp_val_lbl.pack(anchor=tk.E, padx=20)
        
        def update_temp_lbl(val): temp_val_lbl.configure(text=f"{val:.1f}")
        temp_slider = ctk.CTkSlider(win, from_=0.0, to=2.0, number_of_steps=20, command=update_temp_lbl)
        temp_slider.set(self.temperature)
        temp_slider.pack(fill=ctk.X, padx=20, pady=(0, 15))

        # Токены
        ctk.CTkLabel(win, text="Макс. токенов в ответе:").pack(anchor=tk.W, padx=20)
        tokens_entry = ctk.CTkEntry(win)
        tokens_entry.pack(fill=ctk.X, padx=20, pady=(5, 15))
        tokens_entry.insert(0, str(self.max_tokens))

        # Контекст
        ctk.CTkLabel(win, text="Размер контекста:").pack(anchor=tk.W, padx=20)
        ctx_val_lbl = ctk.CTkLabel(win, text=f"{self.context_size}", text_color=COLORS['accent'])
        ctx_val_lbl.pack(anchor=tk.E, padx=20)
        
        def update_ctx_lbl(val): ctx_val_lbl.configure(text=f"{int(val)}")
        ctx_slider = ctk.CTkSlider(win, from_=4096, to=131072, number_of_steps=31, command=update_ctx_lbl)
        ctx_slider.set(self.context_size)
        ctx_slider.pack(fill=ctk.X, padx=20, pady=(0, 15))

        # Интервал
        ctk.CTkLabel(win, text="Суммаризация (каждые N ходов):").pack(anchor=tk.W, padx=20)
        interval_var = ctk.StringVar(value=str(self.summary_interval))
        ctk.CTkOptionMenu(win, variable=interval_var, values=["5", "10", "15", "20"]).pack(anchor=tk.W, padx=20, pady=5)

        def apply_settings():
            self.stream_mode = stream_var.get()
            self.temperature = temp_slider.get()
            self.context_size = int(ctx_slider.get())
            try: self.max_tokens = int(tokens_entry.get())
            except: pass
            try: self.summary_interval = int(interval_var.get())
            except: pass
            self.save_global_settings()
            self.add_system_message(f"⚙️ Настройки сохранены. Стриминг: {'ВКЛ' if self.stream_mode else 'ВЫКЛ'}.")
            win.destroy()

        ctk.CTkButton(win, text="💾 Сохранить", command=apply_settings).pack(pady=20)

    def quit_app(self):
        if messagebox.askyesno("Выход", "Действительно выйти из игры?"):
            self.on_closing()

    def undo_action(self):
        if self.processing or not self.history or not self.current_world_path: return
        last_msg = self.history[-1]
        self.history.pop()
        if self.turns_since_summary > 0: self.turns_since_summary -= 1
        save_history(self.current_world_path, self.history)
        self.refresh_chat_display()
        self.add_system_message("⏪ Последнее сообщение удалено.")

    def regenerate_action(self):
        if self.processing or not self.history or not self.current_world_path: return
        
        if self.history[-1].startswith("Мастер:"): self.history.pop()
        
        last_player_input = ""
        if self.history and self.history[-1].startswith("Игрок:"):
            last_player_input = self.history[-1][len("Игрок:"):].strip()
            
        save_history(self.current_world_path, self.history)
        self.refresh_chat_display()
        
        self.processing = True
        self.send_button.configure(state='disabled', text="⏳ Думаю...")
        self.status_label.configure(text="● Generation...", text_color=COLORS['system_color'])
        Thread(target=self.process_action, args=(last_player_input,), daemon=True).start()
        
    def edit_last_dm_message(self):
        if not self.current_world_path or not self.history: return
        dm_index = -1
        for i in range(len(self.history) - 1, -1, -1):
            if self.history[i].startswith("Мастер:"):
                dm_index = i
                break
        if dm_index == -1: return

        current_text = self.history[dm_index][len("Мастер:"):].strip()
        win = ctk.CTkToplevel(self.root)
        win.title("✏️ Редактировать ответ")
        win.geometry("600x500")
        win.transient(self.root)
        win.grab_set()

        ctk.CTkLabel(win, text="Редактирование ответа:").pack(pady=(10, 5), anchor=tk.W, padx=15)
        
        editor = ctk.CTkTextbox(win, wrap=tk.WORD, font=ctk.CTkFont(size=14))
        editor.pack(fill=ctk.BOTH, expand=True, padx=15, pady=5)
        editor.insert(tk.END, current_text)
        editor.focus_set()
        editor.bind('<Button-3>', self.show_context_menu)

        def save_edited_msg():
            new_text = editor.get("1.0", tk.END).strip()
            if not new_text: return
            self.history[dm_index] = f"Мастер: {new_text}"
            save_history(self.current_world_path, self.history)
            self.refresh_chat_display()
            win.destroy()
            self.add_system_message("📝 Ответ Мастера изменен.")

        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.pack(fill=ctk.X, pady=15, padx=15)
        ctk.CTkButton(btn_frame, text="✅ Сохранить", command=save_edited_msg, fg_color=COLORS['accent'], text_color="black").pack(side=ctk.LEFT)
        ctk.CTkButton(btn_frame, text="❌ Отмена", command=win.destroy, fg_color="gray").pack(side=ctk.RIGHT)

    def force_summary(self):
        if self.processing or not self.current_world_path: return
        self.turns_since_summary = 0
        self.update_summary_label()
        self.add_system_message("📝 Принудительное обновление краткого содержания...")
        Thread(target=self.generate_global_summary, daemon=True).start()

    def show_last_prompt(self):
        if not self.last_sent_prompt:
            messagebox.showinfo("Промпт", "Нет данных о запросе.")
            return

        data = self.last_sent_prompt
        full_text = f"=== ВРЕМЯ ЗАПРОСА ===\n{data['time']}\n\n=== ПРИМЕРНОЕ КОЛ-ВО ТОКЕНОВ ===\n{data['tokens']}\n\n=== SYSTEM ===\n{data['system']}\n\n=== USER ===\n{data['user']}\n"

        win = ctk.CTkToplevel(self.root)
        win.title("📋 Последний промпт")
        win.geometry("750x650")
        win.transient(self.root)
        win.grab_set()

        viewer = ctk.CTkTextbox(win, wrap=tk.WORD, font=ctk.CTkFont(family='Consolas', size=12))
        viewer.pack(fill=ctk.BOTH, expand=True, padx=15, pady=15)
        viewer.insert("1.0", full_text)
        viewer.configure(state='disabled')

        def copy_to_clipboard():
            self.root.clipboard_clear()
            self.root.clipboard_append(full_text)
            self.add_system_message("📋 Промпт скопирован.")

        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.pack(fill=ctk.X, padx=15, pady=(0,15))
        ctk.CTkButton(btn_frame, text="📋 Копировать", command=copy_to_clipboard).pack(side=ctk.LEFT)
        ctk.CTkButton(btn_frame, text="❌ Закрыть", command=win.destroy, fg_color="gray").pack(side=ctk.RIGHT)

    def fix_truncated_text(self, text: str) -> str:
        text = text.strip()
        if not text: return text
        if text[-1] in ['.', '!', '?', '…', '"', '»', '*', ')', ']']: return text
        
        punctuation_marks = [text.rfind('.'), text.rfind('!'), text.rfind('?'), text.rfind('…')]
        last_pos = max(punctuation_marks)
        
        if last_pos != -1:
            cut_text = text[:last_pos + 1].strip()
            if text.count('*') % 2 == 0 and cut_text.count('*') % 2 != 0: cut_text += ' *'
            if len(cut_text) > 15: return cut_text
        return text + "..."

    def send_action(self):
        if self.processing or not self.current_world_path: return
        user_input = self.input_field.get("1.0", tk.END).strip()
        self.input_field.delete("1.0", tk.END)
        
        if user_input: self.add_player_message(user_input)
            
        self.turns_since_summary += 1
        self.update_summary_label()
        self.processing = True
        self.send_button.configure(state='disabled', text="⏳ Думаю...")
        self.status_label.configure(text="● Generation...", text_color=COLORS['system_color'])
        Thread(target=self.process_action, args=(user_input,), daemon=True).start()

    def start_dm_stream(self):
        self.text_area.configure(state='normal')
        self.text_area.insert(tk.END, "\nМастер: ", 'dm')
        self.stream_start_index = self.text_area.index("end-1c")
        self.text_area.configure(state='disabled')
        self.text_area.see(tk.END)

    def append_to_dm_stream(self, chunk):
        self.text_area.configure(state='normal')
        self.text_area.insert(tk.END, chunk, 'dm')
        self.text_area.configure(state='disabled')
        self.text_area.see(tk.END)

    def finalize_dm_stream(self, final_text):
        self.text_area.configure(state='normal')
        if hasattr(self, 'stream_start_index'):
            self.text_area.delete(self.stream_start_index, tk.END)
        self.text_area.insert(tk.END, f"{final_text}\n", 'dm')
        self.text_area.configure(state='disabled')
        self.text_area.see(tk.END)

    def process_action(self, user_input):
        try:
            if user_input and (not self.history or f"Игрок: {user_input}" != self.history[-1]):
                self.history.append(f"Игрок: {user_input}")

            context = ""
            for fname in WORLD_FILES:
                if fname == "summary.txt": continue
                path = self.current_world_path / fname
                if path.exists():
                    content = path.read_text(encoding='utf-8').strip()
                    if content: context += f"=== {fname} ===\n{content}\n"

            summary_path = self.current_world_path / "summary.txt"
            summary_content = summary_path.read_text(encoding='utf-8').strip() if summary_path.exists() else ""
            if summary_content:
                context += f"=== Сжатая хроника прошлых событий (summary.txt) ===\n{summary_content}\n"

            user_content = user_input if user_input else "(Продолжай повествование.)"
            system_base_text = f"{context}\nИСТОРИЯ ТЕКУЩЕЙ ИГРОВОЙ СЕССИИ:\n"
            static_tokens = count_tokens(system_base_text)
            user_tokens = count_tokens(user_content)
            safety_buffer = 200
            
            available_history_tokens = self.context_size - self.max_tokens - static_tokens - user_tokens - safety_buffer
            if available_history_tokens < 300: available_history_tokens = 300

            short_history = []
            current_history_tokens = 0
            
            history_pool = self.history[:-1] if user_input else self.history
            for msg in reversed(history_pool):
                msg_tokens = count_tokens(msg) + 1
                if current_history_tokens + msg_tokens <= available_history_tokens:
                    short_history.insert(0, msg)
                    current_history_tokens += msg_tokens
                else: break
            
            history_text = "\n".join(short_history)
            system_final_content = f"""{context}\nИСТОРИЯ ТЕКУЩЕЙ ИГРОВОЙ СЕССИИ:\n{history_text}"""
            prompt_tokens = count_tokens(system_final_content) + count_tokens(user_content)

            self.last_sent_prompt = {
                "system": system_final_content,
                "user": user_content,
                "tokens": prompt_tokens,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            payload = {
                "messages": [
                    {"role": "system", "content": system_final_content},
                    {"role": "user", "content": user_content}
                ],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "stream": self.stream_mode,
                "stop": ["\nИгрок:", "Игрок:", "<|im_end|>", "<|eot_id|>", "```", "---"]
            }

            if self.stream_mode:
                response = requests.post(API_URL, json=payload, stream=True, timeout=120)
                response.raise_for_status()

                self.root.after(0, self.start_dm_stream)
                raw_narration = ""
                decoder = codecs.getincrementaldecoder('utf-8')('ignore')
                buffer = ""
                
                for chunk in response.iter_content(chunk_size=None):
                    if not chunk: continue
                    buffer += decoder.decode(chunk)
                    
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        line = line.strip()
                        if not line or not line.startswith("data: "): continue
                        json_str = line[6:]
                        if json_str == "[DONE]": break
                        
                        try:
                            data = json.loads(json_str)
                            content = data['choices'][0].get('delta', {}).get('content', '')
                            if content:
                                content = re.sub(r'[\uac00-\ud7a3\u4e00-\u9fff]', '', content)
                                content = content.replace('$', '').replace('{', '').replace('}', '')
                                if content:
                                    raw_narration += content
                                    self.root.after(0, lambda c=content: self.append_to_dm_stream(c))
                        except: pass
                ai_text = raw_narration.strip()
            else:
                response = requests.post(API_URL, json=payload, timeout=120)
                response.raise_for_status()
                ai_text = response.json()['choices'][0]['message']['content'].strip()
                self.root.after(0, self.start_dm_stream)

            if not ai_text:
                self.root.after(0, lambda: self.add_system_message("⚠️ Модель вернула пустой ответ."))
                return

            ai_text = re.sub(r'^(Мастер|AI|Narrator|DM|ИИ|Master):\s*', '', ai_text, flags=re.IGNORECASE).strip()
            cleaned_text = ai_text.replace("```json", "").replace("```", "").strip()
            
            final_narration = ai_text
            final_narration = re.sub(r'\$\{?[^}]*\}?\$', '', final_narration)
            final_narration = final_narration.replace('$', '')
            final_narration = re.sub(r'[\uac00-\ud7a3\u4e00-\u9fff]', '', final_narration)
            final_narration = re.sub(r'\(\s*\)', '', final_narration).strip()
            final_narration = self.fix_truncated_text(final_narration)
            
            self.root.after(0, lambda f=final_narration: self.finalize_dm_stream(f))

            self.history.append(f"Мастер: {final_narration}")
            save_history(self.current_world_path, self.history)

            completion_tokens = count_tokens(final_narration)
            total_tokens = prompt_tokens + completion_tokens
            
            self.root.after(0, lambda p=prompt_tokens, c=completion_tokens, t=total_tokens: self.add_system_message(
                f"📊 Токены: Контекст: {p} | Ответ: {c} | Всего: {t}/{self.context_size}"
            ))

            if self.turns_since_summary >= self.summary_interval:
                self.turns_since_summary = 0
                self.root.after(0, lambda: self.add_system_message("📝 ИИ пересматривает хронологию..."))
                Thread(target=self.generate_global_summary, daemon=True).start()

        except requests.exceptions.ConnectionError:
            self.root.after(0, lambda: self.add_system_message("❌ Ошибка: Локальный сервер ИИ не запущен!"))
        except Exception as e:
            err_msg = str(e)
            self.root.after(0, lambda msg=err_msg: self.add_system_message(f"❌ Ошибка: {msg}"))
        finally:
            self.root.after(0, self.processing_end)

    def generate_global_summary(self):
        try:
            if not self.current_world_path: return
            
            summary_path = self.current_world_path / "summary.txt"
            old_summary = summary_path.read_text(encoding='utf-8').strip() if summary_path.exists() else "Отсутствует."
            
            characters_path = self.current_world_path / "characters.txt"
            characters_content = characters_path.read_text(encoding='utf-8').strip() if characters_path.exists() else "Информация отсутствует."
            
            prompt_template_base = f"""Перед тобой история текстовой ролевой игры, её старое краткое содержание и информация о персонажах.
Твоя задача: составить обновленное, чистое и емкое КРАТКОЕ СОДЕРЖАНИЕ (summary).
ПРАВИЛА:
1. Сформируй кратую исторую в хронологическомы порядке.
2. Игнорируй мелкую рутину, лишние диалоги.
3. Пиши структурированно, лаконично.
4. Обязательно учти информацию из СТАРОГО краткого содержания.
5. УЧТИ ИНФОРМАЦИЮ О ПЕРСОНАЖАХ.

ИНФОРМАЦИЯ О ПЕРСОНАЖАХ:
{characters_content}

СТАРОЕ КРАТКОЕ СОДЕРЖАНИЕ:
{old_summary}

АКТУАЛЬНАЯ ИСТОРИЯ ИГРЫ:

Выдай только текст нового краткого содержания простым текстом без лишних *, вступлений и Markdown."""

            summary_max_tokens = 1000
            base_prompt_tokens = count_tokens(prompt_template_base)
            safety_buffer = 400

            available_summary_history = self.context_size - summary_max_tokens - base_prompt_tokens - safety_buffer
            if available_summary_history < 800: available_summary_history = 800

            short_history = []
            current_history_tokens = 0
            
            for msg in reversed(self.history):
                msg_tokens = count_tokens(msg) + 1
                if current_history_tokens + msg_tokens <= available_summary_history:
                    short_history.insert(0, msg)
                    current_history_tokens += msg_tokens
                else: break
                    
            history_text = "\n".join(short_history)

            prompt = f"""Перед тобой история текстовой ролевой игры, её старое краткое содержание и информация о персонажах.
Твоя задача: составить обновленное, чистое и емкое КРАТКОЕ СОДЕРЖАНИЕ (summary).
ПРАВИЛА:
1. Сформируй кратую исторую в хронологическомы порядке.
2. Игнорируй мелкую рутину.
3. Пиши лаконично, тезисно.
4. Учти СТАРОЕ краткое содержание.

ИНФОРМАЦИЯ О ПЕРСОНАЖАХ:
{characters_content}

СТАРОЕ КРАТКОЕ СОДЕРЖАНИЕ:
{old_summary}

АКТУАЛЬНАЯ ИСТОРИЯ ИГРЫ:
{history_text}

Выдай только текст нового краткого содержания простым текстом без лишних *, вступлений и Markdown."""

            payload = {
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": summary_max_tokens,
                "stream": False
            }
            response = requests.post(API_URL, json=payload, timeout=180)
            response.raise_for_status()
            new_summary = response.json()['choices'][0]['message']['content'].strip()
            new_summary = new_summary.replace("```json", "").replace("```", "").strip()
            
            if new_summary:
                summary_path.write_text(new_summary, encoding='utf-8')
                self.root.after(0, lambda: self.add_system_message("✨ Краткое содержание мира успешно синхронизировано!"))
                self.root.after(0, self.update_summary_label)
                
        except Exception as e:
            err_msg = str(e)
            self.root.after(0, lambda msg=err_msg: self.add_system_message(f"⚠️ Не удалось автоматически обновить саммари: {msg}"))

    def processing_end(self):
        self.processing = False
        self.send_button.configure(state='normal', text="▶ Отправить")
        self.status_label.configure(text="● Готов", text_color=COLORS['player_color'])
        self.input_field.focus()

    def add_system_message(self, message):
        self.text_area.configure(state='normal')
        self.text_area.insert(tk.END, f"\n{message}\n", 'system')
        self.text_area.configure(state='disabled')
        self.text_area.see(tk.END)

    def add_player_message(self, message):
        self.text_area.configure(state='normal')
        self.text_area.insert(tk.END, f"\n🎮 {message}\n", 'player')
        self.text_area.configure(state='disabled')
        self.text_area.see(tk.END)

    def show_context_menu(self, event):
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Копировать", command=lambda: event.widget.event_generate('<<Copy>>'))
        menu.add_command(label="Вставить", command=lambda: event.widget.event_generate('<<Paste>>'))
        menu.add_command(label="Вырезать", command=lambda: event.widget.event_generate('<<Cut>>'))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()


def main():
    # Инициализация CustomTkinter
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")
    
    root = ctk.CTk()
    app = DungeonApp(root)
    root.update_idletasks()
    
    # Центрирование окна
    x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
    y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
    root.geometry(f'+{x}+{y}')
    
    root.mainloop()

if __name__ == "__main__":
    main()