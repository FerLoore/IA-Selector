# IA Selector — asistente de pantalla estilo "Circle to Search"

App para Windows: un botón flotante y atajo de teclado global que, al ejecutarse, lee el contenido de un área fija de tu pantalla (preguntas, código, texto en otro idioma, etc.) usando Gemini y te muestra la respuesta de forma extremadamente discreta.

## 1. Requisitos

- Windows 10 u 11.
- Python 3.10 o superior instalado. Descárgalo de https://www.python.org/downloads/
  (al instalar, marca la casilla **"Add python.exe to PATH"**).
- Una API key **gratuita** de Gemini: entra a
  https://aistudio.google.com/apikey con tu cuenta de Google, crea una key
  y cópiala. No pide tarjeta de crédito.

## 2. Instalación

Abre una terminal (PowerShell o CMD) dentro de esta carpeta y ejecuta:

```powershell
pip install -r requirements.txt
```

## 3. Ejecutar la app

```powershell
python main.py
```

La primera vez te pedirá que pegues tu API key de Gemini (queda guardada en `config.json` en esta misma carpeta — no la compartas).

## 4. Cómo usarla

1. **Botón Flotante**: Aparece un logotipo translúcido flotante en la pantalla. Puedes arrastrarlo libremente a donde quieras. Se vuelve más visible (95% opacidad) al pasar el mouse por encima y vuelve a ser discreto (35% opacidad) cuando lo retiras.
2. **Atajo de Teclado Global**: Puedes presionar el atajo **`ctrl+shift+x`** (atajo predeterminado) en cualquier momento para capturar y analizar la región seleccionada al instante, sin necesidad de hacer clic sobre la esfera flotante.
3. **Primer Uso / Selección**: La primera vez que haces clic en el botón flotante o presionas el atajo de teclado, la pantalla se oscurecerá un poco. Arrastra el mouse para marcar el área que quieres que la IA lea. Al soltar, esa zona quedará definida por un marco blanco sutil que solo se vuelve visible cuando el mouse está cerca.
4. **Consultas Siguientes**: Cada vez que hagas clic en el botón o uses el atajo de teclado, se capturará lo que esté debajo del marco en ese momento y se enviará a la IA. La ventana de respuestas aparecerá en segundos.
5. **Ventana de Respuestas Premium y Discreta**:
   - **Opacidad Adaptativa**: La ventana tiene opacidad adaptativa. Es muy translúcida (25% opacidad) cuando no interactúas con ella y se vuelve legible (95% opacidad) al pasar el mouse.
   - **Colapsable**: Puedes colapsar la respuesta presionando el botón `▲` / `▼` en la barra de título para ocultar el contenido de inmediato en una pequeña barra de 28px.
   - **Copiar al Portapapeles**: Incluye un botón rápido de "Copiar" que copia el texto de respuesta al portapapeles.
   - **Reutilización**: Al hacer una nueva consulta, la ventana de respuesta anterior y el brillo verde en pantalla se cerrarán automáticamente.
6. **Brillo en Pantalla (Detección de Opción Múltiple)**: Si la captura contiene una pregunta o encuesta de opción múltiple, la IA calculará la posición de la opción correcta y el sistema dibujará un brillo translúcido verde de forma temporal directamente sobre la respuesta correcta en la pantalla.
7. **Clic derecho** sobre el botón flotante:
   - *Cambiar área* — Vuelve a definir otra zona de la pantalla.
   - *Cambiar atajo de teclado* — Define una combinación de teclas personalizada global (ej. `ctrl+shift+s`, `f9`, etc.) de forma interactiva.
   - *Cambiar API key* — Reemplaza la API key guardada.
   - *Salir* — Cierra la aplicación por completo.

El marco blanco no bloquea clics: puedes seguir usando lo que está debajo de la zona de captura con total normalidad.

## 5. Límites de la capa gratuita de Gemini

La aplicación utiliza el modelo **Gemini 3.5 Flash**, el cual cuenta con una cuota gratuita completa (de hasta 1,500 solicitudes por día). Si alcanzas el límite de tasa por minuto, espera unos segundos antes de realizar la siguiente consulta.

## 6. (Opcional) Convertirla en un .exe

Si quieres abrirla con doble clic sin usar la terminal:

```powershell
pyinstaller --clean IA-Selector.spec
python -m PyInstaller --clean IA-Selector.spec
```

El ejecutable queda en la carpeta `dist/`. Cópialo junto con tu `config.json` y `logoTraslucido.png` en el mismo directorio.

## Estructura del proyecto

```text
ai_selector/
├── main.py             # Botón flotante, eventos globales y flujo principal
├── overlay.py           # Selección de área, marco blanco fijo y brillo de respuesta
├── ai_client.py         # Llamada a la API de Gemini (con salidas en formato JSON)
├── result_window.py     # Ventana discreta y premium que muestra la respuesta
├── win_utils.py         # Utilidades de Windows para hacer las ventanas click-through
├── config.py             # Carga y guarda la API key y el atajo de teclado
├── logoTraslucido.png   # Logotipo translúcido oficial de la aplicación
└── requirements.txt     # Dependencias de Python (Pillow, keyboard)
```
