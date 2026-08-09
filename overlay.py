"""
Dos piezas:

1) RegionPicker: superposición de pantalla completa, semi-transparente,
   donde el usuario arrastra el mouse UNA VEZ para marcar el área.
   Al soltar, devuelve las coordenadas (no captura nada todavía).

2) FixedFrame: dibuja un marco rojo delgado y fijo alrededor de esa área,
   que se queda visible en pantalla permanentemente y NO bloquea clics
   (click-through en Windows), como el rectángulo rojo del ejemplo.
"""
import tkinter as tk

from win_utils import make_click_through


class RegionPicker:
    """Se muestra una vez para que el usuario dibuje el rectángulo."""

    def __init__(self, root: tk.Tk, on_region_selected):
        self.root = root
        self.on_region_selected = on_region_selected

        self.overlay = tk.Toplevel(root)
        self.overlay.attributes("-fullscreen", True)
        self.overlay.attributes("-alpha", 0.25)
        self.overlay.attributes("-topmost", True)
        self.overlay.configure(bg="black")
        self.overlay.config(cursor="cross")
        self.overlay.focus_force()

        self.canvas = tk.Canvas(self.overlay, bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.start_x = None
        self.start_y = None
        self.rect_id = None

        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.overlay.bind("<Escape>", lambda e: self.overlay.destroy())

        self.canvas.create_text(
            self.overlay.winfo_screenwidth() // 2,
            40,
            text="Marca el área que quieres que la IA lea (queda fija). Esc para cancelar.",
            fill="white",
            font=("Segoe UI", 14, "bold"),
        )

    def _on_press(self, event):
        self.start_x, self.start_y = event.x, event.y
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        self.rect_id = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline="#4da3ff", width=2,
        )

    def _on_drag(self, event):
        if self.start_x is None or self.start_y is None:
            return
        self.canvas.coords(self.rect_id, self.start_x, self.start_y, event.x, event.y)

    def _on_release(self, event):
        if self.start_x is None or self.start_y is None:
            return
        x1, y1 = self.start_x, self.start_y
        x2, y2 = event.x, event.y
        left, top = min(x1, x2), min(y1, y2)
        right, bottom = max(x1, x2), max(y1, y2)

        if right - left < 10 or bottom - top < 10:
            # Si el trazo es muy chico (ej: click accidental), no cerramos la ventana.
            # Borramos el rectángulo dibujado y permitimos reintentar el trazo.
            if self.rect_id:
                self.canvas.delete(self.rect_id)
            self.start_x = None
            self.start_y = None
            return

        self.overlay.destroy()
        self.on_region_selected((left, top, right, bottom))


class FixedFrame:
    """Marco sutil y semi-transparente alrededor de la región elegida. No bloquea clics."""

    def __init__(self, root: tk.Tk, bbox):
        self.root = root
        self.win = tk.Toplevel(root)
        self.set_region(bbox)

        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        try:
            self.win.attributes("-alpha", 0.45)  # Hacer que la ventana/borde sea semi-transparente (45% opacidad)
        except tk.TclError:
            pass

        transparent = "magenta"  # color "clave" que se vuelve invisible
        self.win.configure(bg=transparent)
        try:
            self.win.attributes("-transparentcolor", transparent)
        except tk.TclError:
            pass  # en sistemas donde no aplica, el fondo simplemente no será transparente

        self.canvas = tk.Canvas(self.win, bg=transparent, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self._draw_border()

        self.win.update_idletasks()
        make_click_through(self.win)

    def set_region(self, bbox):
        left, top, right, bottom = bbox
        self.bbox = bbox
        self.win.geometry(f"{right - left}x{bottom - top}+{left}+{top}")

    def _draw_border(self):
        self.canvas.delete("all")
        w = self.bbox[2] - self.bbox[0]
        h = self.bbox[3] - self.bbox[1]
        
        # Parámetros para un borde redondeado y discreto (color blanco con alpha general de 0.45)
        r = 8  # Radio de esquinas redondeadas
        color = "#ffffff"
        width = 2
        
        # Evitar errores si la selección es más pequeña que el doble del radio
        r = min(r, w // 2, h // 2)

        if r > 0:
            # 4 bordes rectos rectangulares
            self.canvas.create_line(2 + r, 2, w - 2 - r, 2, fill=color, width=width)
            self.canvas.create_line(2 + r, h - 2, w - 2 - r, h - 2, fill=color, width=width)
            self.canvas.create_line(2, 2 + r, 2, h - 2 - r, fill=color, width=width)
            self.canvas.create_line(w - 2, 2 + r, w - 2, h - 2 - r, fill=color, width=width)

            # 4 arcos para lograr las esquinas redondeadas
            self.canvas.create_arc(2, 2, 2 + 2*r, 2 + 2*r, start=90, extent=90, style="arc", outline=color, width=width)
            self.canvas.create_arc(w - 2 - 2*r, 2, w - 2, 2 + 2*r, start=0, extent=90, style="arc", outline=color, width=width)
            self.canvas.create_arc(2, h - 2 - 2*r, 2 + 2*r, h - 2, start=180, extent=90, style="arc", outline=color, width=width)
            self.canvas.create_arc(w - 2 - 2*r, h - 2 - 2*r, w - 2, h - 2, start=270, extent=90, style="arc", outline=color, width=width)
        else:
            self.canvas.create_rectangle(2, 2, w - 2, h - 2, outline=color, width=width)

    def update_region(self, bbox):
        self.set_region(bbox)
        self.win.update_idletasks()
        self._draw_border()

    def destroy(self):
        self.win.destroy()
