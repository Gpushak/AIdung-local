"""Общие помощники для тестов: чистое закрытие окон Tk.

CustomTkinter планирует внутренние after-коллбэки (update, check_dpi_scaling,
проверка скроллбаров, иконка заголовка). Они срабатывают уже после того, как
тест уничтожил окно, и Tcl печатает «invalid command name ...» — выглядит
как ошибка, хотя тест прошёл. close_tk_window отменяет все отложенные
коллбэки перед уничтожением, поэтому вывод остаётся чистым.
"""


def close_tk_window(root):
    """Гасит отложенные after-коллбэки и уничтожает окно без шума."""
    if root is None:
        return
    try:
        for after_id in root.tk.call("after", "info"):
            try:
                root.after_cancel(after_id)
            except Exception:
                pass
    except Exception:
        pass
    try:
        root.report_callback_exception = lambda *args: None
    except Exception:
        pass
    try:
        root.destroy()
    except Exception:
        pass
