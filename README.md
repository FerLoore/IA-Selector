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
3. **Primer Uso / Selección**: La primera vez que haces clic en el botón flotante o presionas el atajo de teclado, la pantalla se oscurecerá un poco. Arrastra el mouse para marcar el área que quieres que la IA lea. Al soltar, esa zona quedará definida. El marco es **completamente invisible** por defecto (incluso si pasas el mouse por encima) para máxima discreción.
4. **Visibilidad del Marco a Pedido**: Puedes presionar **`ctrl+shift+f`** o elegir *"Mostrar marco / Ocultar marco"* en el menú del botón flotante para hacerlo visible cuando necesites ver dónde está ubicado, y volverlo a ocultar con la misma tecla.
5. **Consultas Siguientes**: Cada vez que hagas clic en el botón o uses el atajo de teclado (**`ctrl+shift+x`**), se capturará lo que esté debajo del marco en ese momento y se enviará a la IA. La ventana de respuestas aparecerá en segundos.
6. **Ventana de Respuestas Premium y Discreta**:
   - **Opacidad Adaptativa**: La ventana tiene opacidad adaptativa. Es muy translúcida (25% opacidad) cuando no interactúas con ella y se vuelve legible (95% opacidad) al pasar el mouse.
   - **Colapsable**: Puedes colapsar la respuesta presionando el botón `▲` / `▼` en la barra de título para ocultar el contenido de inmediato en una pequeña barra de 28px.
   - **Copiar al Portapapeles**: Incluye un botón rápido de "Copiar" que copia el texto de respuesta al portapapeles.
   - **Contador de Cuota y Tokens**: Botón interactivo `⚡` en la barra que muestra los tokens consumidos y las consultas restantes del día.
7. **Clic derecho** sobre el botón flotante:
   - *Mostrar marco / Ocultar marco* — Alterna la visibilidad del marco fijo (también con `ctrl+shift+f`).
   - *Ver cuota y tokens* — Muestra el consumo detallado de tokens y consultas restantes del día.
   - *Cambiar área* — Vuelve a definir otra zona de la pantalla.
   - *Cambiar API key* — Reemplaza la API key individual guardada.
   - *Directorio archivo API keys (.txt)* — Configura la ruta de un archivo `.txt` (o directorio que lo contenga) con múltiples API keys de Gemini (una por línea). Si una clave agota su cuota de tokens, la aplicación rotará automáticamente a la siguiente. Si dejas el campo vacío, volverá a usar la API key individual.
   - *Salir* — Cierra la aplicación por completo.

El marco blanco no bloquea clics: puedes seguir usando lo que está debajo de la zona de captura con total normalidad.

## 5. Límites de la capa gratuita de Gemini

La aplicación utiliza el modelo **Gemini 3.5 Flash**, el cual cuenta con una cuota gratuita completa (de hasta 1,500 solicitudes por día). Si alcanzas el límite de tasa por minuto, espera unos segundos antes de realizar la siguiente consulta.

## 6. (Opcional) Compilar y generar el archivo .exe

Si quieres generar el ejecutable para abrir la aplicación directamente con doble clic sin necesidad de abrir una consola o terminal:

### Paso 1: Instalar PyInstaller (si aún no lo tienes)
```powershell
pip install pyinstaller
```

### Paso 2: Compilar el ejecutable usando el archivo .spec (Recomendado)
El proyecto ya cuenta con el archivo de configuración `IA-Selector.spec` preparado con todas las opciones optimizadas (modo sin consola negra y assets integrados):

```powershell
python -m PyInstaller --clean IA-Selector.spec
```
*(O si tienes el comando directo disponible en tu PATH: `pyinstaller --clean IA-Selector.spec`)*

### Paso 3: Ubicación y ejecución del .exe
* El archivo compilado quedará listo en la carpeta `dist/`:
  ```text
  dist/IA-Selector.exe
  ```
* Asegúrate de que el archivo `config.json` esté en esa misma carpeta (o déjalo que la app lo genere automáticamente la primera vez).
* Puedes ejecutarlo directamente desde PowerShell con:
  ```powershell
  .\dist\IA-Selector.exe
  ```
  O haciendo doble clic sobre **`IA-Selector.exe`** en el Explorador de Archivos de Windows.

---

### Alternativa: Generar el .exe desde cero por comando
Si alguna vez no tienes el archivo `IA-Selector.spec`, puedes compilarlo directamente con este comando:
```powershell
pyinstaller --noconsole --onefile --clean --add-data "logoTraslucido.png;." --name "IA-Selector" main.py
```

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
