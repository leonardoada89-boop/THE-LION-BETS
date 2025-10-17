import os
import re
import logging
from contextlib import asynccontextmanager
from http import HTTPStatus
from fastapi import FastAPI, Request, Response

# Librerías de Telegram
from telegram import Update
from telegram.ext import Application, CommandHandler

# Módulo de Lógica de Negocio
from bot_logic import start, analizar_apuesta

# --- CONFIGURACIÓN Y VARIABLES DE ENTORNO ---
# NOTA: La clave de Gemini se busca ahora como GOOGLE_API_KEY en bot_logic.py
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
# La línea GEMINI_API_KEY ya no está aquí.

# AHORA SOLO VERIFICAMOS LA CLAVE DE TELEGRAM (LA DE GEMINI SE VERIFICA EN bot_logic.py)
if not TELEGRAM_TOKEN:
    raise ValueError("Falta la variable de entorno TELEGRAM_TOKEN.")

# Configuración del logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Inicialización de la Aplicación de Telegram
application = (
    Application.builder()
    .token(TELEGRAM_TOKEN)
    .build()
)

# Añadir los manejadores de comandos
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("apuesta", analizar_apuesta))


# --- SERVIDOR WEBHOOK (FastAPI) ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Función de 'ciclo de vida' que configura el Webhook en Telegram al inicio.
    """
    logging.info("Iniciando aplicación y configurando Webhook...")
    
    # 1. Obtener la URL pública del servidor Render.com
    WEBHOOK_URL = os.getenv("RENDER_EXTERNAL_URL") 
    
    if WEBHOOK_URL:
        # 2. Establecer el Webhook para que Telegram sepa dónde enviar los mensajes
        # Usamos el path "/telegram" para la URL del Webhook
        await application.bot.set_webhook(f"{WEBHOOK_URL}/telegram")
        logging.info(f"Webhook configurado en: {WEBHOOK_URL}/telegram")
    else:
        logging.error("No se encontró RENDER_EXTERNAL_URL. El Webhook no se configuró.")
        
    async with application:
        await application.start()
        yield # El servidor se mantiene corriendo
        await application.stop()

# Creación de la instancia de FastAPI
app = FastAPI(lifespan=lifespan)

@app.get("/", include_in_schema=False)
async def health():
    """Endpoint de salud para que Render sepa que el servidor está vivo."""
    return Response(content="Bot Activo (THE LION BETS)", status_code=HTTPStatus.OK)

@app.post("/telegram")
async def telegram_webhook(request: Request):
    """
    Endpoint principal que recibe todas las actualizaciones (mensajes, etc.) de Telegram.
    """
    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        
        # Procesar la actualización con la aplicación de Telegram
        await application.process_update(update)
        
        return Response(status_code=HTTPStatus.OK)
    
    except Exception as e:
        logging.error(f"Error procesando el Webhook: {e}")
        return Response(status_code=HTTPStatus.INTERNAL_SERVER_ERROR)

