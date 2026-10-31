import customtkinter as ctk

import tkinter as tk

from tkinter import messagebox

from .config import COLORS

from .i18n import (
    DM_PREFIX,
    PLAYER_PREFIX,
    dm_text,
    is_dm_msg,
    is_player_msg,
    player_text,
)

from .storage import save_history

from .windowing import place_window

class InspectMixin:
    def prompt_next_turn(self):
        if self.is_busy() or not self.current_world_path:
            return

        win = ctk.CTkToplevel(self.root)
        win.title(self.tr("dialog.next_title"))
        win.transient(self.root)
        place_window(win, "520x280", self.root)
        win.grab_set()

        ctk.CTkLabel(
            win,
            text=self.tr("dialog.next_hint"),
            justify=tk.LEFT,
        ).pack(anchor=tk.W, padx=20, pady=(20, 10))

        direction_box = ctk.CTkTextbox(win, height=120, wrap=tk.WORD, font=ctk.CTkFont(size=14))
        direction_box.pack(fill=ctk.BOTH, expand=True, padx=20, pady=(0, 10))
        direction_box.focus()

        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.pack(fill=ctk.X, padx=20, pady=(0, 15))

        def submit_direction():
            direction = direction_box.get("1.0", tk.END).strip()
            if not direction:
                messagebox.showwarning(self.tr("dialog.empty_input"), self.tr("dialog.empty_next"), parent=win)
                return
            win.destroy()
            self.add_player_message(f"❓ {direction}")
            self._dispatch_turn(self.process_action, ("",), {"direction_hint": direction})

        def handle_enter(event):
            if event.state & 0x1:
                return
            submit_direction()
            return "break"

        direction_box.bind("<Return>", handle_enter)

        ctk.CTkButton(
            btn_frame,
            text=self.tr("btn.send"),
            command=submit_direction,
            fg_color=COLORS["accent"],
            hover_color=COLORS["button_hover"],
            text_color="black",
        ).pack(side=ctk.LEFT, padx=(0, 5))
        ctk.CTkButton(btn_frame, text=self.tr("btn.cancel_plain"), command=win.destroy, fg_color="gray").pack(side=ctk.RIGHT)

    def quit_app(self):
        if messagebox.askyesno(self.tr("dialog.quit"), self.tr("dialog.quit_q")):
            self.on_closing()

    def edit_last_message(self):
        if not self.current_world_path or not self.history:
            return

        # Find the last message (either DM or player)
        last_msg_index = len(self.history) - 1
        last_msg = self.history[last_msg_index]

        if is_dm_msg(last_msg):
            self._edit_message_at_index(last_msg_index, "dm")
        elif is_player_msg(last_msg):
            self._edit_message_at_index(last_msg_index, "player")
        else:
            # If last message is system/intro, find the last non-system message
            for i in range(len(self.history) - 1, -1, -1):
                msg = self.history[i]
                if is_dm_msg(msg) or is_player_msg(msg):
                    msg_type = "dm" if is_dm_msg(msg) else "player"
                    self._edit_message_at_index(i, msg_type)
                    return
            # No editable messages found
            return

    def _edit_message_at_index(self, index, msg_type):
        """Helper method to edit a message at given index with navigation."""
        # Find all editable message indices
        editable_indices = []
        for i, msg in enumerate(self.history):
            if is_dm_msg(msg) or is_player_msg(msg):
                editable_indices.append(i)
        
        if not editable_indices:
            return
        
        # Find current position in editable indices
        try:
            current_pos = editable_indices.index(index)
        except ValueError:
            return
        
        def update_editor_for_position(pos):
            idx = editable_indices[pos]
            msg = self.history[idx]
            if is_dm_msg(msg):
                current_text = dm_text(msg)
                dialog_title = self.tr("dialog.edit_dm")
                dialog_label = self.tr("dialog.edit_dm_label")
                prefix = DM_PREFIX
            else:
                current_text = player_text(msg)
                dialog_title = self.tr("dialog.edit_player")
                dialog_label = self.tr("dialog.edit_player_label")
                prefix = PLAYER_PREFIX
            
            title_label.configure(text=f"{dialog_title} ({pos + 1}/{len(editable_indices)})")
            info_label.configure(text=dialog_label)
            editor.delete("1.0", tk.END)
            editor.insert(tk.END, current_text)
            
            # Update button states
            prev_btn.configure(state=tk.NORMAL if pos > 0 else tk.DISABLED)
            next_btn.configure(state=tk.NORMAL if pos < len(editable_indices) - 1 else tk.DISABLED)
            
            return idx, prefix
        
        def navigate_prev():
            nonlocal current_pos, current_index, current_prefix
            if current_pos > 0:
                current_pos -= 1
                current_index, current_prefix = update_editor_for_position(current_pos)
        
        def navigate_next():
            nonlocal current_pos, current_index, current_prefix
            if current_pos < len(editable_indices) - 1:
                current_pos += 1
                current_index, current_prefix = update_editor_for_position(current_pos)
        
        if msg_type == "dm":
            current_text = dm_text(self.history[index])
            dialog_title = self.tr("dialog.edit_dm")
            dialog_label = self.tr("dialog.edit_dm_label")
            prefix = DM_PREFIX
            success_msg = self.tr("msg.dm_edited")
        else:
            current_text = player_text(self.history[index])
            dialog_title = self.tr("dialog.edit_player")
            dialog_label = self.tr("dialog.edit_player_label")
            prefix = PLAYER_PREFIX
            success_msg = self.tr("msg.player_edited")
        
        win = ctk.CTkToplevel(self.root)
        win.title(dialog_title)
        win.transient(self.root)
        place_window(win, "600x550", self.root)
        win.grab_set()
        
        # Title with position
        title_label = ctk.CTkLabel(win, text=f"{dialog_title} ({current_pos + 1}/{len(editable_indices)})", font=ctk.CTkFont(weight="bold"))
        title_label.pack(pady=(10, 5), anchor=tk.W, padx=15)
        
        # Navigation buttons
        nav_frame = ctk.CTkFrame(win, fg_color="transparent")
        nav_frame.pack(fill=ctk.X, padx=15, pady=5)
        
        prev_btn = ctk.CTkButton(nav_frame, text=self.tr("dialog.edit_prev"), width=100, command=navigate_prev, state=tk.DISABLED if current_pos == 0 else tk.NORMAL)
        prev_btn.pack(side=ctk.LEFT, padx=5)
        
        next_btn = ctk.CTkButton(nav_frame, text=self.tr("dialog.edit_next"), width=100, command=navigate_next, state=tk.DISABLED if current_pos == len(editable_indices) - 1 else tk.NORMAL)
        next_btn.pack(side=ctk.RIGHT, padx=5)
        
        info_label = ctk.CTkLabel(win, text=dialog_label)
        info_label.pack(anchor=tk.W, padx=15, pady=(5, 5))
        
        editor = ctk.CTkTextbox(win, wrap=tk.WORD, font=ctk.CTkFont(size=14))
        editor.pack(fill=ctk.BOTH, expand=True, padx=15, pady=5)
        editor.insert(tk.END, current_text)
        editor.focus_set()
        editor.bind("<Button-3>", self.show_context_menu)
        
        # Store current editing state
        current_index = index
        current_prefix = prefix
        
        def save_edited_msg():
            new_text = editor.get("1.0", tk.END).strip()
            if not new_text:
                return
            new_line = f"{current_prefix} {new_text}"
            changed = self.history[current_index] != new_line
            self.history[current_index] = new_line
            if changed and current_index < self.covered_count:
                self.note_history_revised(current_index)
            save_history(self.current_world_path, self.history)
            self.refresh_chat_display()
            self.update_context_indicator()
            win.destroy()
            self.add_system_message(success_msg)
        
        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.pack(fill=ctk.X, pady=15, padx=15)
        ctk.CTkButton(
            btn_frame, text=self.tr("btn.save_ok"), command=save_edited_msg, fg_color=COLORS["accent"], text_color="black"
        ).pack(side=ctk.LEFT)
        ctk.CTkButton(btn_frame, text=self.tr("btn.cancel"), command=win.destroy, fg_color="gray").pack(side=ctk.RIGHT)

    def force_summary(self):
        if self.is_busy() or not self.current_world_path:
            return
        self.add_system_message(self.tr("msg.force_summary"))
        self.generate_global_summary()

    def show_last_prompt(self):
        if not self.last_sent_prompt:
            messagebox.showinfo(self.tr("dialog.prompt_title"), self.tr("dialog.no_prompt"))
            return

        data = self.last_sent_prompt
        full_text = self.tr("dialog.prompt_time", time=data["time"], tokens=data["tokens"]) + self.tr(
            "dialog.prompt_body", system=data["system"], user=data["user"]
        )

        win = ctk.CTkToplevel(self.root)
        win.title(self.tr("dialog.prompt_title"))
        win.transient(self.root)
        place_window(win, "750x650", self.root)
        win.grab_set()

        viewer = ctk.CTkTextbox(win, wrap=tk.WORD, font=ctk.CTkFont(family="Consolas", size=12))
        viewer.pack(fill=ctk.BOTH, expand=True, padx=15, pady=15)
        viewer.insert("1.0", full_text)
        viewer.configure(state="disabled")

        def copy_to_clipboard():
            self.root.clipboard_clear()
            self.root.clipboard_append(full_text)
            self.add_system_message(self.tr("msg.prompt_copied"))

        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.pack(fill=ctk.X, padx=15, pady=(0, 15))
        ctk.CTkButton(btn_frame, text=self.tr("btn.copy"), command=copy_to_clipboard).pack(side=ctk.LEFT)
        ctk.CTkButton(btn_frame, text=self.tr("btn.close_x"), command=win.destroy, fg_color="gray").pack(side=ctk.RIGHT)

    def show_scene_prompt(self, scene_prompt, negative_prompt, style="sd"):
        win = ctk.CTkToplevel(self.root)
        win.title(self.tr("btn.scene_prompt"))
        win.transient(self.root)
        place_window(win, "750x650", self.root)
        # Окно намеренно немодальное: промпт обычно уходит в стороннюю
        # программу (например A1111/ComfyUI), и закрывать окно не хочется.

        ctk.CTkLabel(
            win, text=self.tr("dialog.image_style") + " " + self.tr(f"image_style.{style}"), text_color=COLORS["accent"]
        ).pack(anchor=tk.W, padx=15, pady=(12, 0))

        def labeled_box(parent, label, text, row):
            ctk.CTkLabel(parent, text=label, font=ctk.CTkFont(size=13, weight="bold")).grid(
                row=row, column=0, sticky=tk.W, padx=15, pady=(12, 4)
            )
            box = ctk.CTkTextbox(parent, height=200, wrap=tk.WORD, font=ctk.CTkFont(family="Consolas", size=12))
            box.insert("1.0", text or self.tr("prompt.none"))
            box.configure(state="disabled")
            return box

        grid = ctk.CTkFrame(win, fg_color="transparent")
        grid.pack(fill=ctk.BOTH, expand=True)
        grid.grid_columnconfigure(0, weight=1)

        prompt_box = labeled_box(grid, self.tr("scene.prompt_label"), scene_prompt, 0)
        prompt_box.grid(row=1, column=0, sticky=tk.NSEW, padx=15)

        neg_box = labeled_box(grid, self.tr("scene.negative_label"), negative_prompt, 2)
        neg_box.grid(row=3, column=0, sticky=tk.NSEW, padx=15)
        grid.grid_rowconfigure(1, weight=1)
        grid.grid_rowconfigure(3, weight=1)

        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.pack(fill=tk.X, padx=15, pady=(0, 15))

        def copy(text, done_key):
            if not text:
                return
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.add_system_message(self.tr(done_key))

        ctk.CTkButton(
            btn_frame, text=self.tr("scene.copy_prompt"), command=lambda: copy(scene_prompt, "scene.copied_prompt")
        ).pack(side=ctk.LEFT, padx=(0, 6))
        ctk.CTkButton(
            btn_frame,
            text=self.tr("scene.copy_negative"),
            command=lambda: copy(negative_prompt, "scene.copied_negative"),
        ).pack(side=ctk.LEFT)
        ctk.CTkButton(btn_frame, text=self.tr("btn.close_x"), command=win.destroy, fg_color="gray").pack(side=ctk.RIGHT)

        self.add_system_message(self.tr("msg.scene_prompt_done"))

    def show_memory_bank(self):
        if not self.current_world_path:
            messagebox.showinfo(self.tr("dialog.memory_title"), self.tr("dialog.no_world"))
            return

        entries = self.memory_bank.get("entries", [])
        if not entries:
            messagebox.showinfo(self.tr("dialog.memory_title"), self.tr("dialog.memory_empty"))
            return

        win = ctk.CTkToplevel(self.root)
        win.title(self.tr("dialog.memory_title"))
        win.transient(self.root)
        place_window(win, "750x650", self.root)
        win.grab_set()

        ctk.CTkLabel(
            win,
            text=self.tr("dialog.memory_stats", n=len(entries), turns=self.memory_bank.get("last_indexed_turn", 0)),
            font=ctk.CTkFont(weight="bold"),
        ).pack(anchor=tk.W, padx=15, pady=(10, 5))

        viewer = ctk.CTkTextbox(win, wrap=tk.WORD, font=ctk.CTkFont(family="Consolas", size=12))
        viewer.pack(fill=ctk.BOTH, expand=True, padx=15, pady=5)

        lines = []
        for mem in entries:
            keys = ", ".join(mem.get("keys", [])) or "—"
            npcs = ", ".join(mem.get("npcs", [])) or "—"
            location = mem.get("location") or "—"
            lines.append(
                self.tr(
                    "dialog.memory_entry",
                    id=mem["id"],
                    start=mem.get("turn_start", "?"),
                    end=mem.get("turn_end", "?"),
                    keys=keys,
                    npcs=npcs,
                    location=location,
                    summary=mem.get("summary", ""),
                )
            )
        viewer.insert("1.0", "\n".join(lines))
        viewer.configure(state="disabled")

        def force_index():
            win.destroy()
            self.add_system_message(self.tr("msg.force_memory"))
            self.run_memory_indexing(force=True)

        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.pack(fill=ctk.X, padx=15, pady=(0, 15))
        ctk.CTkButton(btn_frame, text=self.tr("btn.index_now"), command=force_index).pack(side=ctk.LEFT)
        ctk.CTkButton(btn_frame, text=self.tr("btn.close_x"), command=win.destroy, fg_color="gray").pack(side=ctk.RIGHT)
