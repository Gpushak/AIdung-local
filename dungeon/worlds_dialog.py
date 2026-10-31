import shutil

import customtkinter as ctk

import tkinter as tk

from tkinter import messagebox

from .config import (
    BASE_DIR,
    COLORS,
    INTRODUCTION_FILE,
    WORLD_FILES,
)

from .i18n import default_templates

from .storage import (
    format_introduction_history,
    get_world_list,
    read_world_language,
    save_history,
    save_world_files,
    save_world_language,
)

from .windowing import place_window

from .story_cards import (
    default_story_cards,
    save_story_cards,
)

class WorldsMixin:
    def manage_worlds(self):
        win = ctk.CTkToplevel(self.root)
        win.title(self.tr("dialog.manage_worlds"))
        win.transient(self.root)
        place_window(win, "500x400", self.root)
        win.grab_set()

        ctk.CTkLabel(win, text=self.tr("dialog.your_worlds"), font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)

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

        self._world_names = get_world_list()
        listbox.delete(0, tk.END)
        for name in self._world_names:
            lang = read_world_language(BASE_DIR / name)
            mark = f"  ·  {lang.upper()}" if lang in ("ru", "en") else ""
            listbox.insert(tk.END, f"{name}{mark}")

        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.pack(fill=ctk.X, padx=20, pady=10)

        def switch_to_world():
            sel = listbox.curselection()
            if not sel:
                return
            name = self._world_names[sel[0]]
            win.destroy()
            self.load_world(name)

        def delete_world():
            sel = listbox.curselection()
            if not sel:
                return
            name = self._world_names[sel[0]]
            if messagebox.askyesno(self.tr("dialog.delete_world"), self.tr("dialog.delete_world_q", name=name)):
                remaining_worlds = [w for w in get_world_list() if w != name]
                current_world_was_deleted = self.world_name == name

                shutil.rmtree(BASE_DIR / name)
                listbox.delete(sel[0])
                del self._world_names[sel[0]]

                if current_world_was_deleted:
                    self.current_world_path = None
                    self.world_name = None
                    self.history = []
                    self.covered_count = 0
                    self.turns_since_memory = 0
                    self.memory_bank = {"last_indexed_turn": 0, "entries": []}

                    if remaining_worlds:
                        next_world = remaining_worlds[0]
                        win.destroy()
                        self.load_world(next_world)
                        return

                    self.update_memory_label()
                    self.update_context_indicator()
                    self.refresh_chat_display()

        ctk.CTkButton(btn_frame, text=self.tr("btn.load"), command=switch_to_world).pack(side=ctk.LEFT, padx=5)
        ctk.CTkButton(
            btn_frame,
            text=self.tr("btn.delete"),
            command=delete_world,
            fg_color=COLORS["danger"],
            hover_color=COLORS["danger_hover"],
        ).pack(side=ctk.LEFT, padx=5)
        ctk.CTkButton(btn_frame, text=self.tr("btn.create"), command=lambda: [win.destroy(), self.create_world_dialog()]).pack(
            side=ctk.LEFT, padx=5
        )
        ctk.CTkButton(btn_frame, text=self.tr("btn.close"), command=win.destroy, fg_color="gray").pack(side=ctk.RIGHT, padx=5)

    def create_world_dialog(self):
        win = ctk.CTkToplevel(self.root)
        win.title(self.tr("dialog.create_world"))
        win.transient(self.root)
        place_window(win, "750x700", self.root)
        win.grab_set()

        ctk.CTkLabel(win, text=self.tr("dialog.world_name")).pack(pady=(10, 0))
        name_entry = ctk.CTkEntry(win, width=300)
        name_entry.pack(pady=5)
        name_entry.insert(0, self.tr("dialog.default_world_name"))

        tabview = ctk.CTkTabview(win)
        tabview.pack(fill=ctk.BOTH, expand=True, padx=15, pady=5)
        tabs = {}
        new_world_cards = default_story_cards(self.language)

        templates = default_templates(self.language)
        for fname, desc in WORLD_FILES.items():
            tab = tabview.add(self.tr(f"world_file.{fname}"))
            text_widget = ctk.CTkTextbox(tab, wrap=tk.WORD)
            text_widget.pack(fill=ctk.BOTH, expand=True, padx=5, pady=5)
            text_widget.insert("1.0", templates.get(fname, ""))
            text_widget.bind("<Button-3>", self.show_context_menu)
            tabs[fname] = text_widget

        cards_tab = tabview.add(self.tr("world_file.story_cards"))
        cards_tab_frame = ctk.CTkFrame(cards_tab, fg_color="transparent")
        cards_tab_frame.pack(fill=ctk.BOTH, expand=True, padx=5, pady=5)
        cards_editor = self._embed_story_cards_editor(
            cards_tab_frame, new_world_cards, editable=True, persist=False
        )

        def apply_new_world():
            name = name_entry.get().strip()
            if not name or (BASE_DIR / name).exists():
                messagebox.showerror(self.tr("dialog.bad_name"), self.tr("dialog.bad_name_msg"))
                return
            cards_editor["save"]()
            content = {fname: w.get("1.0", tk.END).strip() for fname, w in tabs.items()}
            world_path = BASE_DIR / name
            save_world_files(world_path, content)
            save_world_language(world_path, self.language)
            save_story_cards(world_path, new_world_cards)
            intro = content.get(INTRODUCTION_FILE, "").strip()
            initial_history = [format_introduction_history(intro)] if intro else []
            save_history(world_path, initial_history)
            win.destroy()
            self.load_world(name)
            self.refresh_world_combobox()

        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.pack(fill=ctk.X, pady=15, padx=15)
        ctk.CTkButton(
            btn_frame, text=self.tr("btn.create_ok"), command=apply_new_world, fg_color=COLORS["accent"], text_color="black"
        ).pack(side=ctk.LEFT, padx=5)
        ctk.CTkButton(btn_frame, text=self.tr("btn.cancel"), command=win.destroy, fg_color="gray").pack(side=ctk.RIGHT, padx=5)

