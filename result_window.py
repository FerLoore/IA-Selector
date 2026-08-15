"""
Ventana emergente moderna, compacta y discreta que muestra "Pensando..." y luego la respuesta de la IA.
Cuenta con opacidad adaptativa, barra de título personalizada dragable, y opción de colapso.
"""
import sys
import tkinter as tk
from tkinter import ttk


class ResultWindow:
    def __init__(self, root: tk.Tk):
        self.win = tk.Toplevel(root)
        self.win.overrideredirect(True)  # Sin bordes estándar para máxima discreción
        self.win.attributes("-topmost", True)
        
        # Dimensiones por defecto
        self.width = 420
        self.height = 260
        self.collapsed = False

        # Posicionamiento inteligente cerca del cursor del mouse, sin salirse de la pantalla
        mx = root.winfo_pointerx()
        my = root.winfo_pointery()
        screen_w = root.winfo_screenwidth()
        screen_h = root.winfo_screenheight()
        x = max(10, min(mx + 20, screen_w - self.width - 20))
        y = max(10, min(my + 10, screen_h - self.height - 40))
        self.win.geometry(f"{self.width}x{self.height}+{x}+{y}")

        # Opacidad adaptativa (discreta al perder foco/mouse)
        self.idle_opacity = 0.25
        self.active_opacity = 0.95
        try:
            self.win.attributes("-alpha", self.active_opacity)
        except tk.TclError:
            pass

        # Aplicar estilo de Windows 11 redondeado vía DWM si está disponible
        self._apply_rounded_corners()

        # Marco de borde (1px)
        self.win.configure(bg="#2d2d30")
        
        # Contenedor principal
        self.container = tk.Frame(self.win, bg="#121214")
        self.container.pack(fill="both", expand=True, padx=1, pady=1)

        # Barra de título personalizada
        self.title_bar = tk.Frame(self.container, bg="#18181b", height=28)
        self.title_bar.pack(fill="x")
        self.title_bar.pack_propagate(False)

        # Título
        self.title_label = tk.Label(
            self.title_bar, text="IA Selector", fg="#8a8a8f", bg="#18181b",
            font=("Segoe UI", 9, "bold")
        )
        self.title_label.pack(side="left", padx=10)

        # Dragging de la ventana
        self._drag_x = 0
        self._drag_y = 0
        self.title_bar.bind("<ButtonPress-1>", self._start_drag)
        self.title_bar.bind("<B1-Motion>", self._do_drag)
        self.title_label.bind("<ButtonPress-1>", self._start_drag)
        self.title_label.bind("<B1-Motion>", self._do_drag)

        # Controles en la barra de título
        self.control_frame = tk.Frame(self.title_bar, bg="#18181b")
        self.control_frame.pack(side="right", padx=5)

        # Helper para botones de la barra de título
        def create_title_btn(text, command, hover_fg="#ffffff"):
            btn = tk.Label(
                self.control_frame, text=text, fg="#8a8a8f", bg="#18181b",
                font=("Segoe UI", 9), cursor="hand2", padx=6
            )
            btn.bind("<Button-1>", lambda e: command())
            btn.bind("<Enter>", lambda e: btn.config(fg=hover_fg))
            btn.bind("<Leave>", lambda e: btn.config(fg="#8a8a8f"))
            btn.pack(side="left")
            return btn

        self.copy_btn = create_title_btn("Copiar", self._copy_to_clipboard, "#4da3ff")
        self.collapse_btn = create_title_btn("▲", self._toggle_collapse, "#ffb300")
        self.close_btn = create_title_btn("✕", self.win.destroy, "#ff6b6b")

        # Label de estado interno
        self.status_label = tk.Label(
            self.container, text="Pensando...", fg="#4da3ff", bg="#121214",
            font=("Segoe UI", 9, "bold"), anchor="w"
        )
        self.status_label.pack(fill="x", padx=12, pady=(6, 2))

        # Configurar estilo TTK para scrollbar oscura
        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass
        self.style.configure(
            "Discreet.Vertical.TScrollbar",
            gripcount=0,
            background="#252528",
            troughcolor="#121214",
            bordercolor="#121214",
            arrowcolor="#6a6a6f",
            lightcolor="#252528",
            darkcolor="#252528",
        )

        # Área de texto scrollable personalizada
        self.text_frame = tk.Frame(self.container, bg="#121214")
        self.text_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.text = tk.Text(
            self.text_frame, wrap="word", bg="#18181b", fg="#e3e3e6",
            insertbackground="white", selectbackground="#38383c",
            font=("Segoe UI", 10), relief="flat", padx=8, pady=8,
            bd=0, highlightthickness=0
        )
        self.scrollbar = ttk.Scrollbar(
            self.text_frame, orient="vertical", command=self.text.yview,
            style="Discreet.Vertical.TScrollbar"
        )
        self.text.configure(yscrollcommand=self.scrollbar.set)

        self.text.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.text.insert("1.0", "Analizando la captura, un momento...")
        self.text.config(state="disabled")

        # Agarrador de redimensionamiento (resize grip) discreto en la esquina inferior derecha
        self.grip = tk.Canvas(
            self.container, width=10, height=10,
            bg="#121214", bd=0, highlightthickness=0,
            cursor="size_nw_se"
        )
        self.grip.place(relx=1.0, rely=1.0, anchor="se")
        
        # Dibujar líneas diagonales clásicas de grip en el canvas
        self.grip.create_line(10, 4, 4, 10, fill="#4a4a4f")
        self.grip.create_line(10, 7, 7, 10, fill="#4a4a4f")

        self.grip.bind("<ButtonPress-1>", self._start_resize)
        self.grip.bind("<B1-Motion>", self._do_resize)

        # Binds para opacidad adaptativa en hover
        self.win.bind("<Enter>", self._on_enter)
        self.win.bind("<Leave>", self._on_leave)

    def _apply_rounded_corners(self):
        if sys.platform != "win32":
            return
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetParent(self.win.winfo_id())
            DWMWA_WINDOW_CORNER_PREFERENCE = 33
            DWMWCP_ROUND = 2  # Esquinas redondeadas normales
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 
                DWMWA_WINDOW_CORNER_PREFERENCE, 
                ctypes.byref(ctypes.c_int(DWMWCP_ROUND)), 
                ctypes.sizeof(ctypes.c_int)
            )
        except Exception:
            pass

    def _start_drag(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _do_drag(self, event):
        dx = event.x - self._drag_x
        dy = event.y - self._drag_y
        x = self.win.winfo_x() + dx
        y = self.win.winfo_y() + dy
        self.win.geometry(f"+{x}+{y}")

    def _start_resize(self, event):
        self._resize_start_x = event.x_root
        self._resize_start_y = event.y_root
        self._resize_start_w = self.win.winfo_width()
        self._resize_start_h = self.win.winfo_height()

    def _do_resize(self, event):
        dx = event.x_root - self._resize_start_x
        dy = event.y_root - self._resize_start_y
        
        new_w = max(250, self._resize_start_w + dx)
        new_h = max(100, self._resize_start_h + dy)
        
        x = self.win.winfo_x()
        y = self.win.winfo_y()
        
        if not self.collapsed:
            self.width = new_w
            self.height = new_h
            self.win.geometry(f"{self.width}x{self.height}+{x}+{y}")
        else:
            self.width = new_w
            self.win.geometry(f"{self.width}x28+{x}+{y}")

    def _copy_to_clipboard(self):
        self.win.clipboard_clear()
        self.win.clipboard_append(self.text.get("1.0", "end-1c"))
        self.win.update()
        
        # Indicador visual temporal en el botón de copiar
        self.copy_btn.config(text="✓ Copiado", fg="#4caf50")
        self.win.after(1500, lambda: self.copy_btn.config(text="Copiar", fg="#8a8a8f"))

    def _toggle_collapse(self):
        x = self.win.winfo_x()
        y = self.win.winfo_y()
        if self.collapsed:
            # Expandir a tamaño completo
            self.win.geometry(f"{self.width}x{self.height}+{x}+{y}")
            self.collapse_btn.config(text="▲")
            self.collapsed = False
        else:
            # Colapsar a barra de título
            self.width = self.win.winfo_width()
            self.height = self.win.winfo_height()
            self.win.geometry(f"{self.width}x28+{x}+{y}")
            self.collapse_btn.config(text="▼")
            self.collapsed = True

    def _on_enter(self, event):
        try:
            self.win.attributes("-alpha", self.active_opacity)
        except tk.TclError:
            pass

    def _on_leave(self, event):
        # Asegurarse de que el cursor realmente haya salido de los límites de la ventana
        x, y = self.win.winfo_pointerxy()
        rx = self.win.winfo_rootx()
        ry = self.win.winfo_rooty()
        rw = self.win.winfo_width()
        rh = self.win.winfo_height()
        
        if not (rx <= x <= rx + rw and ry <= y <= ry + rh):
            try:
                self.win.attributes("-alpha", self.idle_opacity)
            except tk.TclError:
                pass

    def show_result(self, text: str):
        self.status_label.config(text="Respuesta:", fg="#4da3ff")
        self.text.config(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", text)
        self.text.config(state="disabled")

    def show_error(self, message: str):
        self.status_label.config(text="Error:", fg="#ff6b6b")
        self.text.config(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", message)
        self.text.config(state="disabled")
