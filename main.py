import os
import logging
from contextlib import asynccontextmanager
from http import HTTPStatus
from fastapi import FastAPI, Request, Response

# Solo importamos Bot y Update (sin telegram.ext)
from telegram import Bot, Update

# Módulo de Lógica de Negocio
from bot_logic import handle_update 

# --- CONFIGURACIÓN Y VARIABLES DE ENTORNO ---
# El token debe estar configurado en las variables de entorno de Render
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TELEGRAM_TOKEN:
    # Esto forzará un error visible si el token falta en Render
    raise ValueError("Falta la variable de entorno TELEGRAM_TOKEN.")

# Configuración del logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Inicialización del Bot (NO usamos Application.builder() para evitar el error)
bot = Bot(token=TELEGRAM_TOKEN) 

# --- GESTIÓN DEL LIFESPAN (WEBHOOK SETUP) ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Configura el Webhook al iniciar el servicio en Render."""
    logging.info("Iniciando aplicación y configurando Webhook...")
    
    # Render proporciona esta URL automáticamente
    WEBHOOK_URL = os.getenv("RENDER_EXTERNAL_URL") 
    
    if WEBHOOK_URL:
        # Establecer el Webhook usando el objeto Bot
        await bot.set_webhook(f"{WEBHOOK_URL}/telegram")
        logging.info(f"Webhook configurado en: {WEBHOOK_URL}/telegram")
    else:
        logging.error("No se encontró RENDER_EXTERNAL_URL. El Webhook no se configuró.")
        
    yield # El servidor se mantiene corriendo
    
    # Opcional: Limpieza al apagar
    logging.info("Deteniendo el servicio...")

# Creación de la instancia de FastAPI
app = FastAPI(lifespan=lifespan)

# --- ENDPOINTS ---

@app.get("/", include_in_schema=False)
async def health():
    """Endpoint de salud para que Render sepa que el servidor está vivo."""
    return Response(content="Bot Activo (THE LION BETS)", status_code=HTTPStatus.OK)

@app.post("/telegram")
async def telegram_webhook(request: Request):
    """
    Endpoint que recibe las actualizaciones de Telegram y las pasa a la lógica.
    """
    try:
        data = await request.json()
        
        # Convertir JSON a objeto Update
        update = Update.de_json(data, bot)
        
        # Procesar la actualización con la lógica de negocio
        await handle_update(update, bot) 
        
        return Response(status_code=HTTPStatus.OK)
    
    except Exception as e:
        logging.error(f"Error procesando el Webhook: {e}")
        # Retornamos 200 OK a Telegram para evitar que siga reintentando
        return Response(status_code=HTTPStatus.OK)
