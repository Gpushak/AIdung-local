import customtkinter as ctk

from .app import DungeonApp
from .config import WINDOW_SIZE
from .windowing import place_window


def main():
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    DungeonApp(root)

    # Размер и положение задаются после создания виджетов: до этого Tk
    # отдаёт дефолтные 200x200, и по центру экрана встать не получится.
    place_window(root, WINDOW_SIZE)
    root.minsize(560, 420)

    root.mainloop()


if __name__ == "__main__":
    main()
