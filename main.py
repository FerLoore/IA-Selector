"""
Punto de entrada de la app.

Flujo:
1. Si no hay API key guardada, la pide una vez (ventana simple).
2. Muestra un botón flotante, arrastrable, siempre encima de todo.
3. Primer clic: pide marcar el área (RegionPicker) y deja un marco fijo (FixedFrame).
4. Clics siguientes: captura esa misma área y la manda a Gemini.
5. Clic derecho sobre el botón: menú para cambiar de área o salir.
"""
import io
import threading
import tkinter as tk
from tkinter import simpledialog, messagebox

# pyrefly: ignore [missing-import]
from PIL import ImageGrab

import config
from ai_client import ask_about_image
from overlay import RegionPicker, FixedFrame
from result_window import ResultWindow


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()  # no mostramos ventana principal, solo el botón

        self.api_key = config.load_api_key()
        if not self.api_key:
            self._ask_for_api_key()

        self.region = None  # (left, top, right, bottom)
        self.fixed_frame = None

        self._build_floating_button()
        self.root.mainloop()

    # ---------- Configuración inicial ----------

    def _ask_for_api_key(self):
        self.root.deiconify()
        self.root.withdraw()
        key = simpledialog.askstring(
            "API key de Gemini",
            "Pega tu API key gratuita de Gemini\n"
            "(consíguela en https://aistudio.google.com/apikey):",
            parent=self.root,
        )
        if not key:
            messagebox.showwarning(
                "Falta la API key",
                "Sin una API key la app no puede consultar a la IA.\n"
                "Puedes agregarla luego editando config.json.",
            )
        else:
            config.save_api_key(key.strip())
            self.api_key = key.strip()

    # ---------- Botón flotante ----------

    def _build_floating_button(self):
        self.btn_win = tk.Toplevel(self.root)
        self.btn_win.overrideredirect(True)
        self.btn_win.attributes("-topmost", True)
        self.btn_win.geometry("56x56+40+200")

        self.btn = tk.Button(
            self.btn_win, text="IA", font=("Segoe UI", 14, "bold"),
            bg="#4da3ff", fg="white", activebackground="#2f86e0",
            relief="flat", command=self._on_button_click,
        )
        self.btn.pack(fill="both", expand=True)

        # Arrastrar el botón
        self._drag_data = {"x": 0, "y": 0}
        self.btn.bind("<ButtonPress-1>", self._start_drag)
        self.btn.bind("<B1-Motion>", self._do_drag)
        self.btn.bind("<ButtonRelease-1>", self._end_drag)

        # Clic derecho: menú
        self.menu = tk.Menu(self.btn_win, tearoff=0)
        self.menu.add_command(label="Cambiar área", command=self._change_region)
        self.menu.add_command(label="Cambiar API key", command=self._ask_for_api_key)
        self.menu.add_separator()
        self.menu.add_command(label="Salir", command=self.root.destroy)
        self.btn.bind("<Button-3>", self._show_menu)

        self._was_drag = False

    def _start_drag(self, event):
        self._drag_data = {"x": event.x, "y": event.y}
        self._was_drag = False

    def _do_drag(self, event):
        dx = event.x - self._drag_data["x"]
        dy = event.y - self._drag_data["y"]
        if abs(dx) > 2 or abs(dy) > 2:
            self._was_drag = True
        x = self.btn_win.winfo_x() + dx
        y = self.btn_win.winfo_y() + dy
        self.btn_win.geometry(f"+{x}+{y}")

    def _end_drag(self, event):
        pass  # el click real se maneja en _on_button_click, solo si no hubo arrastre

    def _show_menu(self, event):
        self.menu.tk_popup(event.x_root, event.y_root)

    # ---------- Lógica principal ----------

    def _on_button_click(self):
        if self._was_drag:
            return  # fue un arrastre, no un clic real
        if not self.api_key:
            self._ask_for_api_key()
            if not self.api_key:
                return
        if self.region is None:
            self._pick_region()
        else:
            self._capture_and_analyze()

    def _pick_region(self):
        RegionPicker(self.root, on_region_selected=self._on_region_selected)

    def _on_region_selected(self, bbox):
        self.region = bbox
        if self.fixed_frame:
            self.fixed_frame.update_region(bbox)
        else:
            self.fixed_frame = FixedFrame(self.root, bbox)

    def _change_region(self):
        self._pick_region()

    def _capture_and_analyze(self):
        left, top, right, bottom = self.region
        screenshot = ImageGrab.grab(bbox=(left, top, right, bottom))
        buffer = io.BytesIO()
        screenshot.save(buffer, format="PNG")
        image_bytes = buffer.getvalue()

        result_win = ResultWindow(self.root)

        def worker():
            try:
                answer = ask_about_image(image_bytes, self.api_key)
            except Exception as exc:  # noqa: BLE001
                self.root.after(0, lambda: result_win.show_error(str(exc)))
                return
            self.root.after(0, lambda: result_win.show_result(answer))

        threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    App()
