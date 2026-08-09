"""
Utilidad exclusiva de Windows: convierte una ventana de tkinter en
'click-through' (los clics del mouse pasan a la ventana de abajo).
Se usa para que el marco rojo de la selección fija no bloquee la
interacción con la app que está detrás.
"""
import sys


def make_click_through(tk_window) -> None:
    if sys.platform != "win32":
        return  # No-op fuera de Windows

    import ctypes

    hwnd = ctypes.windll.user32.GetParent(tk_window.winfo_id())

    GWL_EXSTYLE = -20
    WS_EX_LAYERED = 0x00080000
    WS_EX_TRANSPARENT = 0x00000020

    style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    style |= WS_EX_LAYERED | WS_EX_TRANSPARENT
    ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
