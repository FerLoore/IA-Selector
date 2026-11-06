"""
Manejo de configuración: guarda y lee la API key de Anthropic.
La guarda en un archivo config.json en la misma carpeta (NO la subas a git).
"""
from datetime import date
import json
import os
import sys

DAILY_REQUEST_LIMIT = 1500

if getattr(sys, 'frozen', False):
    # Si está empaquetado con PyInstaller, guardamos config.json junto al ejecutable (.exe)
    base_dir = os.path.dirname(sys.executable)
else:
    # Si se ejecuta desde el código fuente (.py)
    base_dir = os.path.dirname(os.path.abspath(__file__))

CONFIG_PATH = os.path.join(base_dir, "config.json")


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


def load_api_keys_file() -> str | None:
    """Retorna la ruta o directorio configurado para el archivo .txt de API keys."""
    config_data = load_config()
    return config_data.get("api_keys_file")


def save_api_keys_file(path: str | None) -> None:
    """Guarda o elimina la ruta al archivo .txt de API keys."""
    config_data = load_config()
    if path:
        config_data["api_keys_file"] = path.strip()
    else:
        config_data.pop("api_keys_file", None)
    save_config(config_data)


def load_api_keys_pool() -> list[str]:
    """
    Lee las API keys desde el archivo .txt configurado.
    Soporta tanto la ruta directa al archivo .txt como la ruta a una carpeta que contenga un .txt.
    Ignora líneas vacías o comentadas con '#'.
    """
    file_path = load_api_keys_file()
    if not file_path:
        return []

    # Si se especificó un directorio, buscar el primer archivo .txt dentro
    if os.path.isdir(file_path):
        txt_files = [
            os.path.join(file_path, f)
            for f in os.listdir(file_path)
            if f.lower().endswith(".txt") and os.path.isfile(os.path.join(file_path, f))
        ]
        if not txt_files:
            return []
        file_path = txt_files[0]

    if not os.path.isfile(file_path):
        return []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            keys = [
                line.strip()
                for line in f
                if line.strip() and not line.strip().startswith("#")
            ]
        return keys
    except Exception:
        return []


def get_daily_usage() -> dict:
    """Devuelve las estadísticas de uso de hoy y el saldo de consultas restantes."""
    today_str = date.today().isoformat()
    config_data = load_config()
    usage = config_data.get("usage", {})
    if usage.get("date") != today_str:
        return {
            "date": today_str,
            "requests_today": 0,
            "tokens_today": 0,
            "last_tokens": 0,
            "remaining_requests": DAILY_REQUEST_LIMIT,
            "limit": DAILY_REQUEST_LIMIT,
        }
    reqs = usage.get("requests_today", 0)
    return {
        "date": today_str,
        "requests_today": reqs,
        "tokens_today": usage.get("tokens_today", 0),
        "last_tokens": usage.get("last_tokens", 0),
        "remaining_requests": max(0, DAILY_REQUEST_LIMIT - reqs),
        "limit": DAILY_REQUEST_LIMIT,
    }


def record_usage(tokens: int) -> dict:
    """Registra una nueva consulta y acumula los tokens gastados para la fecha actual."""
    today_str = date.today().isoformat()
    config_data = load_config()
    usage = config_data.get("usage", {})
    if usage.get("date") != today_str:
        usage = {
            "date": today_str,
            "requests_today": 1,
            "tokens_today": tokens,
            "last_tokens": tokens,
        }
    else:
        usage["requests_today"] = usage.get("requests_today", 0) + 1
        usage["tokens_today"] = usage.get("tokens_today", 0) + tokens
        usage["last_tokens"] = tokens

    config_data["usage"] = usage
    save_config(config_data)
    reqs = usage["requests_today"]
    return {
        "date": today_str,
        "requests_today": reqs,
        "tokens_today": usage["tokens_today"],
        "last_tokens": tokens,
        "remaining_requests": max(0, DAILY_REQUEST_LIMIT - reqs),
        "limit": DAILY_REQUEST_LIMIT,
    }
