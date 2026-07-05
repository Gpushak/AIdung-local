#!/usr/bin/env python3
import os
import sys
import json
import re
import requests
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
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
        # Корректировка под русский язык для локальных моделей
        return int(len(TOKENIZER.encode(text)) / 1.65)
    return int(len(text) / 3.5)


# ======== НАСТРОЙКИ ========
API_URL = "http://localhost:1234/v1/chat/completions"
import sys
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
    'bg_dark': '#1e1e1e',
    'bg_medium': '#2d2d2d',
    'bg_light': '#3c3c3c',
    'accent': '#e6b450',
    'text_light': '#e0e0e0',
    'text_dim': '#a0a0a0',
    'player_color': '#8bc34a',
    'dm_color': '#e6b450',
    'system_color': '#61afef',
    'input_bg': '#252525',
    'button_bg': '#3a3a3a',
    'button_active': '#e6b450'
}

DEFAULT_TEMPLATES = {
    "ai_instructions.txt": """Ты - ИИ мастер, который предоставляет любой контент для ролевых игр.
Инструкции:
Обязательно:
- Отдавайте предпочтение действиям и диалогам, а не описаниям. 
- Не описывайте окружающую обстановку, освещение, погоду, звуки или жестикуляцию персонажей, если это напрямую не влияет на текущее действие.
- Избегайте повторяющегося эмоционального повествования.
- Пишите скорее как сценарий фильма, чем как роман.

- Будьте конкретны, описательны и изобретательны.
- Избегайте повторений и обобщений.
- Старайтесь развивать историю, даже если пользователь бездействует.
- Обычно говорите от второго лица (например, "О смотрит на вас"). Но используйте слова от третьего лица, если вам кажется, что история развивается именно так.
- Никогда не принимайте решения и не пишите за пользователя. Если ввод заканчивается на середине предложения, продолжайте с того места, где он был прерван.
- Подробно опишите внешность и характерные черты персонажей.
""",
    "plot_basics.txt": """Мир фэнтези.
Вы искатель приключений.
У вас есть мееч и щит.
Вы носите легкую кожаную броню.""",
    "author_notes.txt": """Стиль написания: Приключение, комедия, фэнтези.""",
    "characters.txt": """Главный герой:
- Имя: Арион
- Класс: Воин
- Оружие: Длинный меч и щит
- Навыки: Атлетика, Выживание""",
    "summary.txt": """"""
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
        self.root.geometry("700x1000")
        self.root.configure(bg=COLORS['bg_dark'])
        
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
        self.last_sent_prompt = None  # Хранит полный промпт последнего запроса к ИИ
        
        self.setup_styles()
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
            except:
                pass

    def save_global_settings(self):
        if not BASE_DIR.exists():
            BASE_DIR.mkdir()
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "context_size": self.context_size,
                "summary_interval": self.summary_interval,
                "stream_mode": self.stream_mode
            }, f)

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background=COLORS['bg_dark'])
        style.configure('TButton', background=COLORS['button_bg'], foreground=COLORS['text_light'], borderwidth=1, font=('Arial', 10))
        style.map('TButton', background=[('active', COLORS['button_active'])])
        style.configure('TNotebook', background=COLORS['bg_medium'], borderwidth=0)
        style.configure('TNotebook.Tab', background=COLORS['bg_light'], foreground=COLORS['text_light'], padding=[10, 2])
        style.map('TNotebook.Tab', background=[('selected', COLORS['accent'])])
        style.configure('TLabel', background=COLORS['bg_dark'], foreground=COLORS['text_light'])
        style.configure(
            'TCombobox',
            fieldbackground=COLORS['bg_light'],
            background=COLORS['bg_light'],
            foreground=COLORS['text_light'],
            arrowcolor=COLORS['text_light']
        )
        style.map(
            'TCombobox',
            fieldbackground=[('readonly', COLORS['bg_light'])],
            foreground=[('readonly', COLORS['text_light'])]
        )

    def refresh_world_combobox(self):
        worlds = get_world_list()
        self.world_combobox['values'] = worlds

        if self.world_name and self.world_name in worlds:
            self.world_var.set(self.world_name)
        elif worlds:
            first_world = worlds[0]
            self.world_var.set(first_world)
            self.load_world(first_world)
        else:
            self.world_var.set("")

    def on_world_selected(self, event):
        selected = self.world_var.get()
        if selected and selected != self.world_name:
            if self.current_world_path:
                save_history(self.current_world_path, self.history)
            self.load_world(selected)
    
    def create_widgets(self):
        main_frame = tk.Frame(self.root, bg=COLORS['bg_dark'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        title_label = tk.Label(main_frame, text="🐉 AI DUNGEON MASTER 🐉", font=('Arial', 16, 'bold'), bg=COLORS['bg_dark'], fg=COLORS['accent'])
        title_label.pack(pady=(0, 10))

        info_frame = tk.Frame(main_frame, bg=COLORS['bg_medium'], height=30)
        info_frame.pack(fill=tk.X, pady=(0, 5))
        info_frame.pack_propagate(False)
        
        self.world_var = tk.StringVar()
        self.world_combobox = ttk.Combobox(
            info_frame,
            textvariable=self.world_var,
            state="readonly",
            font=('Arial', 9),
            width=30
        )
        self.world_combobox.pack(side=tk.LEFT, padx=10)
        self.world_combobox.bind('<<ComboboxSelected>>', self.on_world_selected)
        
        add_world_btn = tk.Button(
            info_frame,
            text="➕",
            command=self.create_world_dialog,
            bg=COLORS['bg_medium'],
            fg=COLORS['text_light'],
            font=('Arial', 9),
            relief=tk.FLAT,
            padx=5,
            cursor='hand2'
        )
        add_world_btn.pack(side=tk.LEFT, padx=(2, 10))

        self.summary_label = tk.Label(info_frame, text="До суммаризации: -", font=('Arial', 9), bg=COLORS['bg_medium'], fg=COLORS['text_dim'])
        self.summary_label.pack(side=tk.RIGHT, padx=10)

        self.status_label = tk.Label(info_frame, text="● Готов", font=('Arial', 9), bg=COLORS['bg_medium'], fg=COLORS['player_color'])
        self.status_label.pack(side=tk.RIGHT, padx=10)

        top_button_frame = tk.Frame(main_frame, bg=COLORS['bg_dark'])
        top_button_frame.pack(fill=tk.X, pady=(0, 5))
        
        top_commands = [
            ("📁 Файлы мира", self.open_world_files),
            ("🔄 Миры", self.manage_worlds),
            ("⚙️ Настройки ИИ", self.open_ai_settings),
            ("❌ Выйти", self.quit_app)
        ]
        for text, cmd in top_commands:
            btn = tk.Button(top_button_frame, text=text, command=cmd, bg=COLORS['button_bg'], fg=COLORS['text_light'], font=('Arial', 9), relief=tk.FLAT, padx=10, pady=5, cursor='hand2')
            btn.pack(side=tk.LEFT, padx=2)
            btn.bind('<Enter>', lambda e, b=btn: b.configure(bg=COLORS['button_active']))
            btn.bind('<Leave>', lambda e, b=btn: b.configure(bg=COLORS['button_bg']))

        self.text_area = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, font=('Arial', 11), bg=COLORS['bg_medium'], fg=COLORS['text_light'], insertbackground=COLORS['text_light'], selectbackground=COLORS['accent'], relief=tk.FLAT, borderwidth=0, padx=15, pady=15)
        self.text_area.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        self.text_area.tag_config('player', foreground=COLORS['player_color'], font=('Arial', 11, 'bold'))
        self.text_area.tag_config('dm', foreground=COLORS['dm_color'], font=('Arial', 11))
        self.text_area.tag_config('system', foreground=COLORS['system_color'], font=('Arial', 10, 'italic'))
        self.text_area.configure(state='disabled')

        button_frame = tk.Frame(main_frame, bg=COLORS['bg_dark'])
        button_frame.pack(fill=tk.X, pady=(0, 5))

        regen_btn = tk.Button(button_frame, text="🔁 Перегенерировать", command=self.regenerate_action, bg=COLORS['button_bg'], fg=COLORS['text_light'], font=('Arial', 9), relief=tk.FLAT, padx=10, pady=5, cursor='hand2')
        regen_btn.pack(side=tk.RIGHT, padx=2)
        regen_btn.bind('<Enter>', lambda e, b=regen_btn: b.configure(bg=COLORS['button_active']))
        regen_btn.bind('<Leave>', lambda e, b=regen_btn: b.configure(bg=COLORS['button_bg']))

        prompt_btn = tk.Button(button_frame, text="📋 Промпт", command=self.show_last_prompt, bg=COLORS['button_bg'], fg=COLORS['text_light'], font=('Arial', 9), relief=tk.FLAT, padx=10, pady=5, cursor='hand2')
        prompt_btn.pack(side=tk.RIGHT, padx=2)
        prompt_btn.bind('<Enter>', lambda e, b=prompt_btn: b.configure(bg=COLORS['button_active']))
        prompt_btn.bind('<Leave>', lambda e, b=prompt_btn: b.configure(bg=COLORS['button_bg']))

        edit_btn = tk.Button(button_frame, text="✏️ Редактировать ответ", command=self.edit_last_dm_message, bg=COLORS['button_bg'], fg=COLORS['text_light'], font=('Arial', 9), relief=tk.FLAT, padx=10, pady=5, cursor='hand2')
        edit_btn.pack(side=tk.RIGHT, padx=2)
        edit_btn.bind('<Enter>', lambda e, b=edit_btn: b.configure(bg=COLORS['button_active']))
        edit_btn.bind('<Leave>', lambda e, b=edit_btn: b.configure(bg=COLORS['button_bg']))

        summary_btn = tk.Button(button_frame, text="📝 Суммаризация", command=self.force_summary, bg=COLORS['button_bg'], fg=COLORS['text_light'], font=('Arial', 9), relief=tk.FLAT, padx=10, pady=5, cursor='hand2')
        summary_btn.pack(side=tk.RIGHT, padx=2)
        summary_btn.bind('<Enter>', lambda e, b=summary_btn: b.configure(bg=COLORS['button_active']))
        summary_btn.bind('<Leave>', lambda e, b=summary_btn: b.configure(bg=COLORS['button_bg']))

        undo_btn = tk.Button(button_frame, text="⏪ Отменить ход", command=self.undo_action, bg=COLORS['button_bg'], fg=COLORS['text_light'], font=('Arial', 9), relief=tk.FLAT, padx=10, pady=5, cursor='hand2')
        undo_btn.pack(side=tk.RIGHT, padx=2)
        undo_btn.bind('<Enter>', lambda e, b=undo_btn: b.configure(bg='#d9534f'))
        undo_btn.bind('<Leave>', lambda e, b=undo_btn: b.configure(bg=COLORS['button_bg']))

        input_frame = tk.Frame(main_frame, bg=COLORS['bg_dark'])
        input_frame.pack(fill=tk.X)

        self.input_field = tk.Text(input_frame, font=('Arial', 11), bg=COLORS['input_bg'], fg=COLORS['text_light'], insertbackground=COLORS['text_light'], relief=tk.FLAT, borderwidth=0, height=3, wrap=tk.WORD)
        self.input_field.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5), pady=5)
        self.input_field.bind('<Return>', self.handle_input_enter)
        self.input_field.bind('<Button-3>', self.show_context_menu)
        self.input_field.focus()

        self.send_button = tk.Button(input_frame, text="▶ Отправить", command=self.send_action, bg=COLORS['accent'], fg='#1e1e1e', font=('Arial', 10, 'bold'), relief=tk.FLAT, padx=20, pady=8, cursor='hand2')
        self.send_button.pack(side=tk.RIGHT)

    def handle_input_enter(self, event):
        if event.state & 0x1:
            return
        self.send_action()
        return "break"

    def refresh_chat_display(self):
        self.text_area.configure(state='normal')
        self.text_area.delete(1.0, tk.END)
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
        color = COLORS['accent'] if remaining <= 2 else COLORS['text_dim']
        self.summary_label.configure(text=f"До сумм.: {remaining}", fg=color)

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
        win = tk.Toplevel(self.root)
        win.title("🔄 Управление мирами")
        win.geometry("500x400")
        win.configure(bg=COLORS['bg_medium'])
        win.transient(self.root)
        win.grab_set()

        tk.Label(win, text="Ваши миры:", bg=COLORS['bg_medium'], fg=COLORS['text_light'], font=('Arial', 12, 'bold')).pack(pady=10)
        listbox = tk.Listbox(win, bg=COLORS['bg_dark'], fg=COLORS['text_light'], selectbackground=COLORS['accent'], relief=tk.FLAT, font=('Arial', 11))
        listbox.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0,10))
        
        for w in get_world_list(): listbox.insert(tk.END, w)

        btn_frame = tk.Frame(win, bg=COLORS['bg_medium'])
        btn_frame.pack(fill=tk.X, padx=20, pady=10)

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

        tk.Button(btn_frame, text="Загрузить", command=switch_to_world, bg=COLORS['button_bg'], fg=COLORS['text_light'], relief=tk.FLAT, padx=10, pady=5).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Создать новый", command=lambda: [win.destroy(), self.create_world_dialog()], bg=COLORS['button_bg'], fg=COLORS['text_light'], relief=tk.FLAT, padx=10, pady=5).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Удалить", command=delete_world, bg='#8b3a3a', fg=COLORS['text_light'], relief=tk.FLAT, padx=10, pady=5).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Закрыть", command=win.destroy, bg=COLORS['button_bg'], fg=COLORS['text_light'], relief=tk.FLAT, padx=10, pady=5).pack(side=tk.RIGHT, padx=5)

    def create_world_dialog(self):
        win = tk.Toplevel(self.root)
        win.title("🔄 Создать новый мир")
        win.geometry("700x550")
        win.configure(bg=COLORS['bg_medium'])
        win.transient(self.root)
        win.grab_set()

        tk.Label(win, text="Название мира (папка):", bg=COLORS['bg_medium'], fg=COLORS['text_light']).pack(pady=(10,0))
        name_entry = tk.Entry(win, font=('Arial', 11), bg=COLORS['input_bg'], fg=COLORS['text_light'])
        name_entry.pack(pady=5)
        name_entry.insert(0, "Новый мир")

        notebook = ttk.Notebook(win)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        tabs = {}
        
        for fname, desc in WORLD_FILES.items():
            frame = ttk.Frame(notebook)
            notebook.add(frame, text=desc)
            text_widget = scrolledtext.ScrolledText(frame, wrap=tk.WORD, bg=COLORS['bg_medium'], fg=COLORS['text_light'], font=('Arial', 10), relief=tk.FLAT)
            text_widget.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            text_widget.insert(1.0, DEFAULT_TEMPLATES.get(fname, ""))
            text_widget.bind('<Control-v>', lambda e, tw=text_widget: tw.event_generate('<<Paste>>'))
            text_widget.bind('<Control-c>', lambda e, tw=text_widget: tw.event_generate('<<Copy>>'))
            text_widget.bind('<Button-3>', self.show_context_menu)
            tabs[fname] = text_widget

        def apply_new_world():
            name = name_entry.get().strip()
            if not name or (BASE_DIR / name).exists():
                messagebox.showerror("Ошибка", "Некорректное или занятое имя")
                return
            content = {fname: w.get(1.0, tk.END).strip() for fname, w in tabs.items()}
            save_world_files(BASE_DIR / name, content)
            save_history(BASE_DIR / name, [])
            win.destroy()
            self.load_world(name)
            self.refresh_world_combobox()

        btn_frame = tk.Frame(win, bg=COLORS['bg_medium'])
        btn_frame.pack(fill=tk.X, pady=10)
        tk.Button(btn_frame, text="✅ Создать мир", command=apply_new_world, bg=COLORS['accent'], fg='#1e1e1e', relief=tk.FLAT, padx=15, pady=5).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="❌ Отмена", command=win.destroy, bg=COLORS['button_bg'], fg=COLORS['text_light'], relief=tk.FLAT, padx=15, pady=5).pack(side=tk.LEFT, padx=5)

    def open_world_files(self):
        if not self.current_world_path: return
        win = tk.Toplevel(self.root)
        win.title("📁 Файлы мира")
        win.geometry("700x500")
        win.configure(bg=COLORS['bg_medium'])
        win.transient(self.root)
        win.grab_set()

        # Сброс состояния редактора файлов (на случай повторного открытия окна)
        self.current_editing_file = None
        self.current_editing_file_index = None
        self.file_editor_original_content = ""
        self.files_window = win

        left_frame = tk.Frame(win, bg=COLORS['bg_dark'], width=200)
        left_frame.pack(side=tk.LEFT, fill=tk.Y)
        left_frame.pack_propagate(False)
        
        tk.Label(left_frame, text="Выберите файл:", bg=COLORS['bg_dark'], fg=COLORS['text_light'], font=('Arial', 10, 'bold')).pack(pady=5)
        self.file_listbox = tk.Listbox(left_frame, bg=COLORS['bg_medium'], fg=COLORS['text_light'], selectbackground=COLORS['accent'], relief=tk.FLAT, font=('Arial', 10))
        self.file_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        for fname, desc in WORLD_FILES.items():
            self.file_listbox.insert(tk.END, f"{desc} ({fname})")

        right_frame = tk.Frame(win, bg=COLORS['bg_medium'])
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.file_editor = scrolledtext.ScrolledText(right_frame, wrap=tk.WORD, bg=COLORS['bg_medium'], fg=COLORS['text_light'], font=('Arial', 11), relief=tk.FLAT)
        self.file_editor.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.file_editor.bind('<Control-v>', lambda e: self.file_editor.event_generate('<<Paste>>'))
        self.file_editor.bind('<Control-c>', lambda e: self.file_editor.event_generate('<<Copy>>'))
        self.file_editor.bind('<Button-3>', self.show_context_menu)
        self.file_editor.bind('<<Modified>>', self.on_file_editor_modified)

        btn_frame = tk.Frame(right_frame, bg=COLORS['bg_medium'])
        btn_frame.pack(fill=tk.X, pady=5)
        tk.Button(btn_frame, text="💾 Сохранить изменения", command=self.save_current_file, bg=COLORS['button_bg'], fg=COLORS['text_light'], relief=tk.FLAT, padx=10, pady=5).pack(side=tk.LEFT, padx=5)
        self.unsaved_label = tk.Label(btn_frame, text="", bg=COLORS['bg_medium'], fg=COLORS['accent'], font=('Arial', 9, 'italic'))
        self.unsaved_label.pack(side=tk.LEFT, padx=10)

        self.file_listbox.bind('<<ListboxSelect>>', self.on_file_select)
        win.protocol("WM_DELETE_WINDOW", self.close_files_window)

        if self.file_listbox.size() > 0:
            self.file_listbox.selection_set(0)
            self._load_file_into_editor(0)

    def on_file_editor_modified(self, event):
        # Виджет сам взводит флаг modified при любом изменении текста — сбрасываем его,
        # чтобы событие срабатывало и при следующем изменении тоже
        self.file_editor.edit_modified(False)
        self.update_unsaved_indicator()

    def has_unsaved_file_changes(self):
        if not hasattr(self, 'file_editor') or self.current_editing_file is None:
            return False
        current_content = self.file_editor.get(1.0, tk.END).strip()
        return current_content != self.file_editor_original_content.strip()

    def update_unsaved_indicator(self):
        if not hasattr(self, 'unsaved_label') or not self.unsaved_label.winfo_exists():
            return
        if self.has_unsaved_file_changes():
            self.unsaved_label.configure(text="● Есть несохранённые изменения")
        else:
            self.unsaved_label.configure(text="")

    def _load_file_into_editor(self, index):
        fname = list(WORLD_FILES.keys())[index]
        path = self.current_world_path / fname
        content = path.read_text(encoding='utf-8') if path.exists() else ""
        self.file_editor.delete(1.0, tk.END)
        self.file_editor.insert(1.0, content)
        self.file_editor.edit_modified(False)
        self.current_editing_file = fname
        self.current_editing_file_index = index
        self.file_editor_original_content = content
        self.update_unsaved_indicator()

    def on_file_select(self, event):
        sel = self.file_listbox.curselection()
        if not sel: return
        new_index = sel[0]

        if new_index == self.current_editing_file_index:
            return

        if not self.has_unsaved_file_changes():
            self._load_file_into_editor(new_index)
            return

        # Есть несохранённые изменения — спрашиваем, что делать
        old_fname = self.current_editing_file
        choice = messagebox.askyesnocancel(
            "Несохранённые изменения",
            f"В файле «{WORLD_FILES.get(old_fname, old_fname)}» есть несохранённые изменения.\n\n"
            f"Сохранить их перед переключением?"
        )

        if choice is None:
            # Отмена — возвращаем выбор списка на текущий файл
            self.file_listbox.selection_clear(0, tk.END)
            self.file_listbox.selection_set(self.current_editing_file_index)
            return
        elif choice:
            self.save_current_file()

        self._load_file_into_editor(new_index)

    def close_files_window(self):
        if self.has_unsaved_file_changes():
            choice = messagebox.askyesnocancel(
                "Несохранённые изменения",
                f"В файле «{WORLD_FILES.get(self.current_editing_file, self.current_editing_file)}» есть несохранённые изменения.\n\n"
                f"Сохранить их перед закрытием?"
            )
            if choice is None:
                return  # Не закрываем окно
            elif choice:
                self.save_current_file()
        self.files_window.destroy()

    def save_current_file(self):
        if not getattr(self, 'current_editing_file', None): return
        content = self.file_editor.get(1.0, tk.END)
        (self.current_world_path / self.current_editing_file).write_text(content, encoding='utf-8')
        self.file_editor_original_content = content.strip()
        self.file_editor.edit_modified(False)
        self.update_unsaved_indicator()
        self.add_system_message(f"✅ Файл {self.current_editing_file} сохранён")

    def open_ai_settings(self):
        win = tk.Toplevel(self.root)
        win.title("⚙️ Настройки ИИ")
        win.geometry("400x480")
        win.configure(bg=COLORS['bg_medium'])
        win.transient(self.root)
        win.grab_set()

        tk.Label(win, text="Режим вывода текста:", bg=COLORS['bg_medium'], fg=COLORS['text_light'], font=('Arial', 10, 'bold')).pack(anchor=tk.W, padx=10, pady=(10, 2))
        stream_var = tk.BooleanVar(value=self.stream_mode)
        stream_cb = tk.Checkbutton(
            win, text="Потоковый ответ (Streaming)", variable=stream_var,
            bg=COLORS['bg_medium'], fg=COLORS['text_light'],
            selectcolor=COLORS['bg_dark'], activebackground=COLORS['bg_medium'],
            activeforeground=COLORS['text_light']
        )
        stream_cb.pack(anchor=tk.W, padx=10, pady=5)

        tk.Label(win, text="Температура (0.0 - 2.0):", bg=COLORS['bg_medium'], fg=COLORS['text_light']).pack(anchor=tk.W, padx=10, pady=5)
        temp_var = tk.DoubleVar(value=self.temperature)
        tk.Scale(win, from_=0.0, to=2.0, resolution=0.1, orient=tk.HORIZONTAL, variable=temp_var, bg=COLORS['bg_medium'], fg=COLORS['text_light'], highlightthickness=0, length=300).pack(fill=tk.X, padx=10, pady=5)

        tk.Label(win, text="Максимум токенов в ответе (от 25 до 2500):", bg=COLORS['bg_medium'], fg=COLORS['text_light']).pack(anchor=tk.W, padx=10, pady=5)
        tokens_var = tk.IntVar(value=self.max_tokens)
        tk.Spinbox(win, from_=25, to=2500, increment=25, textvariable=tokens_var, bg=COLORS['bg_light'], fg=COLORS['text_light'], relief=tk.FLAT, width=10).pack(anchor=tk.W, padx=10, pady=5)

        tk.Label(win, text="Размер контекста ИИ (от 4096 до 131072):", bg=COLORS['bg_medium'], fg=COLORS['text_light']).pack(anchor=tk.W, padx=10, pady=5)
        context_var = tk.IntVar(value=self.context_size)
        tk.Scale(win, from_=4096, to=131072, resolution=1024, orient=tk.HORIZONTAL, variable=context_var, bg=COLORS['bg_medium'], fg=COLORS['text_light'], highlightthickness=0, length=300).pack(fill=tk.X, padx=10, pady=5)

        tk.Label(win, text="Обновлять Краткое содержание каждые N ходов:", bg=COLORS['bg_medium'], fg=COLORS['text_light']).pack(anchor=tk.W, padx=10, pady=5)

        interval_options = [5, 10, 15, 20]
        current_interval = self.summary_interval
        if current_interval not in interval_options:
            interval_options = sorted(interval_options + [current_interval])

        interval_var = tk.IntVar(value=current_interval)
        interval_combo = ttk.Combobox(
            win,
            values=interval_options,
            textvariable=interval_var,
            state="readonly",
            width=10
        )
        interval_combo.pack(anchor=tk.W, padx=10, pady=5)
        interval_combo.set(current_interval)

        def apply_settings():
            self.stream_mode = stream_var.get()
            self.temperature = temp_var.get()
            self.max_tokens = tokens_var.get()
            self.context_size = context_var.get()
            try:
                self.summary_interval = int(interval_var.get())
            except:
                pass
            self.save_global_settings()
            self.add_system_message(f"⚙️ Настройки сохранены. Стриминг: {'ВКЛ' if self.stream_mode else 'ВЫКЛ'}.")
            win.destroy()

        tk.Button(win, text="💾 Сохранить", command=apply_settings, bg=COLORS['button_bg'], fg=COLORS['text_light'], relief=tk.FLAT, padx=15, pady=5).pack(pady=15)

    def quit_app(self):
        if messagebox.askyesno("Выход", "Действительно выйти из игры?"):
            self.on_closing()

    # ======== ОТМЕНА И РЕГЕНЕРАЦИЯ ========
    def undo_action(self):
        if self.processing or not self.history or not self.current_world_path: return
        last_msg = self.history[-1]
        if last_msg.startswith("Мастер:"):
            self.history.pop()
            if self.turns_since_summary > 0: self.turns_since_summary -= 1
        elif last_msg.startswith("Игрок:"):
            self.history.pop()
            if self.turns_since_summary > 0: self.turns_since_summary -= 1
        else:
            self.history.pop()
        save_history(self.current_world_path, self.history)
        self.refresh_chat_display()
        self.add_system_message("⏪ Последнее сообщение удалено.")

    def regenerate_action(self):
        if self.processing or not self.history or not self.current_world_path:
            return
        
        if self.history[-1].startswith("Мастер:"):
            self.history.pop()
        
        last_player_input = ""
        if self.history and self.history[-1].startswith("Игрок:"):
            last_player_input = self.history[-1][len("Игрок:"):].strip()
            
        save_history(self.current_world_path, self.history)
        self.refresh_chat_display()
        
        self.processing = True
        self.send_button.configure(state='disabled', text="⏳ Думаю...")
        self.status_label.configure(text="● Generation...", fg=COLORS['system_color'])
        Thread(target=self.process_action, args=(last_player_input,), daemon=True).start()
        
    def edit_last_dm_message(self):
        if not self.current_world_path or not self.history:
            messagebox.showwarning("Внимание", "История пуста или мир не выбран.")
            return
        dm_index = -1
        for i in range(len(self.history) - 1, -1, -1):
            if self.history[i].startswith("Мастер:"):
                dm_index = i
                break
        if dm_index == -1:
            messagebox.showwarning("Внимание", "В текущей истории нет сообщений от Мастера.")
            return

        current_text = self.history[dm_index][len("Мастер:"):].strip()
        win = tk.Toplevel(self.root)
        win.title("✏️ Редактировать ответ Мастера")
        win.geometry("600x700")
        win.configure(bg=COLORS['bg_medium'])
        win.transient(self.root)
        win.grab_set()

        tk.Label(win, text="Редактирование последнего сообщения Мастера:", bg=COLORS['bg_medium'], fg=COLORS['text_light'], font=('Arial', 10, 'bold')).pack(pady=(10, 5), anchor=tk.W, padx=15)
        
        editor = scrolledtext.ScrolledText(win, wrap=tk.WORD, bg=COLORS['bg_dark'], fg=COLORS['text_light'], insertbackground=COLORS['text_light'], selectbackground=COLORS['accent'], font=('Arial', 11), relief=tk.FLAT, padx=10, pady=10)
        editor.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)
        editor.insert(tk.END, current_text)
        editor.focus_set()
        editor.bind('<Button-3>', self.show_context_menu)

        def save_edited_msg():
            new_text = editor.get(1.0, tk.END).strip()
            if not new_text: return
            self.history[dm_index] = f"Мастер: {new_text}"
            save_history(self.current_world_path, self.history)
            self.refresh_chat_display()
            win.destroy()
            self.add_system_message("📝 Ответ Мастера успешно отредактирован и сохранен.")

        btn_frame = tk.Frame(win, bg=COLORS['bg_medium'])
        btn_frame.pack(fill=tk.X, pady=15, padx=15)
        tk.Button(btn_frame, text="✅ Сохранить", command=save_edited_msg, bg=COLORS['accent'], fg='#1e1e1e', font=('Arial', 10, 'bold'), relief=tk.FLAT, padx=20, pady=6).pack(side=tk.LEFT)
        tk.Button(btn_frame, text="❌ Отмена", command=win.destroy, bg=COLORS['button_bg'], fg=COLORS['text_light'], font=('Arial', 10), relief=tk.FLAT, padx=15, pady=6).pack(side=tk.RIGHT)

    def force_summary(self):
        if self.processing or not self.current_world_path: return
        self.turns_since_summary = 0
        self.update_summary_label()
        self.add_system_message("📝 Принудительное обновление краткого содержания...")
        Thread(target=self.generate_global_summary, daemon=True).start()

    def show_last_prompt(self):
        if not self.last_sent_prompt:
            messagebox.showinfo("Промпт", "Пока не было ни одного запроса к ИИ в этом мире.")
            return

        data = self.last_sent_prompt
        full_text = (
            f"=== ВРЕМЯ ЗАПРОСА ===\n{data['time']}\n\n"
            f"=== ПРИМЕРНОЕ КОЛ-ВО ТОКЕНОВ (контекст) ===\n{data['tokens']}\n\n"
            f"=== SYSTEM (инструкции + мир + история) ===\n{data['system']}\n\n"
            f"=== USER (сообщение игрока) ===\n{data['user']}\n"
        )

        win = tk.Toplevel(self.root)
        win.title("📋 Последний промпт, отправленный ИИ")
        win.geometry("750x650")
        win.configure(bg=COLORS['bg_medium'])
        win.transient(self.root)
        win.grab_set()

        tk.Label(
            win,
            text=f"Полный текст, отправленный модели ({data['time']}, ~{data['tokens']} токенов):",
            bg=COLORS['bg_medium'], fg=COLORS['text_light'], font=('Arial', 10, 'bold')
        ).pack(anchor=tk.W, padx=15, pady=(10, 5))

        viewer = scrolledtext.ScrolledText(
            win, wrap=tk.WORD, bg=COLORS['bg_dark'], fg=COLORS['text_light'],
            insertbackground=COLORS['text_light'], selectbackground=COLORS['accent'],
            font=('Consolas', 10), relief=tk.FLAT, padx=10, pady=10
        )
        viewer.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)
        viewer.insert(1.0, full_text)
        viewer.configure(state='disabled')
        viewer.bind('<Button-3>', self.show_context_menu)

        def copy_to_clipboard():
            self.root.clipboard_clear()
            self.root.clipboard_append(full_text)
            self.add_system_message("📋 Промпт скопирован в буфер обмена.")

        btn_frame = tk.Frame(win, bg=COLORS['bg_medium'])
        btn_frame.pack(fill=tk.X, padx=15, pady=10)
        tk.Button(
            btn_frame, text="📋 Скопировать всё", command=copy_to_clipboard,
            bg=COLORS['button_bg'], fg=COLORS['text_light'], relief=tk.FLAT, padx=10, pady=5
        ).pack(side=tk.LEFT, padx=5)
        tk.Button(
            btn_frame, text="❌ Закрыть", command=win.destroy,
            bg=COLORS['button_bg'], fg=COLORS['text_light'], relief=tk.FLAT, padx=10, pady=5
        ).pack(side=tk.RIGHT, padx=5)

    # ======== ОБРАБОТЧИК ОБРЫВОВ СТРОК (НЕЙРО-ХЕЙЛИНГ) ========
    def fix_truncated_text(self, text: str) -> str:
        """Обрезает незаконченное на полуслове предложение, сохраняя разметку."""
        text = text.strip()
        if not text: 
            return text
        
        # Если текст уже заканчивается на точку, восклицание, вопрос, кавычку или звездочку действий — он целый
        if text[-1] in ['.', '!', '?', '…', '"', '»', '*', ')', ']']:
            return text
        
        # Ищем последние позиции полноценных знаков завершения предложения
        punctuation_marks = [text.rfind('.'), text.rfind('!'), text.rfind('?'), text.rfind('…')]
        last_pos = max(punctuation_marks)
        
        if last_pos != -1:
            # Отсекаем оборванный кусок
            cut_text = text[:last_pos + 1].strip()
            
            # Корректируем баланс звездочек (чтобы описание действий *...* не ломало шрифт чата)
            if text.count('*') % 2 == 0 and cut_text.count('*') % 2 != 0:
                cut_text += ' *'
                
            # Если после обрезки остался нормальный кусок текста — возвращаем его
            if len(cut_text) > 15:
                return cut_text
                
        # Если нормальных знаков препинания вообще нет — просто добавляем красивое многоточие
        return text + "..."

    # ======== ОБРАБОТКА И ОТПРАВКА ========
    def send_action(self):
        if self.processing or not self.current_world_path: return
        user_input = self.input_field.get("1.0", tk.END).strip()
        self.input_field.delete("1.0", tk.END)
        
        if user_input:
            self.add_player_message(user_input)
            
        self.turns_since_summary += 1
        self.update_summary_label()
        self.processing = True
        self.send_button.configure(state='disabled', text="⏳ Думаю...")
        self.status_label.configure(text="● Generation...", fg=COLORS['system_color'])
        Thread(target=self.process_action, args=(user_input,), daemon=True).start()

    def start_dm_stream(self):
        self.text_area.configure(state='normal')
        # Вставляем начало сообщения и перенос строки, если нужно
        self.text_area.insert(tk.END, "\nМастер: ", 'dm')
        
        # 🦺 ВАЖНО: Запоминаем точный индекс (строка.символ), 
        # откуда начнется текст ответа ИИ
        self.stream_start_index = self.text_area.index("end-1c")
        
        self.text_area.configure(state='disabled')
        self.text_area.see(tk.END)

    def append_to_dm_stream(self, chunk):
        self.text_area.configure(state='normal')
        # Вставляем сырые кусочки текста по мере загрузки
        self.text_area.insert(tk.END, chunk, 'dm')
        self.text_area.configure(state='disabled')
        self.text_area.see(tk.END)

    def finalize_dm_stream(self, final_text):
        self.text_area.configure(state='normal')
        
        # 🦺 ВАЖНО: Удаляем весь "черновой" текст, который набежал во время стрима
        if hasattr(self, 'stream_start_index'):
            self.text_area.delete(self.stream_start_index, tk.END)
        
        # Вставляем чистовик (уже без JSON, обрезанных фраз и т.д.)
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

            # Точный подсчет отправляемых токенов контекста перед запросом
            system_final_content = f"""{context}\nИСТОРИЯ ТЕКУЩЕЙ ИГРОВОЙ СЕССИИ:\n{history_text}"""
            prompt_tokens = count_tokens(system_final_content) + count_tokens(user_content)

            # Сохраняем полный промпт для просмотра пользователем (кнопка "📋 Промпт")
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
                "stop": ["\nИгрок:", "Игрок:", "<|im_end|>", "<|eot_id|>", "```", "---"],
                "enable_thinking": False,
                "frequency_penalty": 0.1,
                "presence_penalty": 0.1
            }

            # --- НАЧАЛО ОБРАБОТКИ ОТВЕТА ---
            if self.stream_mode:
                response = requests.post(API_URL, json=payload, stream=True, timeout=120)
                response.raise_for_status()

                self.root.after(0, self.start_dm_stream)
                raw_narration = ""
                decoder = codecs.getincrementaldecoder('utf-8')('ignore')
                buffer = ""  # Буфер для накопления неполных строк и предотвращения дублирования
                
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
                            delta = data['choices'][0].get('delta', {})
                            content = delta.get('content', '')
                            if content:
                                # Хак против галлюцинаций Gemma: убираем иероглифы и системный мусор
                                content = re.sub(r'[\uac00-\ud7a3\u4e00-\u9fff]', '', content) # Корейский/китайский
                                content = content.replace('$', '').replace('{', '').replace('}', '')
                                
                                if content: # Если после очистки что-то осталось
                                    raw_narration += content
                                    self.root.after(0, lambda c=content: self.append_to_dm_stream(c))
                        except json.JSONDecodeError:
                            pass
                            
                # Обработка возможного остатка в буфере после завершения цикла
                if buffer and buffer.startswith("data: "):
                    try:
                        json_str = buffer[6:].strip()
                        if json_str != "[DONE]":
                            data = json.loads(json_str)
                            content = data['choices'][0].get('delta', {}).get('content', '')
                            if content:
                                raw_narration += content
                                self.root.after(0, lambda c=content: self.append_to_dm_stream(c))
                    except:
                        pass
                        
                ai_text = raw_narration.strip()
            else:
                response = requests.post(API_URL, json=payload, timeout=120)
                response.raise_for_status()
                
                ai_text = response.json()['choices'][0]['message']['content'].strip()
                self.root.after(0, self.start_dm_stream)

            # --- ОБЩАЯ ОЧИСТКА, ФИЛЬТРАЦИЯ И НЕЙРО-ХЕЙЛИНГ ОБРЫВОВ ---
            if not ai_text:
                self.root.after(0, lambda: self.add_system_message("⚠️ Модель вернула пустой ответ."))
                return

            ai_text = re.sub(r'^(Мастер|AI|Narrator|DM|ИИ|Master):\s*', '', ai_text, flags=re.IGNORECASE).strip()

            cleaned_text = ai_text.replace("```json", "").replace("```", "").strip()
            start = cleaned_text.find('{')
            end = cleaned_text.rfind('}') + 1
            final_narration = ai_text
            # --- ОЧИСТКА ОТ ГАЛЛЮЦИНАЦИЙ И МУСОРА ---
            # 1. Удаляем переменные и формулы вида $text$ или ${text}$
            final_narration = re.sub(r'\$\{?[^}]*\}?\$', '', final_narration)
            final_narration = final_narration.replace('$', '')
            
            # 2. Удаляем корейские (Хангыль) и китайские иероглифы
            final_narration = re.sub(r'[\uac00-\ud7a3\u4e00-\u9fff]', '', final_narration)
            
            # 3. Убираем висящие пустые скобки, оставшиеся после удаления (например, от переменных)
            final_narration = re.sub(r'\(\s*\)', '', final_narration)
            final_narration = final_narration.strip()
            # ----------------------------------------

            # Применяем обработчик обрывов текста (отсекаем недописанные фразы)
            final_narration = self.fix_truncated_text(final_narration)
            
            if start >= 0 and end > start:
                json_str = cleaned_text[start:end]
                try:
                    result = json.loads(json_str, strict=False)
                    final_narration = result.get('narration', ai_text)
                except:
                    narration_match = re.search(r'"narration"\s*:\s*"((?:[^"\\]|\\.)*)"', json_str, re.DOTALL)
                    if narration_match:
                        final_narration = narration_match.group(1)
                        
            final_narration = final_narration.replace('\n', '\n').replace('\\"', '"').strip()

            # Применяем обработчик обрывов текста (отсекаем недописанные фразы)
            final_narration = self.fix_truncated_text(final_narration)

            # Выводим красивую, исправленную версию в текстовое поле чата
            self.root.after(0, lambda f=final_narration: self.finalize_dm_stream(f))

            self.history.append(f"Мастер: {final_narration}")
            save_history(self.current_world_path, self.history)

            # Расчитываем генерацию и выводим статистику токенов в чат
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
            self.root.after(0, lambda: self.add_system_message(f"❌ Ошибка: {str(e)}"))
        finally:
            self.root.after(0, self.processing_end)

    def generate_global_summary(self):
        try:
            if not self.current_world_path: return
            
            summary_path = self.current_world_path / "summary.txt"
            old_summary = summary_path.read_text(encoding='utf-8').strip() if summary_path.exists() else "Отсутствует."
            
            # === ЗАГРУЖАЕМ ФАЙЛ С ПЕРСОНАЖАМИ ===
            characters_path = self.current_world_path / "characters.txt"
            characters_content = characters_path.read_text(encoding='utf-8').strip() if characters_path.exists() else "Информация о персонажах отсутствует."
            
            # === ФОРМИРУЕМ ПРОМТ С ПЕРСОНАЖАМИ ===
            prompt_template_base = f"""Перед тобой история текстовой ролевой игры, её старое краткое содержание и информация о персонажах.
Твоя задача: составить обновленное, чистое и емкое КРАТКОЕ СОДЕРЖАНИЕ (summary).
ПРАВИЛА:
1. Сформируй кратую исторую в хронологическомы порядке с описанием действий, событий.
2. Игнорируй мелкую рутину, лишние диалоги и описания комнат.
3. Пиши структурированно, лаконично, тезисно или по хронологическим абзацам.
4. Обязательно учти информацию из СТАРОГО краткого содержания.
5. УЧТИ ИНФОРМАЦИЮ О ПЕРСОНАЖАХ: Не описывай уже описанных персонажей.


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

            # === ФИНАЛЬНЫЙ ПРОМТ С ПЕРСОНАЖАМИ ===
            prompt = f"""Перед тобой история текстовой ролевой игры, её старое краткое содержание и информация о персонажах.
Твоя задача: составить обновленное, чистое и емкое КРАТКОЕ СОДЕРЖАНИЕ (summary).
ПРАВИЛА:
1. Сформируй кратую исторую в хронологическомы порядке с описанием действий, событий.
2. Игнорируй мелкую рутину, лишние диалоги и описания комнат.
3. Пиши структурированно, лаконично, тезисно.
4. Обязательно учти информацию из СТАРОГО краткого содержания.
5. УЧТИ ИНФОРМАЦИЮ О ПЕРСОНАЖАХ: Не описывай уже описанных персонажей.

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
                
        except requests.exceptions.ConnectionError:
            self.root.after(0, lambda: self.add_system_message("❌ Ошибка сети: Не удалось связаться с сервером ИИ для суммаризации."))
        except requests.exceptions.Timeout:
            self.root.after(0, lambda: self.add_system_message("⏳ Таймаут: Сервер ИИ слишком долго генерировал саммари."))
        except Exception as e:
            self.root.after(0, lambda: self.add_system_message(f"⚠️ Не удалось автоматически обновить саммари: {str(e)}"))

    def processing_end(self):
        self.processing = False
        self.send_button.configure(state='normal', text="▶ Отправить")
        self.status_label.configure(text="● Готов", fg=COLORS['player_color'])
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
    root = tk.Tk()
    app = DungeonApp(root)
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
    y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
    root.geometry(f'+{x}+{y}')
    root.mainloop()

if __name__ == "__main__":
    main()