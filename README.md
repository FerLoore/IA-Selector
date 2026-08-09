# IA Selector — asistente de pantalla estilo "Circle to Search"

App para Windows: un botón flotante que, al presionarlo, lee el contenido
de un área fija de tu pantalla (preguntas, código, texto en otro idioma,
etc.) usando Gemini y te muestra la respuesta.

## 1. Requisitos

- Windows 10 u 11.
- Python 3.10 o superior instalado. Descárgalo de https://www.python.org/downloads/
  (al instalar, marca la casilla **"Add python.exe to PATH"**).
- Una API key **gratuita** de Gemini: entra a
  https://aistudio.google.com/apikey con tu cuenta de Google, crea una key
  y cópiala. No pide tarjeta de crédito.

## 2. Instalación

Abre una terminal (PowerShell o CMD) dentro de esta carpeta y ejecuta:

```
pip install -r requirements.txt
```

## 3. Ejecutar la app

```
python main.py
```

La primera vez te pedirá que pegues tu API key de Gemini (queda guardada
en `config.json`, en esta misma carpeta — no la compartas).

## 4. Cómo usarla

1. Aparece un botón azul flotante "IA" en la pantalla. Arrástralo a donde
   quieras.
2. **Primer clic:** la pantalla se oscurece un poco — arrastra el mouse
   para marcar el área que quieres que la IA lea (como el rectángulo rojo
   del ejemplo). Al soltar, esa área queda marcada con un borde rojo fijo.
3. **Clics siguientes:** cada vez que presiones el botón, se captura lo
   que hay *en ese mismo cuadro* en ese momento y se envía a la IA. La
   respuesta aparece en una ventana emergente en unos segundos.
4. **Clic derecho** sobre el botón:
   - *Cambiar área* — vuelve a marcar otra zona de la pantalla.
   - *Cambiar API key* — si quieres reemplazar la key guardada.
   - *Salir* — cierra la app.

El marco rojo no bloquea clics: puedes seguir usando lo que está debajo
con normalidad.

## 5. Límites de la capa gratuita de Gemini

Gemini 2.5 Flash (el modelo que usa la app) tiene una cuota diaria
gratuita bastante generosa, pero limitada (cientos de solicitudes al día,
pocas por minuto). Si ves un error de "cuota agotada", espera un momento
o revisa tu panel en https://aistudio.google.com — ahí puedes ver tu
consumo exacto.

## 6. (Opcional) Convertirla en un .exe

Si quieres abrirla con doble clic sin usar la terminal:

```
pip install pyinstaller
pyinstaller --onefile --noconsole --name "IA-Selector" main.py
```

El ejecutable queda en la carpeta `dist/`. Cópialo junto con tu
`config.json` (o vuelve a pegar la API key la primera vez que lo abras).

## Estructura del proyecto

```
ai_selector/
├── main.py           # botón flotante y flujo principal
├── overlay.py         # selección de área + marco rojo fijo
├── ai_client.py       # llamada a la API de Gemini
├── result_window.py   # ventana que muestra la respuesta
├── win_utils.py        # hace el marco "click-through" en Windows
├── config.py           # guarda/lee la API key
└── requirements.txt
```
