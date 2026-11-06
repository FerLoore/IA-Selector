"""
Cliente optimizado que envía la captura a Gemini usando conexión HTTPS persistente (Keep-Alive),
máxima reducción de tokens, reintentos automáticos transparentes (anti-503) y clúster de respaldo (fallback).
"""
import base64
import http.client
import json
import ssl
import threading
import time

# Cadena de modelos de alta disponibilidad: si uno está saturado (503), conmuta automáticamente al siguiente
MODELS_CHAIN = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-3.5-flash",
]
API_HOST = "generativelanguage.googleapis.com"

SYSTEM_PROMPT = (
    "Eres un asistente visual de pantalla ultra rápido, preciso y conciso.\n"
    "REGLAS ESTRICTAS DE RESPUESTA EN ESPAÑOL:\n"
    "1. PREGUNTAS DE OPCIÓN MÚLTIPLE O TEST: Da ÚNICAMENTE la respuesta o inciso correcto (ejemplo: 'B) París' o la opción exacta). "
    "Está TOTALMENTE PROHIBIDO dar explicaciones, justificaciones o razonamientos lógicos. Solo la opción/respuesta directa.\n"
    "2. SERIE O LISTA DE PREGUNTAS: Si la captura contiene varias preguntas, enuméralas directamente dando únicamente la opción/respuesta correcta de cada una, sin ninguna explicación (ejemplo:\n"
    "1. A) Opción correcta\n"
    "2. C) Opción correcta\n"
    "3. B) Opción correcta).\n"
    "3. PREGUNTAS ABIERTAS: Responde directamente y explica brevemente lo necesario de forma concisa (1 o 2 párrafos cortos como máximo).\n"
    "4. CÓDIGO O MATEMÁTICAS: Da el resultado o corrección directa sin explicaciones largas.\n"
    "5. NUNCA incluyas saludos, despedidas, relleno ni texto innecesario."
)


class GeminiOverloadedError(Exception):
    """503: Servidor de Google sobrecargado."""
    pass


class GeminiRateLimitError(Exception):
    """429: Cuota por minuto alcanzada."""
    pass


class GeminiModelNotFoundError(Exception):
    """404: Modelo no encontrado."""
    pass


class GeminiConnectionPool:
    """Mantiene un socket HTTPS abierto (Keep-Alive) para eliminar la latencia del handshake TLS (ahorra 200-350ms)."""

    def __init__(self, host: str = API_HOST):
        self.host = host
        self.conn = None
        self.lock = threading.Lock()
        self.ssl_context = ssl.create_default_context()

    def post(self, path: str, payload_bytes: bytes, api_key: str, timeout: int = 40) -> bytes:
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
            "Connection": "keep-alive",
        }
        with self.lock:
            for attempt in range(2):
                try:
                    if self.conn is None:
                        self.conn = http.client.HTTPSConnection(
                            self.host, timeout=timeout, context=self.ssl_context
                        )
                    self.conn.request("POST", path, body=payload_bytes, headers=headers)
                    resp = self.conn.getresponse()
                    body = resp.read()

                    if resp.status == 200:
                        return body
                    elif resp.status == 503:
                        raise GeminiOverloadedError("503: Clúster sobrecargado")
                    elif resp.status == 429:
                        raise GeminiRateLimitError("429: Límite por minuto alcanzado")
                    elif resp.status == 404:
                        raise GeminiModelNotFoundError(f"404: Modelo no disponible en {path}")
                    else:
                        err_text = body.decode("utf-8", errors="ignore")
                        raise RuntimeError(f"Error de la API de Gemini ({resp.status}): {err_text}")
                except (http.client.RemoteDisconnected, BrokenPipeError, ConnectionResetError):
                    # El socket Keep-Alive expiró en el servidor remoto; reconectamos en el siguiente intento
                    self.close()
                    if attempt == 1:
                        raise
                except (GeminiOverloadedError, GeminiRateLimitError, GeminiModelNotFoundError):
                    raise
                except Exception:
                    self.close()
                    raise

    def close(self):
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None


_pool = GeminiConnectionPool()


def ask_about_image(
    image_bytes: bytes,
    api_key: str | list[str],
    extra_instruction: str = "",
    mime_type: str = "image/jpeg",
    start_key_index: int = 0,
) -> tuple[str, dict | None, int]:
    """
    image_bytes: contenido JPEG optimizado de la captura.
    api_key: una clave individual (str) o una lista de claves (list[str]) para rotación automática.
    extra_instruction: contexto adicional opcional.
    mime_type: tipo MIME ('image/jpeg').
    start_key_index: índice de la clave por la cual comenzar la rotación.
    Devuelve un tuple (texto_respuesta, token_info, indice_clave_usada).
    """
    if isinstance(api_key, str):
        keys_pool = [api_key.strip()] if api_key.strip() else []
    else:
        keys_pool = [k.strip() for k in api_key if k and k.strip()]

    if not keys_pool:
        raise RuntimeError("No hay ninguna API key disponible para realizar la consulta.")

    b64_image = base64.standard_b64encode(image_bytes).decode("utf-8")

    user_text = "Responde según las reglas indicadas."
    if extra_instruction.strip():
        user_text += f"\n\nContexto adicional: {extra_instruction.strip()}"

    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"inline_data": {"mime_type": mime_type, "data": b64_image}},
                    {"text": user_text},
                ],
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 350,  # Evita respuestas largas que ralentizan la app y gastan tokens
            "thinkingConfig": {
                "thinkingBudget": 0  # Desactiva razonamiento oculto para velocidad instantánea
            },
        },
    }

    data = json.dumps(payload).encode("utf-8")

    # Reordenar las claves para comenzar en start_key_index
    n_keys = len(keys_pool)
    ordered_indices = [(start_key_index + i) % n_keys for i in range(n_keys)]
    ordered_keys = [keys_pool[idx] for idx in ordered_indices]

    last_error = None
    response_bytes = None
    successful_key_index = start_key_index

    # Iterar sobre las claves del pool (si una se agota, pasa de inmediato a la siguiente)
    for key_idx, current_api_key in zip(ordered_indices, ordered_keys):
        key_exhausted = False

        # Recorrer la cadena de modelos de respaldo si hay saturación (503)
        for model_name in MODELS_CHAIN:
            path = f"/v1beta/models/{model_name}:generateContent"

            # Hasta 2 intentos con pausa automática por modelo
            for attempt in range(2):
                try:
                    response_bytes = _pool.post(path, data, current_api_key)
                    successful_key_index = key_idx
                    break  # Petición completada con éxito
                except GeminiOverloadedError as e:
                    last_error = e
                    # Pausa breve de 500ms antes del reintento automático
                    time.sleep(0.5 * (attempt + 1))
                    continue
                except GeminiModelNotFoundError as e:
                    last_error = e
                    break
                except GeminiRateLimitError as e:
                    last_error = e
                    key_exhausted = True
                    break
                except (http.client.HTTPException, TimeoutError, OSError) as e:
                    reason_str = str(e).lower()
                    if "timed out" in reason_str:
                        last_error = RuntimeError(
                            "⌛ Tiempo de espera agotado (Timeout).\n\n"
                            "Google tardó demasiado en responder. La conexión está lenta o la API tiene alta demanda."
                        )
                    else:
                        last_error = RuntimeError(f"No se pudo conectar con Gemini: {e}")
                    time.sleep(0.4)
                    continue
                except Exception as e:
                    last_error = e
                    err_str = str(e).lower()
                    # Si la clave dio error de cuota o autenticación, marcarla para rotar
                    if "quota" in err_str or "api_key" in err_str or "key not valid" in err_str or "resource_exhausted" in err_str:
                        key_exhausted = True
                        break
                    time.sleep(0.4)
                    continue

            if response_bytes is not None or key_exhausted:
                break

        if response_bytes is not None:
            # Clave y modelo respondieron con éxito
            break

        # Si esta API key agotó su cuota y tenemos más claves en el archivo, rotar a la siguiente
        if key_exhausted and len(keys_pool) > 1:
            continue

    if response_bytes is None:
        if isinstance(last_error, GeminiOverloadedError):
            raise RuntimeError(
                "⚠️ Servidores de Google sobrecargados temporalmente (503).\n\n"
                "Se intentó con los modelos de respaldo pero Google sigue saturado a nivel global. "
                "Por favor espera unos segundos y vuelve a presionar el atajo."
            )
        elif isinstance(last_error, GeminiRateLimitError):
            pool_msg = f" (se probaron las {len(keys_pool)} API keys configuradas)" if len(keys_pool) > 1 else ""
            raise RuntimeError(
                f"⏳ Límite de consultas o cuota alcanzada (429){pool_msg}.\n\n"
                "Todas las claves configuradas han alcanzado su límite por minuto o cuota diaria."
            )
        elif last_error:
            raise last_error
        else:
            raise RuntimeError("No se obtuvo respuesta de los servidores de Google.")

    try:
        result = json.loads(response_bytes.decode("utf-8"))
        candidates = result.get("candidates", [])
        if not candidates:
            feedback = result.get("promptFeedback", {})
            block_reason = feedback.get("blockReason", "desconocido")
            return f"La consulta fue bloqueada por filtros de seguridad ({block_reason}).", None, successful_key_index

        candidate = candidates[0]
        if candidate.get("finishReason") == "RECITATION":
            return (
                "Respuesta bloqueada por el filtro de derechos de autor (RECITATION).\n\n"
                "Intenta capturar un área ligeramente distinta o más enfocada en la pregunta."
            ), None, successful_key_index

        parts = candidate.get("content", {}).get("parts", [])
        text = "\n".join(p.get("text", "") for p in parts).strip()

        usage = result.get("usageMetadata", {})
        token_info = {
            "prompt_tokens": usage.get("promptTokenCount", 0),
            "output_tokens": usage.get("candidatesTokenCount", 0),
            "total_tokens": usage.get("totalTokenCount", 0),
        }
        return text or "(La IA no devolvió texto)", token_info, successful_key_index

    except Exception:
        return f"No se pudo interpretar la respuesta:\n{json.dumps(result, indent=2, ensure_ascii=False)}", None, successful_key_index


