"""Проверка размещения окон: центр экрана и удержание в его пределах."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dungeon.windowing import (  # noqa: E402
    SCREEN_MARGIN,
    TASKBAR_RESERVE,
    centered_position,
    fit_to_screen,
    parse_size,
    place_window,
)

BIG = (2560, 1440)
FHD = (1920, 1080)
LAPTOP = (1366, 768)
SMALL = (1280, 720)


def test_parse_size():
    assert parse_size("750x650") == (750, 650)
    assert parse_size("900X1200") == (900, 1200)
    # Мусор не должен ломать запуск приложения
    assert parse_size("") == (0, 0)
    assert parse_size(None) == (0, 0)
    assert parse_size("не размер") == (0, 0)
    print("OK  размер разбирается, мусор не ломает запуск")


def test_main_window_centered_on_large_screen():
    x, y = centered_position(900, 1200, *BIG)
    assert 0 < x < BIG[0] - 900, x
    assert 0 < y, y
    # Отступы слева/справа почти равны — окно действительно по центру
    assert abs((BIG[0] - 900 - x) - x) <= 2, (x, BIG[0] - 900 - x)
    print(f"OK  большой экран: окно 900x1200 встаёт по центру ({x}, {y})")


def test_oversized_window_fits_and_stays_on_screen():
    """Исходный баг: на 1080p окно 1200px не помещалось и уезжало вверх."""
    w, h = fit_to_screen(900, 1200, *FHD)
    x, y = centered_position(w, h, *FHD)
    assert y >= 0, f"окно уехало за верхний край: y={y}"
    assert y + h <= FHD[1], (y, h)
    # И оно правда уменьшилось, а не просто наехало на край
    assert h < 1200, h
    print(f"OK  на {FHD[1]}px окно ужато до {w}x{h} и помещается (y={y})")


def test_fits_every_common_screen():
    for screen in (BIG, FHD, LAPTOP, SMALL):
        w, h = fit_to_screen(900, 1200, *screen)
        x, y = centered_position(w, h, *screen)
        assert x >= 0 and y >= 0, (screen, x, y)
        assert x + w <= screen[0], (screen, x, w)
        assert y + h <= screen[1], (screen, y, h)
    print("OK  окно помещается на 1440p, 1080p, 768p и 720p")


def test_never_overflows_sideways_on_narrow_screen():
    w, h = fit_to_screen(2000, 800, *LAPTOP)
    x, y = centered_position(w, h, *LAPTOP)
    assert x + w <= LAPTOP[0], (x, w)
    assert w <= LAPTOP[0]
    print("OK  широкое окно ужимается по ширине узкого экрана")


def test_bottom_reserved_for_taskbar():
    """Рабочая область на Windows меньше экрана на высоту панели задач."""
    avail_h = FHD[1] - 2 * SCREEN_MARGIN - TASKBAR_RESERVE
    _, h = fit_to_screen(900, 3000, *FHD)
    assert h <= avail_h, (h, avail_h)
    print(f"OK  внизу резервируется {TASKBAR_RESERVE}px под панель задач")


def test_centered_on_parent_when_given():
    parent = (500, 100, 900, 1200)
    x, y = centered_position(500, 400, *BIG, parent_rect=parent)
    # Центры должны совпасть
    assert abs((x + 500 // 2) - (500 + 900 // 2)) <= 1, x
    assert abs((y + 400 // 2) - (100 + 1200 // 2)) <= 1, y
    print("OK  окно центрируется по родительскому окну")


def test_parent_offset_offscreen_is_clamped():
    """Если родитель уехал за край, окно всё равно остаётся на экране."""
    parent = (3000, 2000, 900, 1200)  # родитель за пределами экрана
    w, h = fit_to_screen(500, 400, *BIG)
    x, y = centered_position(w, h, *BIG, parent_rect=parent)
    assert x >= 0 and y >= 0, (x, y)
    assert x + w <= BIG[0] and y + h <= BIG[1], (x, y)
    print("OK  родитель за экраном не утаскивает диалог за край")


def test_smallest_screens_still_get_usable_window():
    w, h = fit_to_screen(900, 1200, 800, 600)
    assert w >= 240 and h >= 240, (w, h)
    print("OK  даже на крошечном экране остаётся окно не меньше 240px")


def test_place_window_applies_geometry_to_real_tk():
    import customtkinter as ctk

    ctk.set_appearance_mode("Dark")
    root = ctk.CTk()
    place_window(root, "900x1200")
    root.deiconify()
    root.update()
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    x, y, w, h = root.winfo_rootx(), root.winfo_rooty(), root.winfo_width(), root.winfo_height()
    assert (w, h) == (900, 1200), (w, h)
    assert x >= 0 and y >= 0 and x + w <= sw and y + h <= sh, (x, y, w, h)
    root.destroy()
    print("OK  реальное окно Tk получает корректный размер и позицию")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("ALL WINDOW TESTS PASSED")
