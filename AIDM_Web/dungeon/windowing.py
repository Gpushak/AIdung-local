"""Размещение окон в пределах экрана.

Tk не сообщает запрошенный размер ещё не показанного окна: и winfo_width(),
и geometry() возвращают 200x200, пока окно не отрисовано. Поэтому размер
задаёт вызывающий код — той же строкой, которую раньше передавали в
geometry(), — а модуль только вписывает его в экран и вычисляет координаты.

Отдельно учитывается, что winfo_screenheight() на Windows возвращает полную
высоту экрана вместе с панелью задач, поэтому внизу резервируется место под
неё, а слишком высокое окно ужимается до рабочей области.
"""

# Поле у краёв экрана, чтобы окно не прижималось вплотную.
SCREEN_MARGIN = 16
# Резерв под панель задач и системные панели.
TASKBAR_RESERVE = 56


def parse_size(size):
    """Разбирает «750x650» в (750, 650). Неверный ввод не ломает запуск."""
    try:
        w, h = str(size).lower().split("x", 1)
        return max(1, int(w)), max(1, int(h))
    except (ValueError, AttributeError):
        return 0, 0


def fit_to_screen(width, height, screen_w, screen_h, reserve=TASKBAR_RESERVE):
    """Вписывает окно в рабочую область, не увеличивая уже подходящее."""
    avail_w = max(240, screen_w - 2 * SCREEN_MARGIN)
    avail_h = max(240, screen_h - 2 * SCREEN_MARGIN - reserve)
    return min(width, avail_w), min(height, avail_h)


def centered_position(width, height, screen_w, screen_h, parent_rect=None, reserve=TASKBAR_RESERVE):
    """Координаты левого верхнего угла окна.

    Если задан parent_rect (x, y, w, h), окно центрируется по родителю,
    иначе — по экрану. В любом случае результат зажимается в границы
    экрана. width/height должны уже быть вписаны в экран (см. fit_to_screen).
    """
    if parent_rect:
        px, py, pw, ph = parent_rect
        cx = px + pw // 2 - width // 2
        cy = py + ph // 2 - height // 2
    else:
        cx = screen_w // 2 - width // 2
        # Центрируем по рабочей области, а не по всему экрану
        cy = (screen_h - reserve) // 2 - height // 2

    max_x = max(SCREEN_MARGIN, screen_w - width - SCREEN_MARGIN)
    max_y = max(SCREEN_MARGIN, screen_h - height - SCREEN_MARGIN)
    return max(SCREEN_MARGIN, min(cx, max_x)), max(SCREEN_MARGIN, min(cy, max_y))


def place_window(win, size, parent=None, reserve=TASKBAR_RESERVE):
    """Задаёт размер окна и ставит его по центру, не выводя за пределы экрана.

    size — строка вида «750x650». parent — окно, по которому центрировать
    (обычно главное); если оно скрыто или неизвестно, берётся центр экрана.
    """
    width, height = parse_size(size)
    if not width or not height:
        return

    screen_w = win.winfo_screenwidth()
    screen_h = win.winfo_screenheight()
    width, height = fit_to_screen(width, height, screen_w, screen_h, reserve)

    parent_rect = _visible_rect(parent)
    x, y = centered_position(width, height, screen_w, screen_h, parent_rect, reserve)
    win.geometry(f"{width}x{height}+{x}+{y}")


def center_window(win, parent=None, reserve=TASKBAR_RESERVE):
    """Сдвигает уже созданное окно в центр, не меняя его размер.

    Используется для главного окна, размер которого к этому моменту известен.
    """
    win.update_idletasks()
    screen_w = win.winfo_screenwidth()
    screen_h = win.winfo_screenheight()
    width, height = win.winfo_width(), win.winfo_height()
    if width <= 1 or height <= 1:
        return
    width, height = fit_to_screen(width, height, screen_w, screen_h, reserve)
    x, y = centered_position(width, height, screen_w, screen_h, _visible_rect(parent), reserve)
    win.geometry(f"{width}x{height}+{x}+{y}")


def _visible_rect(parent):
    """Прямоугольник видимого родительского окна или None."""
    if parent is None:
        return None
    try:
        w, h = parent.winfo_width(), parent.winfo_height()
        # До отрисовки Tk отдаёт 1x1 или дефолтные 200x200 у пустых окон
        if w <= 1 or h <= 1:
            return None
        return parent.winfo_rootx(), parent.winfo_rooty(), w, h
    except Exception:
        return None
