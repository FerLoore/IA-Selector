"""
Punto de entrada de la app.

Flujo:
1. Si no hay API key guardada, la pide una vez (ventana simple).
2. Muestra un botón flotante, arrastrable, siempre encima de todo.
3. Primer clic: pide marcar el área (RegionPicker) y deja un marco fijo (FixedFrame).
4. Clics siguientes: captura esa misma área y la manda a Gemini.
5. Clic derecho sobre el botón: menú para cambiar de área o salir.
"""
import hashlib
import io
import os
import sys
import threading
import time
import tkinter as tk
from tkinter import simpledialog, messagebox

# pyrefly: ignore [missing-import]
from PIL import ImageGrab, Image, ImageTk

import config
from ai_client import ask_about_image
from overlay import RegionPicker, FixedFrame, OptionHighlight
from result_window import ResultWindow


def get_resource_path(relative_path):
    """Obtiene la ruta absoluta para un recurso, compatible con desarrollo y PyInstaller"""
    if getattr(sys, 'frozen', False):
        # PyInstaller crea una carpeta temporal y guarda la ruta en _MEIPASS
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()  # no mostramos ventana principal, solo el botón

        # Configurar el icono global de la app
        try:
            self.app_icon = ImageTk.PhotoImage(Image.open(get_resource_path("logoTraslucido.png")))
            self.root.iconphoto(True, self.app_icon)
        except Exception:
            pass

        self.api_keys_pool = config.load_api_keys_pool()
        self.current_key_idx = 0
        self.api_key = config.load_api_key()
        if not self.api_key and not self.api_keys_pool:
            self._ask_for_api_key()

        self.region = None  # (left, top, right, bottom)
        self.fixed_frame = None
        self.current_result_win = None
        self.current_highlight = None
        self.hover_timer = None
        self.is_analyzing = False
        self.last_capture_hash = None
        self.last_result = None  # (answer, box)
        self.last_trigger_time = 0.0

        # Cargar y registrar el atajo de teclado global
        self.hotkey = config.load_hotkey()
        self._register_global_hotkey()

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
            raw_logo = Image.open(get_resource_path("logoTraslucido.png"))
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
        self.menu.add_command(label="📍 Ver dónde está el marco (Ctrl+Shift+F)", command=self._show_frame_location)
        self.menu.add_command(label="Ver cuota y tokens", command=self._show_quota_window)
        self.menu.add_command(label="Cambiar área", command=self._change_region)
        self.menu.add_command(label="Cambiar API key", command=self._ask_for_api_key)
        self.menu.add_command(label="Directorio archivo API keys (.txt)", command=self._configure_keys_file)
        self.menu.add_separator()
        self.menu.add_command(label="Salir", command=self.root.destroy)
        self.btn.bind("<Button-3>", self._show_menu)
        self.btn.bind("<Button-2>", lambda e: self._show_frame_location())

        # Eventos hover para cambiar la opacidad
        self.btn.bind("<Enter>", self._on_button_enter)
        self.btn.bind("<Leave>", self._on_button_leave)

        self._was_drag = False

    def _start_drag(self, event):
        self._drag_data = {"x": event.x, "y": event.y}
        self._was_drag = False
        
        # Cancelar el temporizador de hover si se empieza a arrastrar el botón
        if self.hover_timer:
            self.root.after_cancel(self.hover_timer)
            self.hover_timer = None

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
            
        # Iniciar temporizador para activar la IA automáticamente al mantener el mouse (hover)
        # Esperamos 1500ms (1.5s) para evitar disparos accidentales al pasar el mouse por encima
        if self.hover_timer:
            self.root.after_cancel(self.hover_timer)
        self.hover_timer = self.root.after(1500, self._on_hover_trigger)

    def _on_button_leave(self, event):
        try:
            self.btn_win.attributes("-alpha", 0.35)  # Se desvanece de nuevo al salir
        except tk.TclError:
            pass
            
        # Cancelar el temporizador si el mouse sale antes de que se dispare
        if self.hover_timer:
            self.root.after_cancel(self.hover_timer)
            self.hover_timer = None

    # ---------- Lógica principal ----------

    def _has_api_keys(self) -> bool:
        return bool(self.api_keys_pool or self.api_key)

    def _on_button_click(self):
        if self._was_drag:
            return  # fue un arrastre, no un clic real
        if self.hover_timer:
            self.root.after_cancel(self.hover_timer)
            self.hover_timer = None
        if self.is_analyzing:
            return
            
        if not self._has_api_keys():
            self._ask_for_api_key()
            if not self._has_api_keys():
                return
        if self.region is None:
            self._pick_region()
        else:
            self._capture_and_analyze()

    def _on_hover_trigger(self):
        self.hover_timer = None
        if self.is_analyzing:
            return
            
        if not self._has_api_keys():
            self._ask_for_api_key()
            if not self._has_api_keys():
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
        self.last_capture_hash = None
        self.last_result = None
        if self.fixed_frame:
            self.fixed_frame.update_region(bbox)
        else:
            self.fixed_frame = FixedFrame(self.root, bbox)
        # Mostrarlo temporalmente (2.5s) para ver dónde quedó y luego desaparece solo
        self.fixed_frame.flash_location(2500)

    def _show_frame_location(self):
        if not self.region:
            self._pick_region()
            return
        if not self.fixed_frame:
            self.fixed_frame = FixedFrame(self.root, self.region)
        # Muestra el marco claramente durante 2.5s y se desvanece por completo
        self.fixed_frame.flash_location(2500)

    def _change_region(self):
        self._pick_region()

    def _capture_and_analyze(self):
        # Debounce: evitar peticiones consecutivas con menos de 1.2 segundos de diferencia
        now = time.time()
        if now - self.last_trigger_time < 1.2:
            return
        self.last_trigger_time = now

        left, top, right, bottom = self.region
        screenshot = ImageGrab.grab(bbox=(left, top, right, bottom))

        # Optimizar imagen: máx 768px (consume solo 1 tile = 258 tokens en Gemini)
        # y compresión rápida con BILINEAR y calidad 75
        img = screenshot.convert("RGB")
        max_dim = 768
        w, h = img.size
        if max(w, h) > max_dim:
            scale = max_dim / float(max(w, h))
            new_w = max(1, int(w * scale))
            new_h = max(1, int(h * scale))
            img = img.resize((new_w, new_h), Image.Resampling.BILINEAR)

        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=75)
        image_bytes = buffer.getvalue()

        # Comprobar si la captura es idéntica a la anterior (Caché local - 0 cuota consumida)
        img_hash = hashlib.md5(image_bytes).hexdigest()

        # Si ya existe la ventana de resultados y está abierta, la reutilizamos y conservamos su posición
        if self.current_result_win and self.current_result_win.win.winfo_exists():
            result_win = self.current_result_win
        else:
            result_win = ResultWindow(self.root)
            self.current_result_win = result_win

        if self.last_capture_hash == img_hash and self.last_result is not None:
            cached_answer, cached_tok = self.last_result
            daily_info = config.get_daily_usage()
            result_win.show_result(
                f"{cached_answer}\n\n[⚡ Resultado en caché local - 0 cuota consumida]",
                token_info={"total_tokens": 0, "prompt_tokens": 0, "output_tokens": 0},
                daily_info=daily_info,
            )
            return

        result_win.show_loading()
        self.is_analyzing = True

        def worker():
            if self.api_keys_pool:
                keys_to_use = self.api_keys_pool
                start_idx = self.current_key_idx
            else:
                keys_to_use = self.api_key
                start_idx = 0

            try:
                answer, token_info, used_idx = ask_about_image(
                    image_bytes,
                    keys_to_use,
                    mime_type="image/jpeg",
                    start_key_index=start_idx,
                )
            except Exception as exc:  # noqa: BLE001
                err_msg = str(exc)
                self.root.after(0, lambda: result_win.show_error(err_msg))
                self.root.after(0, self._set_analyzing_false)
                return

            if self.api_keys_pool:
                self.current_key_idx = used_idx
                if token_info:
                    token_info["key_display"] = f"Key #{used_idx + 1}/{len(self.api_keys_pool)}"

            tokens_spent = token_info.get("total_tokens", 0) if token_info else 0
            daily_info = config.record_usage(tokens_spent)

            self.last_capture_hash = img_hash
            self.last_result = (answer, token_info)

            self.root.after(0, lambda: result_win.show_result(answer, token_info=token_info, daily_info=daily_info))
            self.root.after(0, self._set_analyzing_false)

        threading.Thread(target=worker, daemon=True).start()

    def _show_quota_window(self):
        from result_window import show_quota_dialog
        daily_info = config.get_daily_usage()
        last_tok = self.last_result[1] if self.last_result else None
        show_quota_dialog(self.root, token_info=last_tok, daily_info=daily_info)

    def _set_analyzing_false(self):
        self.is_analyzing = False

    def _highlight_correct_option(self, box):
        # Desactivado a petición: no marcar con verde en pantalla
        pass

    def _register_global_hotkey(self):
        try:
            import keyboard
            keyboard.clear_all_hotkeys()
        except Exception:
            pass

        try:
            import keyboard
            if self.hotkey:
                # Registramos el atajo global de captura y análisis.
                keyboard.add_hotkey(self.hotkey, lambda: self.root.after(0, self._on_hotkey_pressed))
            # Atajo global para iluminar y saber dónde está el marco (desaparece solo tras 2.5s)
            keyboard.add_hotkey("ctrl+shift+f", lambda: self.root.after(0, self._show_frame_location))
        except Exception as e:
            print(f"Error registrando atajo: {e}")

    def _on_hotkey_pressed(self):
        if self.is_analyzing:
            return
        if not self._has_api_keys():
            self._ask_for_api_key()
            if not self._has_api_keys():
                return
        if self.region is None:
            self._pick_region()
        else:
            self._capture_and_analyze()

    def _configure_keys_file(self):
        self.root.deiconify()
        self.root.withdraw()

        current = config.load_api_keys_file() or ""
        prompt_text = (
            "Ingresa la ruta o directorio del archivo .txt con tus API Keys de Gemini\n"
            "(una clave por línea):\n\n"
            f"Ruta actual: {current if current else '(Ninguna - usando API key única)'}\n\n"
            "• Pega la ruta al archivo .txt o al directorio que lo contiene.\n"
            "• Si dejas el campo vacío y presionas Aceptar, se desactivará el archivo y se usará la API key única."
        )

        path_input = simpledialog.askstring(
            "Archivo de API Keys (.txt)",
            prompt_text,
            initialvalue=current,
            parent=self.root,
        )

        if path_input is not None:
            clean_path = path_input.strip().strip('"').strip("'")
            if not clean_path:
                config.save_api_keys_file(None)
                self.api_keys_pool = []
                self.current_key_idx = 0
                messagebox.showinfo(
                    "Modo API Key Única",
                    "Se desactivó el archivo .txt.\nLa aplicación ahora usará la API key individual guardada en 'Cambiar API key'.",
                    parent=self.root,
                )
            else:
                config.save_api_keys_file(clean_path)
                keys = config.load_api_keys_pool()
                if keys:
                    self.api_keys_pool = keys
                    self.current_key_idx = 0
                    messagebox.showinfo(
                        "API Keys Cargadas",
                        f"¡Éxito! Se cargaron {len(keys)} API keys desde:\n{clean_path}\n\n"
                        "Si una clave agota su cuota o tokens (429), el sistema cambiará automáticamente a la siguiente clave del archivo.",
                        parent=self.root,
                    )
                else:
                    messagebox.showwarning(
                        "Sin claves encontradas",
                        f"No se pudieron encontrar claves válidas en la ruta:\n{clean_path}\n\n"
                        "Asegúrate de que el archivo termine en .txt y tenga una API key por línea.",
                        parent=self.root,
                    )


if __name__ == "__main__":
    App()
