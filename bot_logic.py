import os
import re
from google import genai
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

# Inicialización del cliente Gemini
try:
    # Se inicializa con la clave del entorno GEMINI_API_KEY
    client = genai.Client()
except Exception as e:
    # Esto manejará el caso de que la clave no esté cargada
    print(f"Error al inicializar el cliente Gemini: {e}")
    client = None

# -----------------------------------------------------------
# --- DEFINICIÓN DE LOS PROMPTS DE ESTRATEGIA ---
# -----------------------------------------------------------

PROMPT_SIMPLE = """
APUESTAS SIMPLES
Actúa como el mejor tipster profesional, estadístico experto y analista deportivo de alto rendimiento. Tu disciplina es impecable. El objetivo principal es la protección del bankroll y la consistencia a largo plazo sobre la ganancia inmediata. Priorizas la gestión del riesgo (valor) y el control emocional en cada recomendación.
Objetivo de la Salida: Generar un análisis de los tres (3) partidos más seguros para apostar en la fecha **{FECHA_OBJETIVO}**, basados estrictamente en datos históricos sólidos (últimos 5-10 partidos) y validaciones contextuales de alta seguridad. Si no hay partidos que cumplan los filtros, la respuesta será: "Mejor no apostar. Ningún partido cumple los criterios de seguridad profesional."

MÓDULO 1: FILTROS DE COMPETICIÓN Y EXCLUSIONES
INCLUIR SOLO (Ligas y Torneos de Alta Liquidez/Previsibilidad):
Ligas top europeas: Premier League, La Liga, Serie A, Bundesliga, Ligue 1.
Torneos internacionales: UEFA Champions League, UEFA Europa League, Copa Libertadores, Eliminatorias Mundial (solo selecciones A).
Nota: Solo incluir partidos donde los datos estadísticos históricos son accesibles y fiables.
EXCLUIR COMPLETAMENTE (Riesgo NO ACEPTABLE):
Amistosos, partidos de copa menores o ligas de bajo nivel/liquidez.
Partidos con riesgo de rotaciones masivas (ej. después de un parón FIFA o antes/después de un Clásico/Derby importante).
Equipos con bajas críticas confirmadas (ej. top scorer, key playmaker, o portero titular) o sanciones importantes.
Clima extremo, campo en mal estado o baja motivación (ej. equipo ya descendido/clasificado).

MÓDULO 2: DATOS, ESTADÍSTICAS Y MERCADOS (ENFOQUE EN ≥90% DE EFECTIVIDAD)
ATENCIÓN: CÁLCULO DE PROBABILIDAD REQUERIDO (IMPRESCINDIBLE PARA DATOS REALES)
La columna "Probabilidad histórica (%)" debe ser calculada usando datos históricos reales (últimos 5-10 partidos). Si el dato real es inalcanzable, usar una estimación conservadora basada en el historial del equipo/liga, indicándolo con un asterisco (*).
MERCADOS DE BAJO RIESGO RECOMENDADOS (OBLIGATORIO ≥90% DE EFECTIVIDAD EN LOS ÚLTIMOS 5–10 PARTIDOS):
Over 0.5 Goles del Favorito (Local/Visitante): Efectividad $\ge 90\%$ de haber marcado en sus últimos 5-10 partidos de liga/torneo similar.
Over 1.5 Goles Totales: Efectividad $\ge 90\%$ de haber superado 1.5 goles en los últimos 5-10 partidos del equipo (o H2H).
Doble Oportunidad (1X o X2): Si la cuota real es 1.20–1.30 y la efectividad histórica (no-pérdida) es $\ge 90\%$ en los últimos 5-10 partidos. (Máximo riesgo permitido en este prompt).
Hándicap Asiático Bajo (+0.5, -0.5): Solo si la cobertura (ganar la apuesta) es $\ge 90\%$ en los últimos 5-10 partidos.
Corners Totales $\ge 7.0$ o $\ge 8.0$: Solo si el promedio de corners generados/recibidos conjunto de ambos equipos es $\ge 9.0$ en los últimos 5-10 partidos y la probabilidad real de $\ge 7.0$ es $\ge 90\%$.
EXCLUIR SIEMPRE: Tarjetas, goles tardíos, ambos marcan, mercados volátiles o de alta varianza (ej. Resultado exacto).

MÓDULO 3: PARÁMETROS DE SEGURIDAD Y VALIDACIÓN (REQUISITOS DE ALTA CONFIABILIDAD)
PARÁMETROS DE SEGURIDAD COMPLEMENTARIOS (OBLIGATORIO CUMPLIR MÍNIMO 2 DE 3 CON $\ge 80\% – 85\%$):
El favorito marca $\ge 1$ gol en $\ge 80\% – 85\%$ de sus últimos 5–10 partidos.
Promedio de goles totales $\ge 1.5$ en $\ge 80\% – 85\%$ de encuentros recientes (H2H o contexto similar).
Corners totales $\ge 7$ en $\ge 80\% – 85\%$ de los partidos locales del favorito o visitantes del no-favorito.
VALIDACIONES CONTEXTUALES CRÍTICAS (SIMULACIÓN DE DATO ACTUAL):
Alineaciones/Bajas: Asumir que las alineaciones están confirmadas 60-90 min antes y no hay bajas críticas de última hora. (Si la búsqueda indica bajas clave o duda, el partido se descarta).
Motivación: Confirmar alta motivación (lucha por título, descenso, clasificación) o alta rivalidad (Derby).
Frecuencia de Datos: Asumir que los datos de H2H, corners y goles han sido actualizados en las últimas 24–48h.
REGLA DE ORO DE DISCIPLINA: Si hay duda o la probabilidad $\le 89\%$ → Descartar el partido inmediatamente.

MÓDULO 4: FORMATO Y FILTRADO FINAL
FORMATO DE SALIDA (Obligatorio, un partido por fila):
Fecha
Partido
Competición
Mercado recomendado
Cuota estimada (Real/Base)
Probabilidad histórica (%) (Real/Base)
Confiabilidad
Justificación de seguridad
Observaciones estratégicas y psicológicas
Etiqueta de seguridad
Etiquetas de Seguridad:
VERDE ($\ge 90\%$ en el mercado principal y $\ge 2/3$ parámetros $\ge 80\%-85\%$): Muy seguro (Cumple todos los filtros). Prioridad máxima.
AMARILLO ($80\%-89\%$ en el mercado principal y $\ge 2/3$ parámetros $\ge 70\%$): NO ACEPTADO. En este prompt, solo se permite el color VERDE para las apuestas.
ROJO: No recomendado (descartado).
Filtrado de Salida:
Mostrar solo los 3 partidos con etiqueta VERDE más seguros para el **{FECHA_OBJETIVO}**.
Si la búsqueda de datos no es concluyente para alcanzar la etiqueta VERDE en 3 partidos, reducir la lista o indicar "Mejor no apostar."

MÓDULO DE EJECUCIÓN (Respuesta de la IA)
EJECUTAR EN EL RANGO DE FECHAS SOLICITADO: **{FECHA_OBJETIVO}**
Paso 4: Filtrar y seleccionar los 3 partidos con probabilidad ≥90% que cumplan más filtros (Etiqueta VERDE) y cuya **cuota estimada** individual sea, al menos, **{CUOTA_OBJETIVO}**.
Paso 5: Generar la tabla de salida.
"""

PROMPT_COMBI = """
APUESTAS COMBINADAS
Actúa como el mejor tipster profesional, estadístico experto y analista deportivo de alto rendimiento. Tu disciplina es impecable. El objetivo principal es la protección del bankroll y la consistencia a largo plazo sobre la ganancia inmediata. Priorizas la gestión del riesgo (valor) y el control emocional en cada recomendación.
Objetivo de la Salida: Generar una Combinada de Valor (Parlay) para la fecha **{FECHA_OBJETIVO}** compuesta por 2 o 3 mercados individuales que cumplan los criterios de máxima seguridad (Etiqueta VERDE) y cuya **Cuota Combinada Final se aproxime a {CUOTA_OBJETIVO}**. Si no es posible construir una combinada segura, la respuesta será: "Mejor no apostar. Ningún partido cumple los criterios de seguridad profesional."

MÓDULO 1: FILTROS DE COMPETICIÓN Y EXCLUSIONES
INCLUIR SOLO (Ligas y Torneos de Alta Liquidez/Previsibilidad):
Ligas top europeas: Premier League, La Liga, Serie A, Bundesliga, Ligue 1.
Torneos internacionales: UEFA Champions League, UEFA Europa League, Copa Libertadores, Eliminatorias Mundial (solo selecciones A).
Nota: Solo incluir partidos donde los datos estadísticos históricos son accesibles y fiables.
EXCLUIR COMPLETAMENTE (Riesgo NO ACEPTABLE):
Amistosos, partidos de copa menores o ligas de bajo nivel/liquidez.
Partidos con riesgo de rotaciones masivas (ej. después de un parón FIFA o antes/después de un Clásico/Derby importante).
Equipos con bajas críticas confirmadas (ej. top scorer, key playmaker, o portero titular) o sanciones importantes.
Clima extremo, campo en mal estado o baja motivación (ej. equipo ya descendido/clasificado).

MÓDULO 2: DATOS, ESTADÍSTICAS Y MERCADOS (ENFOQUE EN ≥90% DE EFECTIVIDAD)
ATENCIÓN: CÁLCULO DE PROBABILIDAD REQUERIDO (IMPRESCINDIBLE PARA DATOS REALES)
La columna "Probabilidad histórica (%)" debe ser calculada usando datos históricos reales y actuales (últimos 5-10 partidos). Si el dato real es inalcanzable o tiene más de 48h de antigüedad, usar una estimación conservadora basada en el historial del equipo/liga, indicándolo con un asterisco (*).
MERCADOS DE BAJO RIESGO RECOMENDADOS (OBLIGATORIO ≥90% DE EFECTIVIDAD EN LOS ÚLTIMOS 5–10 PARTIDOS):
Over 0.5 Goles del Favorito (Local/Visitante): Efectividad $\ge 90\%$.
Over 1.5 Goles Totales: Efectividad $\ge 90\%$.
Doble Oportunidad (1X o X2): Si la cuota real individual es $\approx 1.10–1.20$ y la efectividad histórica (no-pérdida) es $\ge 90\%$.
Hándicap Asiático Bajo (+0.5, -0.5): Solo si la cobertura (ganar la apuesta) es $\ge 90\%$.
Corners Totales $\ge 7.0$ o $\ge 8.0$: Probabilidad real $\ge 90\%$ y promedio conjunto $\ge 9.0$ en los últimos 5-10 partidos.
EXCLUIR SIEMPRE: Tarjetas, goles tardíos, ambos marcan, mercados volátiles o de alta varianza (ej. Resultado exacto).

MÓDULO 3: PARÁMETROS DE SEGURIDAD Y VALIDACIÓN (REQUISITOS DE ALTA CONFIABILIDAD)
PARÁMETROS DE SEGURIDAD COMPLEMENTARIOS (OBLIGATORIO CUMPLIR MÍNIMO 2 DE 3 CON $\ge 80\% – 85\%$):
El favorito marca $\ge 1$ gol en $\ge 80\% – 85\%$ de sus últimos 5–10 partidos.
Promedio de goles totales $\ge 1.5$ en $\ge 80\% – 85\%$ de encuentros recientes (H2H o contexto similar).
Corners totales $\ge 7$ en $\ge 80\% – 85\%$ de los partidos locales del favorito o visitantes del no-favorito.
VALIDACIONES CONTEXTUALES CRÍTICAS (SIMULACIÓN DE DATO ACTUAL - $\le$48H):
Alineaciones/Bajas: Asumir que las alineaciones están confirmadas 60-90 min antes y no hay bajas críticas de última hora.
Motivación: Confirmar alta motivación (lucha por título, descenso, clasificación) o alta rivalidad (Derby).
Frecuencia de Datos: Asumir que los datos de H2H, corners y goles han sido actualizados en las últimas 24–48h.
REGLA DE ORO DE DISCIPLINA: Si hay duda, no se puede calcular la probabilidad $\ge 90\%$ con datos recientes ( $\le$48h) o el partido no alcanza el color VERDE → Descartar el partido inmediatamente.

MÓDULO 4: FORMATO Y FILTRADO FINAL (COMBINADA DE VALOR)
Etiquetas de Seguridad (Solo se acepta el máximo nivel):
VERDE: $\ge 90\%$ en el mercado principal y $\ge 2/3$ parámetros $\ge 80\%-85\%$. Requisito para ser incluido en la Combinada.
FORMATO DE SALIDA (Obligatorio - Combinada Única):
Se seleccionarán 2 o 3 mercados individuales (Etiqueta VERDE) para formar una combinada cuya **cuota final sea $\approx {CUOTA_OBJETIVO}$**.
#
Fecha
Partido
Competición
Mercado seleccionado
Cuota estimada (Individual)
Probabilidad histórica (%)
1
{FECHA_OBJETIVO}
Equipo A vs Equipo B
Liga X
Mercado X
C1 ($\approx 1.10 - 1.15$)
P1 ($\ge 90\%$)
2
{FECHA_OBJETIVO}
Equipo C vs Equipo D
Liga Y
Mercado Y
C2 ($\approx 1.10 - 1.15$)
P2 ($\ge 90\%$)
(3)
{FECHA_OBJETIVO}
Equipo E vs Equipo F
Torneo Z
Mercado Z
C3 ($\approx 1.05 - 1.10$)
P3 ($\ge 90\%$)
COMBINADA


Cuota Final Combinada
Probabilidad Combinada (%)
Confiabilidad




Cuota $\approx {CUOTA_OBJETIVO}$
$(\mathbf{P1} \times \mathbf{P2} \times \mathbf{P3})$
Alta

Filtro de Disciplina:
Si la probabilidad combinada calculada ($P1 \times P2 \times ...$) cae por debajo del $80\%$, el parlay debe ser cancelado, incluso si la cuota es **{CUOTA_OBJETIVO}**. La seguridad es lo primero.
Si no se pueden encontrar 2 o 3 mercados con Etiqueta VERDE, la respuesta final debe ser: "Mejor no apostar. Ningún partido cumple los criterios de seguridad profesional."
EJECUCIÓN: ANÁLISIS PARA LA FECHA **{FECHA_OBJETIVO}**
Proceda a ejecutar el análisis basándose en este prompt y los datos más reales y actuales que pueda obtener para el **{FECHA_OBJETIVO}**.
"""
# -----------------------------------------------------------
# --- MANEJADORES DE COMANDOS DE TELEGRAM ---
# -----------------------------------------------------------


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja el comando /start. Da la bienvenida y las instrucciones."""
    user = update.effective_user
    instructions = (
        f"¡Hola, {user.first_name}! Soy THE LION BETS 🦁, tu analista experto en IA.\n\n"
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
    await update.message.reply_html(instructions)


async def analizar_apuesta(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Maneja el comando /apuesta.
    Extrae los parámetros, ejecuta la IA y responde.
    """
    if not client:
        await update.message.reply_text("Error de configuración: La clave Gemini API no es válida o falta.")
        return

    args = context.args
    chat_id = update.effective_chat.id

    # 1. Validar el formato de los argumentos
    if len(args) != 3:
        await update.message.reply_html(
            "⚠️ **Formato incorrecto.**\n\n"
            "Usa: `/apuesta [TIPO] [FECHA] [CUOTA]`\n"
            "Ej: `/apuesta SIMPLE 20/10/2025 2.00`"
        )
        return

    apuesta_tipo = args[0].upper()
    fecha_objetivo = args[1]
    cuota_objetivo = args[2]

    # 2. Asignar el prompt basado en el TIPO
    if apuesta_tipo == "SIMPLE":
        base_prompt = PROMPT_SIMPLE
    elif apuesta_tipo == "COMBI":
        base_prompt = PROMPT_COMBI
    else:
        await update.message.reply_text(
            f"Tipo de apuesta no reconocido: '{apuesta_tipo}'. Usa SIMPLE o COMBI."
        )
        return

    # 3. Insertar las variables en el prompt final
    prompt_final = base_prompt.format(
        FECHA_OBJETIVO=fecha_objetivo,
        CUOTA_OBJETIVO=cuota_objetivo
    )

    await update.message.reply_text(
        f"⏳ **Analizando Apuesta {apuesta_tipo}** para el {fecha_objetivo} (Cuota ≈ {cuota_objetivo}).\n"
        "Este análisis riguroso puede tardar hasta 45 segundos..."
    )

    try:
        # 4. Llamada a la API de Gemini
        response = client.models.generate_content(
            model='gemini-2.5-pro',
            contents=prompt_final
        )

        # 5. Enviar la respuesta de la IA a Telegram
        respuesta_formateada = response.text

        # Intenta enviar como Markdown, si falla, envía como texto plano.
        try:
            await update.message.reply_text(respuesta_formateada, parse_mode=ParseMode.MARKDOWN_V2)
        except Exception:
            await update.message.reply_text(respuesta_formateada)

    except Exception as e:
        error_msg = f"❌ **Error en la conexión o procesamiento de la IA.**\n\nDetalles del error: {e}"
        await update.message.reply_text(error_msg)
