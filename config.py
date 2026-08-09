"""
Manejo de configuración: guarda y lee la API key de Anthropic.
La guarda en un archivo config.json en la misma carpeta (NO la subas a git).
"""
import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def load_api_key() -> str | None:
    # 1) Variable de entorno tiene prioridad
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key

    # 2) Archivo local config.json
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("api_key")
        except Exception:
            return None
    return None


def save_api_key(api_key: str) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump({"api_key": api_key}, f)
