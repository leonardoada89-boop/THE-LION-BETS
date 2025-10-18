import os
import re
from google import genai
from telegram import Bot, Update 
from telegram.constants import ParseMode

# -----------------------------------------------------------
# --- INICIALIZACIÓN DEL CLIENTE GEMINI ---
# -----------------------------------------------------------
client = None
try:
    # La clave debe estar configurada en las variables de entorno de Render
    API_KEY = os.getenv("GOOGLE_API_KEY") 
    
    if not API_KEY:
        # No se detiene la ejecución, pero no permitirá usar la IA
        print("ADVERTENCIA: La clave GOOGLE_API_KEY no se encontró. Los comandos de IA fallarán.")
        client = None
    else:
        client = genai.Client(api_key=API_KEY)
    
except Exception as e:
    print(f"Error al inicializar el cliente Gemini: {e}")
    client = None

# -----------------------------------------------------------
# --- DEFINICIÓN DE LOS PROMPTS DE ESTRATEGIA ---
# -----------------------------------------------------------

# Usamos raw strings (r"") y comillas triples para manejar el texto y evitar errores de secuencias de escape
PROMPT_SIMPLE = r"""
APUESTAS SIMPLES
Actúa como el mejor tipster profesional, estadístico experto y analista deportivo de alto rendimiento. Tu disciplina es impecable. El objetivo principal es la protección del bankroll y la consistencia a largo plazo sobre la ganancia inmediata. Priorizas la gestión del riesgo (valor) y el control emocional en cada recomendación.
Objetivo de la Salida: Generar un análisis de los tres (3) partidos más seguros para apostar en la fecha **{FECHA_OBJETIVO}**, basados estrictamente en datos históricos sólidos (últimos 5-10 partidos) y validaciones contextuales de alta seguridad. Si no hay partidos que cumplan los filtros, la respuesta será: "Mejor no apostar. Ningún partido cumple los criterios de seguridad profesional."

**FORMATO DE SALIDA ESTRICTO (Markdown V2):**

Debe empezar con un título y una tabla de resumen.
Usa **solo** los formatos de Markdown V2 de Telegram (por ejemplo, `\*bold\*`, `\_italic\_`, `\[link\]\(url\)`).

Ejemplo de salida:
# Análisis Profesional \- Apuestas Simples

|Partido|Hora \(UTC\)|Competición|Cuota Recomendada|
|:---:|:---:|:---:|:---:|
|Equipo A vs\. Equipo B|20:00|Liga|1\.80|
|...|...|...|...|

## Pick 1: Equipo A vs Equipo B

**Fecha/Hora:** 20/10/2025 20:00 UTC
**Análisis de Valor:** Alto \- Etiqueta \*VERDE\*
**Pronóstico Oficial:** Over 0\.5 Goles del Equipo A

### Fundamentos Estadísticos:
1\. Efectividad de Goles: Equipo A ha marcado en el 90% de sus últimos 10 partidos\.
2\. Rendimiento Local/Visitante: Equipo A es local y promedia 2\.5 Goles por partido en casa\.
3\. Validación de Seguridad: La cuota de 1\.80 compensa perfectamente el riesgo de la apuesta\.

### Criterios de Seguridad Aplicados:
* **Over 0\.5 Goles del Favorito \(Local/Visitante\):** Efectividad $\ge 90\%$ de haber marcado en sus últimos 5\-10 partidos de liga/torneo similar\.
* **Cuota Mínima/Máxima:** 1\.65 a 2\.10, valor real comprobado\.

---
(Repetir para Pick 2 y Pick 3)

"""

PROMPT_COMBI = r"""
APUESTAS COMBINADAS
Actúa como el mejor tipster profesional, estadístico experto y analista deportivo de alto rendimiento. Tu disciplina es impecable. El objetivo principal es la protección del bankroll y la consistencia a largo plazo sobre la ganancia inmediata. Priorizas la gestión del riesgo (valor) y el control emocional en cada recomendación.
Objetivo de la Salida: Generar una Combinada de Valor (Parlay) para la fecha **{FECHA_OBJETIVO}** compuesta por 2 o 3 mercados individuales que cumplan los criterios de máxima seguridad (Etiqueta VERDE) y cuya **Cuota Combinada Final se aproxime a {CUOTA_OBJETIVO}**. Si no es posible construir una combinada segura, la respuesta será: "Mejor no apostar. Ningún partido cumple los criterios de seguridad profesional."

**FORMATO DE SALIDA ESTRICTO (Markdown V2):**

Debe empezar con un título y una tabla de resumen\.
Usa **solo** los formatos de Markdown V2 de Telegram (por ejemplo, `\*bold\*`, `\_italic\_`, `\[link\]\(url\)`)\.

Ejemplo de salida:
# Combinada Profesional \- Parlay de Valor

|Partido|Pronóstico|Cuota Individual|
|:---:|:---:|:---:|
|Equipo X vs\. Equipo Y|Over 0\.5 Goles Local|1\.15|
|Equipo P vs\. Equipo Q|Doble Oportunidad \(1X\)|1\.20|

**Cuota Combinada Final Aproximada:** **{CUOTA\_OBJETIVO}**
**Análisis de Valor General:** Alto \- Etiqueta \*VERDE\*
**Fecha Objetivo:** {FECHA\_OBJETIVO}

### Criterios de Seguridad Aplicados en la Combinada:
* **Selección de Mercados:** Solo pronósticos de "Seguridad Absoluta" (ej\. Over 0\.5 Goles del Favorito, Doble Oportunidad 1X/X2 en partidos muy desequilibrados)\.
* **Over 0\.5 Goles del Favorito \(Local/Visitante\):** Efectividad $\ge 90\%\.$
* **Cuota Objetivo:** Máximo 1\.40 (para mantener la consistencia del Bankroll)\.

---
"""

# -----------------------------------------------------------
# --- MANEJADORES DE COMANDOS DE TELEGRAM (VERSIÓN MANUAL) ---
# -----------------------------------------------------------

# MODO DE PARSEO: Se usa MarkdownV2 para las respuestas de la IA.
# Pero HTML para los mensajes de instrucción iniciales (más fácil de escribir)

async def send_message(chat_id: int, text: str, bot: Bot, parse_mode=ParseMode.HTML):
    """Función auxiliar para enviar mensajes con manejo de errores de formato."""
    try:
        await bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)
    except Exception:
        # Si falla el formato, intenta texto plano
        await bot.send_message(chat_id=chat_id, text=text)

async def handle_start(update: Update, bot: Bot) -> None:
    """Maneja el comando /start."""
    user = update.effective_user
    instructions = (
        f"¡Hola, **{user.first_name}**! Soy THE LION BETS 🦁, tu analista experto en IA.\n\n"
        "**Mi disciplina es estricta (¡solo Apuestas VERDES!).**\n\n"
        "Para solicitar un análisis, usa el siguiente formato de comando:\n\n"
        "👉 `/apuesta [TIPO] [FECHA] [CUOTA]`\n\n"
        "**Ejemplos:**\n"
        "1.  **Apuestas Simples (Cuota 2.00):**\n"
        "    `/apuesta SIMPLE 20/10/2025 2.00`\n\n"
        "2.  **Apuestas Combinadas (Cuota 1.30 - Recomendado):**\n"
        "    `/apuesta COMBI 21/10/2025 1.30`\n\n"
        "Procesaré tu solicitud con la máxima rigurosidad estadística y de valor."
    )
    # Usamos HTML para que el mensaje de bienvenida se vea bien (bold y emojis)
    await send_message(update.effective_chat.id, instructions, bot, ParseMode.HTML)

async def handle_apuesta(update: Update, bot: Bot, args: list) -> None:
    """Maneja el comando /apuesta."""
    chat_id = update.effective_chat.id
    
    if not client:
        await send_message(chat_id, "❌ Error de configuración: La clave Gemini API no es válida o falta. No se puede procesar la solicitud.", bot)
        return

    if len(args) != 3:
        await send_message(chat_id, 
            "⚠️ **Formato incorrecto.**\n\nUsa: `/apuesta [TIPO] [FECHA] [CUOTA]`\nEj: `/apuesta SIMPLE 20/10/2025 2.00`", bot)
        return

    apuesta_tipo = args[0].upper()
    fecha_objetivo = args[1]
    cuota_objetivo = args[2]
    
    if apuesta_tipo == "SIMPLE":
        base_prompt = PROMPT_SIMPLE
    elif apuesta_tipo == "COMBI":
        base_prompt = PROMPT_COMBI
    else:
        await send_message(chat_id, f"Tipo de apuesta no reconocido: '{apuesta_tipo}'. Usa SIMPLE o COMBI.", bot)
        return

    prompt_final = base_prompt.format(
        FECHA_OBJETIVO=fecha_objetivo,
        CUOTA_OBJETIVO=cuota_objetivo
    )
    
    await send_message(chat_id, 
        f"⏳ **Analizando Apuesta {apuesta_tipo}** para el {fecha_objetivo} (Cuota ≈ {cuota_objetivo}).\nEste análisis riguroso puede tardar hasta 45 segundos...", bot)

    try:
        # La llamada a la IA de Gemini
        response = client.models.generate_content(
            model='gemini-2.5-pro',
            contents=prompt_final
        )
        
        # Enviamos con ParseMode.MARKDOWN_V2 para que los formatos de tabla y negrita/cursiva funcionen correctamente
        await send_message(chat_id, response.text, bot, parse_mode=ParseMode.MARKDOWN_V2)

    except Exception as e:
        error_msg = f"❌ **Error en la conexión o procesamiento de la IA.**\n\nDetalles del error: {e}"
        await send_message(chat_id, error_msg, bot)


async def handle_update(update: Update, bot: Bot) -> None:
    """Función principal que procesa cualquier actualización y redirige comandos."""
    if update.message and update.message.text:
        text = update.message.text.strip()
        
        # Manejo manual de comandos
        if text.lower().startswith('/start'):
            await handle_start(update, bot)
            
        elif text.lower().startswith('/apuesta'):
            # Divide el comando y los argumentos: /apuesta TIPO FECHA CUOTA
            parts = text.split()
            args = parts[1:] 
            await handle_apuesta(update, bot, args)
