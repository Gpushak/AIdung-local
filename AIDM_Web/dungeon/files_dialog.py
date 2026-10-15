import customtkinter as ctk

import tkinter as tk

from tkinter import messagebox

from .config import (
    COLORS,
    INTRODUCTION_FILE,
    STORY_CARDS_KEY,
    WORLD_FILES,
)

from .windowing import place_window

from .story_cards import (
    load_story_cards,
    save_story_cards,
)

class FilesMixin:
    def open_world_files(self):
        if not self.current_world_path:
            return
        win = ctk.CTkToplevel(self.root)
        win.title(self.tr("dialog.world_files"))
        win.transient(self.root)
        place_window(win, "800x550", self.root)
        win.grab_set()

        self.current_editing_file = None
        self.current_editing_file_index = None
        self.file_editor_original_content = ""
        self.files_window = win

        left_frame = ctk.CTkFrame(win, width=200)
        left_frame.pack(side=ctk.LEFT, fill=ctk.Y, padx=10, pady=10)
        left_frame.pack_propagate(False)

        ctk.CTkLabel(left_frame, text=self.tr("dialog.choose_file"), font=ctk.CTkFont(weight="bold")).pack(pady=5)

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
        self.world_file_keys = list(WORLD_FILES.keys()) + [STORY_CARDS_KEY]
        for key in self.world_file_keys:
            self.file_listbox.insert(tk.END, self.world_file_label(key))

        right_frame = ctk.CTkFrame(win)
        right_frame.pack(side=ctk.RIGHT, fill=ctk.BOTH, expand=True, padx=(0, 10), pady=10)

        self.file_editor_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        self.file_editor_frame.pack(fill=ctk.BOTH, expand=True)

        self.file_editor = ctk.CTkTextbox(self.file_editor_frame, wrap=tk.WORD, font=ctk.CTkFont(size=14))
        self.file_editor.pack(fill=ctk.BOTH, expand=True, padx=10, pady=10)
        self.file_editor.bind("<Button-3>", self.show_context_menu)
        self.file_editor._textbox.bind("<<Modified>>", self.on_file_editor_modified)

        self.story_cards_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        self.story_cards_data = load_story_cards(self.current_world_path)
        self._embed_story_cards_editor(
            self.story_cards_frame,
            self.story_cards_data,
            editable=True,
            on_save=lambda: save_story_cards(self.current_world_path, self.story_cards_data),
        )

        btn_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        btn_frame.pack(fill=ctk.X, pady=10, padx=10)

        self.file_save_btn = ctk.CTkButton(btn_frame, text=self.tr("btn.save"), command=self.save_current_file)
        self.file_save_btn.pack(side=ctk.LEFT, padx=5)
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
        if self.current_editing_file == STORY_CARDS_KEY:
            return False
        current_content = self.file_editor.get("1.0", tk.END).strip()
        return current_content != self.file_editor_original_content.strip()

    def update_unsaved_indicator(self):
        if not hasattr(self, "unsaved_label") or not self.unsaved_label.winfo_exists():
            return
        if self.has_unsaved_file_changes():
            self.unsaved_label.configure(text=self.tr("dialog.unsaved"))
        else:
            self.unsaved_label.configure(text="")

    def _show_file_editor_panel(self):
        self.story_cards_frame.pack_forget()
        self.file_editor_frame.pack(fill=ctk.BOTH, expand=True)
        self.file_save_btn.pack(side=ctk.LEFT, padx=5)

    def _show_story_cards_panel(self):
        self.file_editor_frame.pack_forget()
        self.story_cards_frame.pack(fill=ctk.BOTH, expand=True)
        self.file_save_btn.pack_forget()
        self.unsaved_label.configure(text="")

    def _load_file_into_editor(self, index):
        file_key = self.world_file_keys[index]
        if file_key == STORY_CARDS_KEY:
            self.current_editing_file = STORY_CARDS_KEY
            self.current_editing_file_index = index
            self.story_cards_data = load_story_cards(self.current_world_path)
            self.story_cards = self.story_cards_data
            for widget in self.story_cards_frame.winfo_children():
                widget.destroy()
            self._embed_story_cards_editor(
                self.story_cards_frame,
                self.story_cards_data,
                editable=True,
                on_save=lambda: save_story_cards(self.current_world_path, self.story_cards_data),
            )
            self._show_story_cards_panel()
            return

        self._show_file_editor_panel()
        fname = file_key
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
        old_label = self.tr("world_file.story_cards") if old_fname == STORY_CARDS_KEY else self.tr(f"world_file.{old_fname}")
        choice = messagebox.askyesnocancel(
            self.tr("dialog.attention"), self.tr("dialog.file_unsaved", label=old_label)
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
            choice = messagebox.askyesnocancel(self.tr("dialog.attention"), self.tr("dialog.close_unsaved"))
            if choice is None:
                return
            elif choice:
                self.save_current_file()
        self.files_window.destroy()

    def save_current_file(self):
        if not getattr(self, "current_editing_file", None):
            return
        if self.current_editing_file == STORY_CARDS_KEY:
            return
        content = self.file_editor.get("1.0", tk.END)
        (self.current_world_path / self.current_editing_file).write_text(content, encoding="utf-8")
        self.file_editor_original_content = content.strip()
        self.file_editor._textbox.edit_modified(False)
        self.update_unsaved_indicator()
        if self.current_editing_file == INTRODUCTION_FILE:
            self.sync_introduction_to_history(content.strip())
        self.update_context_indicator()
        self.add_system_message(self.tr("msg.file_saved", name=self.current_editing_file))

