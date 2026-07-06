import shutil
from threading import Thread

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox

from .config import BASE_DIR, COLORS, DEFAULT_TEMPLATES, WORLD_FILES
from .storage import get_world_list, save_history, save_world_files


class DialogMixin:
    def manage_worlds(self):
        win = ctk.CTkToplevel(self.root)
        win.title("🔄 Управление мирами")
        win.geometry("500x400")
        win.transient(self.root)
        win.grab_set()

        ctk.CTkLabel(win, text="Ваши миры:", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)

        listbox = tk.Listbox(
            win,
            bg=COLORS["listbox_bg"],
            fg="white",
            selectbackground=COLORS["listbox_sel"],
            relief=tk.FLAT,
            font=("Arial", 12),
            highlightthickness=0,
            borderwidth=0,
        )
        listbox.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 10))

        for w in get_world_list():
            listbox.insert(tk.END, w)

        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.pack(fill=ctk.X, padx=20, pady=10)

        def switch_to_world():
            sel = listbox.curselection()
            if not sel:
                return
            name = listbox.get(sel[0])
            win.destroy()
            self.load_world(name)

        def delete_world():
            sel = listbox.curselection()
            if not sel:
                return
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
                    self.turns_since_memory = 0
                    self.memory_bank = {"last_indexed_turn": 0, "entries": []}
                    self.update_summary_label()
                    self.update_memory_label()
                    self.refresh_chat_display()

        ctk.CTkButton(btn_frame, text="Загрузить", command=switch_to_world).pack(side=ctk.LEFT, padx=5)
        ctk.CTkButton(
            btn_frame,
            text="Удалить",
            command=delete_world,
            fg_color=COLORS["danger"],
            hover_color=COLORS["danger_hover"],
        ).pack(side=ctk.LEFT, padx=5)
        ctk.CTkButton(btn_frame, text="Создать", command=lambda: [win.destroy(), self.create_world_dialog()]).pack(
            side=ctk.LEFT, padx=5
        )
        ctk.CTkButton(btn_frame, text="Закрыть", command=win.destroy, fg_color="gray").pack(side=ctk.RIGHT, padx=5)

    def create_world_dialog(self):
        win = ctk.CTkToplevel(self.root)
        win.title("🔄 Создать новый мир")
        win.geometry("750x600")
        win.transient(self.root)
        win.grab_set()

        ctk.CTkLabel(win, text="Название мира (папка):").pack(pady=(10, 0))
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
            text_widget.bind("<Button-3>", self.show_context_menu)
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
        ctk.CTkButton(
            btn_frame, text="✅ Создать", command=apply_new_world, fg_color=COLORS["accent"], text_color="black"
        ).pack(side=ctk.LEFT, padx=5)
        ctk.CTkButton(btn_frame, text="❌ Отмена", command=win.destroy, fg_color="gray").pack(side=ctk.RIGHT, padx=5)

    def open_world_files(self):
        if not self.current_world_path:
            return
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

        self.file_listbox = tk.Listbox(
            left_frame,
            bg=COLORS["listbox_bg"],
            fg="white",
            selectbackground=COLORS["listbox_sel"],
            relief=tk.FLAT,
            font=("Arial", 11),
            highlightthickness=0,
            borderwidth=0,
        )
        self.file_listbox.pack(fill=ctk.BOTH, expand=True, padx=5, pady=5)
        for _, desc in WORLD_FILES.items():
            self.file_listbox.insert(tk.END, desc)

        right_frame = ctk.CTkFrame(win)
        right_frame.pack(side=ctk.RIGHT, fill=ctk.BOTH, expand=True, padx=(0, 10), pady=10)

        self.file_editor = ctk.CTkTextbox(right_frame, wrap=tk.WORD, font=ctk.CTkFont(size=14))
        self.file_editor.pack(fill=ctk.BOTH, expand=True, padx=10, pady=10)
        self.file_editor.bind("<Button-3>", self.show_context_menu)
        self.file_editor._textbox.bind("<<Modified>>", self.on_file_editor_modified)

        btn_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        btn_frame.pack(fill=ctk.X, pady=10, padx=10)

        ctk.CTkButton(btn_frame, text="💾 Сохранить", command=self.save_current_file).pack(side=ctk.LEFT, padx=5)
        self.unsaved_label = ctk.CTkLabel(btn_frame, text="", text_color=COLORS["accent"])
        self.unsaved_label.pack(side=ctk.LEFT, padx=10)

        self.file_listbox.bind("<<ListboxSelect>>", self.on_file_select)
        win.protocol("WM_DELETE_WINDOW", self.close_files_window)

        if self.file_listbox.size() > 0:
            self.file_listbox.selection_set(0)
            self._load_file_into_editor(0)

    def on_file_editor_modified(self, event):
        self.file_editor._textbox.edit_modified(False)
        self.update_unsaved_indicator()

    def has_unsaved_file_changes(self):
        if not hasattr(self, "file_editor") or self.current_editing_file is None:
            return False
        current_content = self.file_editor.get("1.0", tk.END).strip()
        return current_content != self.file_editor_original_content.strip()

    def update_unsaved_indicator(self):
        if not hasattr(self, "unsaved_label") or not self.unsaved_label.winfo_exists():
            return
        if self.has_unsaved_file_changes():
            self.unsaved_label.configure(text="● Есть несохранённые изменения")
        else:
            self.unsaved_label.configure(text="")

    def _load_file_into_editor(self, index):
        fname = list(WORLD_FILES.keys())[index]
        path = self.current_world_path / fname
        content = path.read_text(encoding="utf-8") if path.exists() else ""
        self.file_editor.delete("1.0", tk.END)
        self.file_editor.insert("1.0", content)
        self.file_editor._textbox.edit_modified(False)
        self.current_editing_file = fname
        self.current_editing_file_index = index
        self.file_editor_original_content = content
        self.update_unsaved_indicator()

    def on_file_select(self, event):
        sel = self.file_listbox.curselection()
        if not sel:
            return
        new_index = sel[0]

        if new_index == self.current_editing_file_index:
            return
        if not self.has_unsaved_file_changes():
            self._load_file_into_editor(new_index)
            return

        old_fname = self.current_editing_file
        choice = messagebox.askyesnocancel(
            "Внимание", f"В файле «{WORLD_FILES.get(old_fname, old_fname)}» есть изменения. Сохранить?"
        )
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
            if choice is None:
                return
            elif choice:
                self.save_current_file()
        self.files_window.destroy()

    def save_current_file(self):
        if not getattr(self, "current_editing_file", None):
            return
        content = self.file_editor.get("1.0", tk.END)
        (self.current_world_path / self.current_editing_file).write_text(content, encoding="utf-8")
        self.file_editor_original_content = content.strip()
        self.file_editor._textbox.edit_modified(False)
        self.update_unsaved_indicator()
        self.add_system_message(f"✅ Файл {self.current_editing_file} сохранён")

    def open_ai_settings(self):
        win = ctk.CTkToplevel(self.root)
        win.title("⚙️ Настройки ИИ")
        win.geometry("450x620")
        win.transient(self.root)
        win.grab_set()

        stream_var = ctk.BooleanVar(value=self.stream_mode)
        ctk.CTkCheckBox(win, text="Потоковый ответ (Streaming)", variable=stream_var).pack(anchor=tk.W, padx=20, pady=(20, 10))

        ctk.CTkLabel(win, text="Температура (0.0 - 2.0):").pack(anchor=tk.W, padx=20)
        temp_val_lbl = ctk.CTkLabel(win, text=f"{self.temperature:.1f}", text_color=COLORS["accent"])
        temp_val_lbl.pack(anchor=tk.E, padx=20)

        def update_temp_lbl(val):
            temp_val_lbl.configure(text=f"{val:.1f}")

        temp_slider = ctk.CTkSlider(win, from_=0.0, to=2.0, number_of_steps=20, command=update_temp_lbl)
        temp_slider.set(self.temperature)
        temp_slider.pack(fill=ctk.X, padx=20, pady=(0, 15))

        ctk.CTkLabel(win, text="Макс. токенов в ответе:").pack(anchor=tk.W, padx=20)
        tokens_entry = ctk.CTkEntry(win)
        tokens_entry.pack(fill=ctk.X, padx=20, pady=(5, 15))
        tokens_entry.insert(0, str(self.max_tokens))

        ctk.CTkLabel(win, text="Размер контекста:").pack(anchor=tk.W, padx=20)
        ctx_val_lbl = ctk.CTkLabel(win, text=f"{self.context_size}", text_color=COLORS["accent"])
        ctx_val_lbl.pack(anchor=tk.E, padx=20)

        def update_ctx_lbl(val):
            ctx_val_lbl.configure(text=f"{int(val)}")

        ctx_slider = ctk.CTkSlider(win, from_=4096, to=131072, number_of_steps=31, command=update_ctx_lbl)
        ctx_slider.set(self.context_size)
        ctx_slider.pack(fill=ctk.X, padx=20, pady=(0, 15))

        ctk.CTkLabel(win, text="Суммаризация (каждые N ходов):").pack(anchor=tk.W, padx=20)
        interval_var = ctk.StringVar(value=str(self.summary_interval))
        ctk.CTkOptionMenu(win, variable=interval_var, values=["5", "10", "15", "20"]).pack(anchor=tk.W, padx=20, pady=5)

        ctk.CTkLabel(win, text="Банк памяти (индексация каждые N ходов):").pack(anchor=tk.W, padx=20, pady=(10, 0))
        memory_interval_var = ctk.StringVar(value=str(self.memory_interval))
        ctk.CTkOptionMenu(win, variable=memory_interval_var, values=["3", "5", "10", "15"]).pack(
            anchor=tk.W, padx=20, pady=5
        )

        ctk.CTkLabel(win, text="Макс. воспоминаний в промпте:").pack(anchor=tk.W, padx=20)
        memory_top_k_var = ctk.StringVar(value=str(self.memory_top_k))
        ctk.CTkOptionMenu(win, variable=memory_top_k_var, values=["3", "5", "7", "10"]).pack(anchor=tk.W, padx=20, pady=5)

        def apply_settings():
            self.stream_mode = stream_var.get()
            self.temperature = temp_slider.get()
            self.context_size = int(ctx_slider.get())
            try:
                self.max_tokens = int(tokens_entry.get())
            except:
                pass
            try:
                self.summary_interval = int(interval_var.get())
            except:
                pass
            try:
                self.memory_interval = int(memory_interval_var.get())
            except:
                pass
            try:
                self.memory_top_k = int(memory_top_k_var.get())
            except:
                pass
            self.save_global_settings()
            self.update_memory_label()
            self.add_system_message(f"⚙️ Настройки сохранены. Стриминг: {'ВКЛ' if self.stream_mode else 'ВЫКЛ'}.")
            win.destroy()

        ctk.CTkButton(win, text="💾 Сохранить", command=apply_settings).pack(pady=20)

    def quit_app(self):
        if messagebox.askyesno("Выход", "Действительно выйти из игры?"):
            self.on_closing()

    def edit_last_dm_message(self):
        if not self.current_world_path or not self.history:
            return
        dm_index = -1
        for i in range(len(self.history) - 1, -1, -1):
            if self.history[i].startswith("Мастер:"):
                dm_index = i
                break
        if dm_index == -1:
            return

        current_text = self.history[dm_index][len("Мастер:") :].strip()
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
        editor.bind("<Button-3>", self.show_context_menu)

        def save_edited_msg():
            new_text = editor.get("1.0", tk.END).strip()
            if not new_text:
                return
            self.history[dm_index] = f"Мастер: {new_text}"
            save_history(self.current_world_path, self.history)
            self.refresh_chat_display()
            win.destroy()
            self.add_system_message("📝 Ответ Мастера изменен.")

        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.pack(fill=ctk.X, pady=15, padx=15)
        ctk.CTkButton(
            btn_frame, text="✅ Сохранить", command=save_edited_msg, fg_color=COLORS["accent"], text_color="black"
        ).pack(side=ctk.LEFT)
        ctk.CTkButton(btn_frame, text="❌ Отмена", command=win.destroy, fg_color="gray").pack(side=ctk.RIGHT)

    def force_summary(self):
        if self.processing or not self.current_world_path:
            return
        self.turns_since_summary = 0
        self.update_summary_label()
        self.add_system_message("📝 Принудительное обновление краткого содержания...")
        Thread(target=self.generate_global_summary, daemon=True).start()

    def show_last_prompt(self):
        if not self.last_sent_prompt:
            messagebox.showinfo("Промпт", "Нет данных о запросе.")
            return

        data = self.last_sent_prompt
        full_text = (
            f"=== ВРЕМЯ ЗАПРОСА ===\n{data['time']}\n\n"
            f"=== ПРИМЕРНОЕ КОЛ-ВО ТОКЕНОВ ===\n{data['tokens']}\n\n"
            f"=== SYSTEM ===\n{data['system']}\n\n"
            f"=== USER ===\n{data['user']}\n"
        )

        win = ctk.CTkToplevel(self.root)
        win.title("📋 Последний промпт")
        win.geometry("750x650")
        win.transient(self.root)
        win.grab_set()

        viewer = ctk.CTkTextbox(win, wrap=tk.WORD, font=ctk.CTkFont(family="Consolas", size=12))
        viewer.pack(fill=ctk.BOTH, expand=True, padx=15, pady=15)
        viewer.insert("1.0", full_text)
        viewer.configure(state="disabled")

        def copy_to_clipboard():
            self.root.clipboard_clear()
            self.root.clipboard_append(full_text)
            self.add_system_message("📋 Промпт скопирован.")

        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.pack(fill=ctk.X, padx=15, pady=(0, 15))
        ctk.CTkButton(btn_frame, text="📋 Копировать", command=copy_to_clipboard).pack(side=ctk.LEFT)
        ctk.CTkButton(btn_frame, text="❌ Закрыть", command=win.destroy, fg_color="gray").pack(side=ctk.RIGHT)

    def show_memory_bank(self):
        if not self.current_world_path:
            messagebox.showinfo("Память", "Мир не выбран.")
            return

        entries = self.memory_bank.get("entries", [])
        if not entries:
            messagebox.showinfo("Память", "Банк памяти пуст. Записи появятся после нескольких ходов.")
            return

        win = ctk.CTkToplevel(self.root)
        win.title("🧠 Банк памяти")
        win.geometry("750x650")
        win.transient(self.root)
        win.grab_set()

        ctk.CTkLabel(
            win,
            text=f"Записей: {len(entries)} | Проиндексировано ходов: {self.memory_bank.get('last_indexed_turn', 0)}",
            font=ctk.CTkFont(weight="bold"),
        ).pack(anchor=tk.W, padx=15, pady=(10, 5))

        viewer = ctk.CTkTextbox(win, wrap=tk.WORD, font=ctk.CTkFont(family="Consolas", size=12))
        viewer.pack(fill=ctk.BOTH, expand=True, padx=15, pady=5)

        lines = []
        for mem in entries:
            keys = ", ".join(mem.get("keys", []))
            npcs = ", ".join(mem.get("npcs", []))
            location = mem.get("location") or "—"
            lines.append(
                f"=== {mem['id']} | ходы {mem.get('turn_start', '?')}-{mem.get('turn_end', '?')} ===\n"
                f"Ключи: {keys or '—'}\n"
                f"NPC: {npcs or '—'} | Локация: {location}\n"
                f"{mem.get('summary', '')}\n"
            )
        viewer.insert("1.0", "\n".join(lines))
        viewer.configure(state="disabled")

        def force_index():
            win.destroy()
            self.add_system_message("🧠 Принудительная индексация памяти...")
            Thread(target=self.run_memory_indexing, kwargs={"force": True}, daemon=True).start()

        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.pack(fill=ctk.X, padx=15, pady=(0, 15))
        ctk.CTkButton(btn_frame, text="🔄 Индексировать сейчас", command=force_index).pack(side=ctk.LEFT)
        ctk.CTkButton(btn_frame, text="❌ Закрыть", command=win.destroy, fg_color="gray").pack(side=ctk.RIGHT)
