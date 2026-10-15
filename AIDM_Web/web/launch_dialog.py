"""Окно выбора сети перед запуском сервера."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

from web.netbind import BIND_MODES, network_addresses, saved_mode, share_urls

COPY = {
    "ru": {
        "title": "Запуск AIDM",
        "lead": "Откуда открыть игру?",
        "local": "Только этот компьютер",
        "lan": "Домашняя сеть Wi-Fi",
        "tailscale": "Tailscale",
        "local_hint": "Страница откроется только на этом компьютере.",
        "lan_hint": "Телефон должен быть в той же сети Wi-Fi.",
        "tailscale_hint": "Телефон должен быть в той же сети Tailscale. Общий Wi-Fi не нужен.",
        "tailscale_off": "Tailscale не найден. Запустите Tailscale и откройте программу снова.",
        "no_lan": "Адрес Wi-Fi не найден.",
        "start": "Запустить",
        "cancel": "Выход",
        "busy": "Порт {port} уже занят. Закройте другой запуск игры и попробуйте снова.",
        "remembered": "Выбор запоминается и будет предложен в следующий раз.",
    },
    "en": {
        "title": "Start AIDM",
        "lead": "Where should the game open?",
        "local": "This computer only",
        "lan": "Home Wi-Fi",
        "tailscale": "Tailscale",
        "local_hint": "The page opens only on this computer.",
        "lan_hint": "The phone has to be on the same Wi-Fi.",
        "tailscale_hint": "The phone has to be on the same Tailscale network. Shared Wi-Fi is not required.",
        "tailscale_off": "Tailscale was not found. Start Tailscale and open the program again.",
        "no_lan": "No Wi-Fi address found.",
        "start": "Start",
        "cancel": "Exit",
        "busy": "Port {port} is already in use. Close the other game window and try again.",
        "remembered": "The choice is saved and offered next time.",
    },
}

BG = "#1c1814"
INK = "#e8e0d0"
MUTED = "#8a8175"
GOLD = "#e6b450"
LINE = "#3a332c"
PAPER = "#14110e"


def _text(language):
    return COPY["en"] if language == "en" else COPY["ru"]


def ask_bind_mode(port, settings):
    """Возвращает local, lan или tailscale. None — пользователь закрыл окно."""
    language = settings.get("language", "ru") if isinstance(settings, dict) else "ru"
    text = _text(language)
    addresses = network_addresses()
    initial = saved_mode(settings if isinstance(settings, dict) else {})
    if initial == "tailscale" and not addresses["tailscale"]:
        initial = "lan" if addresses["lan"] else "local"

    chosen = {"mode": None}
    root = tk.Tk()
    root.title(text["title"])
    root.configure(bg=BG)
    root.resizable(False, False)
    try:
        root.tk.call("tk", "scaling", 1.4)
    except tk.TclError:
        pass

    frame = tk.Frame(root, bg=BG, padx=22, pady=18)
    frame.pack(fill="both")
    tk.Label(frame, text=text["lead"], bg=BG, fg=GOLD, font=("Segoe UI", 16, "bold")).pack(anchor="w")
    tk.Label(
        frame,
        text=text["remembered"],
        bg=BG,
        fg=MUTED,
        font=("Segoe UI", 10),
        wraplength=420,
        justify="left",
    ).pack(anchor="w", pady=(4, 12))

    mode_var = tk.StringVar(value=initial)

    def option(mode, title, hint, enabled=True):
        urls = share_urls(mode, port, addresses)
        shown = urls["share"][0] if urls["share"] else urls["local"]
        row = tk.Frame(frame, bg=PAPER, highlightbackground=LINE, highlightthickness=1, padx=10, pady=8)
        row.pack(fill="x", pady=4)
        button = tk.Radiobutton(
            row,
            text=title,
            variable=mode_var,
            value=mode,
            bg=PAPER,
            fg=INK,
            selectcolor=BG,
            activebackground=PAPER,
            activeforeground=INK,
            font=("Segoe UI", 12),
            anchor="w",
            state=("normal" if enabled else "disabled"),
        )
        button.pack(fill="x")
        tk.Label(row, text=shown, bg=PAPER, fg=GOLD, font=("Segoe UI", 11)).pack(anchor="w", padx=24)
        tk.Label(row, text=hint, bg=PAPER, fg=MUTED, font=("Segoe UI", 9), wraplength=400, justify="left").pack(
            anchor="w", padx=24, pady=(2, 0)
        )

    option("local", text["local"], text["local_hint"])
    lan_hint = text["lan_hint"] if addresses["lan"] else text["no_lan"]
    option("lan", text["lan"], lan_hint)
    ts_hint = text["tailscale_hint"] if addresses["tailscale"] else text["tailscale_off"]
    option("tailscale", text["tailscale"], ts_hint, enabled=bool(addresses["tailscale"]))

    buttons = tk.Frame(frame, bg=BG)
    buttons.pack(fill="x", pady=(14, 0))

    def accept():
        mode = mode_var.get()
        if mode not in BIND_MODES:
            return
        chosen["mode"] = mode
        root.destroy()

    def cancel():
        chosen["mode"] = None
        root.destroy()

    start = tk.Button(
        buttons,
        text=text["start"],
        command=accept,
        bg=GOLD,
        fg="#1a140c",
        activebackground=GOLD,
        font=("Segoe UI", 11, "bold"),
        relief="flat",
        padx=16,
        pady=6,
    )
    start.pack(side="right")
    tk.Button(
        buttons,
        text=text["cancel"],
        command=cancel,
        bg=BG,
        fg=INK,
        activebackground=BG,
        activeforeground=INK,
        font=("Segoe UI", 11),
        relief="flat",
        highlightbackground=LINE,
        padx=12,
        pady=6,
    ).pack(side="right", padx=(0, 8))

    root.protocol("WM_DELETE_WINDOW", cancel)
    root.bind("<Return>", lambda _event: accept())
    root.bind("<Escape>", lambda _event: cancel())
    root.update_idletasks()
    width = max(root.winfo_width(), 460)
    height = root.winfo_height()
    x = max(0, (root.winfo_screenwidth() - width) // 2)
    y = max(0, (root.winfo_screenheight() - height) // 2)
    root.geometry(f"{width}x{height}+{x}+{y}")
    start.focus_set()
    root.mainloop()
    return chosen["mode"]


def tell_port_busy(port, language):
    text = _text(language)
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(text["title"], text["busy"].format(port=port), parent=root)
    root.destroy()
