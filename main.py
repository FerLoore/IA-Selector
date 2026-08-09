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
from PIL import ImageGrab, Image, ImageTk

import config
from ai_client import ask_about_image
from overlay import RegionPicker, FixedFrame, OptionHighlight
from result_window import ResultWindow


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()  # no mostramos ventana principal, solo el botón

        # Configurar el icono global de la app
        try:
            self.app_icon = ImageTk.PhotoImage(Image.open("logoTraslucido.png"))
            self.root.iconphoto(True, self.app_icon)
        except Exception:
            pass

        self.api_key = config.load_api_key()
        if not self.api_key:
            self._ask_for_api_key()

        self.region = None  # (left, top, right, bottom)
        self.fixed_frame = None
        self.current_result_win = None
        self.current_highlight = None

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

        # Cargar y redimensionar el logo
        try:
            raw_logo = Image.open("logoTraslucido.png")
            logo_resized = raw_logo.resize((48, 48), Image.Resampling.LANCZOS)
            
            # Procesar la imagen para que sea compatible con transparentcolor (eliminar semitransparencias)
            logo_resized = logo_resized.convert("RGBA")
            pixels = list(logo_resized.getdata())
            new_pixels = []
            for p in pixels:
                if p[3] < 128:
                    new_pixels.append((255, 0, 255, 255))  # Magenta puro (transparente en Windows)
                else:
                    new_pixels.append((p[0], p[1], p[2], 255))  # Totalmente opaco
            logo_resized.putdata(new_pixels)
            
            self.logo_img = ImageTk.PhotoImage(logo_resized)
        except Exception:
            self.logo_img = None

        transparent_color = "magenta"
        self.btn_win.configure(bg=transparent_color)
        try:
            self.btn_win.attributes("-transparentcolor", transparent_color)
            self.btn_win.attributes("-alpha", 0.35)  # Opacidad por defecto discreta (35%)
        except tk.TclError:
            pass

        # Usamos tk.Label en lugar de tk.Button para evitar bordes o relieves del tema del OS
        # que arruinarían la transparencia de color de Tkinter.
        self.btn = tk.Label(
            self.btn_win, image=self.logo_img,
            bg=transparent_color,
            bd=0, highlightthickness=0,
        )
        self.btn.pack(padx=4, pady=4)

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

        # Eventos hover para cambiar la opacidad
        self.btn.bind("<Enter>", self._on_button_enter)
        self.btn.bind("<Leave>", self._on_button_leave)

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
        if not self._was_drag:
            self._on_button_click()

    def _show_menu(self, event):
        self.menu.tk_popup(event.x_root, event.y_root)

    def _on_button_enter(self, event):
        try:
            self.btn_win.attributes("-alpha", 0.95)  # Se vuelve opaco al pasar el mouse
        except tk.TclError:
            pass

    def _on_button_leave(self, event):
        try:
            self.btn_win.attributes("-alpha", 0.35)  # Se desvanece de nuevo al salir
        except tk.TclError:
            pass

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
        # Retardo de 180ms para garantizar que el click del botón original se procese
        # por completo antes de mapear la ventana de selección.
        self.root.after(180, lambda: RegionPicker(self.root, on_region_selected=self._on_region_selected))

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

        # Cerrar la ventana anterior si existe y está abierta
        if self.current_result_win and self.current_result_win.win.winfo_exists():
            try:
                self.current_result_win.win.destroy()
            except Exception:
                pass
        self.current_result_win = None

        result_win = ResultWindow(self.root)
        self.current_result_win = result_win

        def worker():
            try:
                answer, box = ask_about_image(image_bytes, self.api_key)
            except Exception as exc:  # noqa: BLE001
                err_msg = str(exc)
                self.root.after(0, lambda: result_win.show_error(err_msg))
                return
            self.root.after(0, lambda: result_win.show_result(answer))
            if box:
                self.root.after(0, lambda: self._highlight_correct_option(box))

        threading.Thread(target=worker, daemon=True).start()

    def _highlight_correct_option(self, box):
        # Cerrar el brillo anterior si existe y está abierto
        if self.current_highlight and self.current_highlight.win.winfo_exists():
            try:
                self.current_highlight.win.destroy()
            except Exception:
                pass
        self.current_highlight = None

        if not self.region:
            return
        left, top, right, bottom = self.region
        w = right - left
        h = bottom - top
        
        # box es [ymin, xmin, ymax, xmax] normalizados en [0, 1000]
        ymin, xmin, ymax, xmax = box
        
        opt_left = left + int((xmin / 1000.0) * w)
        opt_top = top + int((ymin / 1000.0) * h)
        opt_right = left + int((xmax / 1000.0) * w)
        opt_bottom = top + int((ymax / 1000.0) * h)
        
        self.current_highlight = OptionHighlight(self.root, (opt_left, opt_top, opt_right, opt_bottom))


if __name__ == "__main__":
    App()
