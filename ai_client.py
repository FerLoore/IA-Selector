"""
Cliente que envía la imagen capturada a Gemini (Google AI Studio, capa
gratuita) y devuelve la respuesta en texto.

Usa la API REST directamente (no depende de un SDK que pueda cambiar).
Modelo: gemini-2.5-flash -> buen balance de calidad/velocidad y el de
mejor cuota gratuita para este tipo de uso.
"""
import base64
import json
import urllib.request
import urllib.error

MODEL = "gemini-3.6-flash"
ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

SYSTEM_PROMPT = (
    "Estás integrado en una herramienta de selección de pantalla estilo "
    "'Circle to Search'. El usuario marca una zona fija de su pantalla y "
    "cada cierto tiempo te envía una nueva captura de esa misma zona. Tu "
    "trabajo es mirar la imagen y responder directamente lo que corresponda:\n"
    "- Si hay una pregunta (examen, formulario, trivia, etc.), respóndela "
    "directamente y de forma breve, con la justificación mínima necesaria.\n"
    "- Si hay una operación matemática, resuélvela y muestra el resultado.\n"
    "- Si hay código con un error, indica el error y la corrección.\n"
    "- Si es texto en otro idioma, tradúcelo.\n"
    "- Si no hay una tarea clara, describe brevemente qué se ve y ofrece la "
    "información más útil posible.\n"
    "Responde siempre en español, de forma directa y concisa. No repitas la "
    "pregunta, ve directo a la respuesta.\n"
    "IMPORTANTE: Para evitar activar filtros de derechos de autor (recitation), "
    "NUNCA copies textos extensos o códigos protegidos de forma exacta. Explica, "
    "resume y parafrasea siempre usando tus propias palabras."
)


def ask_about_image(image_bytes: bytes, api_key: str, extra_instruction: str = "") -> str:
    """
    image_bytes: contenido PNG de la captura de pantalla.
    api_key: API key de Google AI Studio (gratis en aistudio.google.com/apikey).
    extra_instruction: texto opcional que el usuario escriba para dar contexto.
    """
    b64_image = base64.standard_b64encode(image_bytes).decode("utf-8")

    user_text = "Analiza esta captura de pantalla y responde según las reglas."
    if extra_instruction.strip():
        user_text += f"\n\nContexto adicional del usuario: {extra_instruction.strip()}"

    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"inline_data": {"mime_type": "image/png", "data": b64_image}},
                    {"text": user_text},
                ],
            }
        ],
        "generationConfig": {
            "temperature": 1.0
        }
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT,
        data=data,
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Error de la API de Gemini ({e.code}): {error_body}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"No se pudo conectar con Gemini: {e.reason}") from e

    try:
        candidates = result["candidates"]
        candidate = candidates[0]
        
        # Detectar filtro de derechos de autor (RECITATION)
        if candidate.get("finishReason") == "RECITATION":
            return (
                "⚠️ Respuesta bloqueada por el filtro de derechos de autor (RECITATION).\n\n"
                "Para evitarlo:\n"
                "1. La IA ha sido configurada ahora con mayor temperatura y orden de parafrasear.\n"
                "2. Intenta capturar un área ligeramente distinta o más pequeña.\n"
                "3. Si es una pregunta de opción múltiple o examen, asegúrate de que no incluya logotipos o marcas de copyright de la plataforma."
            )
            
        parts = candidate["content"]["parts"]
        text = "\n".join(p.get("text", "") for p in parts).strip()
        return text or "(La IA no devolvió texto)"
    except (KeyError, IndexError):
        # Puede venir bloqueado por seguridad, cuota agotada, etc.
        return f"No se pudo interpretar la respuesta:\n{json.dumps(result, indent=2, ensure_ascii=False)}"
