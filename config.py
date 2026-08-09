"""
Manejo de configuración: guarda y lee la API key de Anthropic.
La guarda en un archivo config.json en la misma carpeta (NO la subas a git).
"""
import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def load_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_config(config_dict: dict) -> None:
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config_dict, f, indent=4)
    except Exception:
        pass


def load_api_key() -> str | None:
    # 1) Variable de entorno tiene prioridad
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key

    # 2) Archivo local config.json
    config_data = load_config()
    return config_data.get("api_key")


def save_api_key(api_key: str) -> None:
    config_data = load_config()
    config_data["api_key"] = api_key
    save_config(config_data)


def load_hotkey() -> str:
    config_data = load_config()
    return config_data.get("hotkey", "ctrl+shift+x")


def save_hotkey(hotkey: str) -> None:
    config_data = load_config()
    config_data["hotkey"] = hotkey
    save_config(config_data)
