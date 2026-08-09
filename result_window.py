"""
Ventana emergente que muestra "Pensando..." y luego la respuesta de la IA.
"""
import tkinter as tk
from tkinter import scrolledtext


class ResultWindow:
    def __init__(self, root: tk.Tk):
        self.win = tk.Toplevel(root)
        self.win.title("Respuesta de la IA")
        self.win.attributes("-topmost", True)
        self.win.geometry("420x300+80+80")
        self.win.configure(bg="#1e1e1e")

        self.label = tk.Label(
            self.win, text="Pensando...", fg="#4da3ff", bg="#1e1e1e",
            font=("Segoe UI", 11, "bold"), anchor="w",
        )
        self.label.pack(fill="x", padx=12, pady=(12, 4))

        self.text = scrolledtext.ScrolledText(
            self.win, wrap="word", bg="#252525", fg="white",
            font=("Segoe UI", 11), relief="flat", padx=10, pady=10,
        )
        self.text.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.text.insert("1.0", "Analizando la captura, un momento...")
        self.text.config(state="disabled")

        close_btn = tk.Button(
            self.win, text="Cerrar", command=self.win.destroy,
            bg="#3a3a3a", fg="white", relief="flat", padx=10, pady=4,
        )
        close_btn.pack(pady=(0, 12))

    def show_result(self, text: str):
        self.label.config(text="Respuesta:")
        self.text.config(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", text)
        self.text.config(state="disabled")

    def show_error(self, message: str):
        self.label.config(text="Error", fg="#ff6b6b")
        self.text.config(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", message)
        self.text.config(state="disabled")
