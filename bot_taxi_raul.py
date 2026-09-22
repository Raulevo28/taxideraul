import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes, CommandHandler
import google.generativeai as genai
import os

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TU_USERNAME = "raulevo28"

logging.basicConfig(level=logging.INFO)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

SYSTEM_PROMPT = """Eres el asistente virtual de El Taxi de Raul, un servicio de taxi en Madrid. Eres amable, cercano y profesional. Hablas siempre en español.

Tu objetivo es recoger los datos del servicio:
1. Nombre del cliente
2. Origen del viaje
3. Destino del viaje
4. Fecha y hora
5. Número de personas

Servicios disponibles:
- Vehículo de 8 plazas
- Adaptado para PMR
- Viajes largos desde Madrid
- Aeropuerto, bodas, eventos, hospitales

Cuando tengas TODOS los datos escribe al final:
LEAD_COMPLETO: nombre=[nombre], origen=[origen], destino=[destino], fecha=[fecha], personas=[personas]"""

conversaciones = {}
raul_chat_id = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global raul_chat_id
    username = update.message.from_user.username
    if username == TU_USERNAME:
        raul_chat_id = update.message.chat_id
        await update.message.reply_text(f"✅ Bot activado. Tu ID es: {raul_chat_id}. Los leads te llegarán aquí.")
    else:
        await update.message.reply_text("👋 ¡Hola! Soy el asistente de El Taxi de Raul.\n\n🚐 Taxi desde Madrid · 8 plazas · Adaptado PMR\n\n¿En qué puedo ayudarte?")

async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global raul_chat_id
    user_id = update.message.chat_id
    username = update.message.from_user.username
    mensaje = update.message.text

    if username == TU_USERNAME:
        raul_chat_id = user_id
        await update.message.reply_text(f"✅ Tu ID guardado: {raul_chat_id}. Los leads te llegarán aquí.")
        return

    if user_id not in conversaciones:
        conversaciones[user_id] = []

    conversaciones[user_id].append({"role": "user", "parts": [mensaje]})

    try:
        chat = model.start_chat(history=conversaciones[user_id][:-1])
        respuesta = chat.send_message(SYSTEM_PROMPT + "\n\nCliente dice: " + mensaje)
        texto_respuesta = respuesta.text
    except Exception as e:
        await update.message.reply_text("Lo siento, ha habido un error. Contacta con Raul al 618 736 155.")
        return

    conversaciones[user_id].append({"role": "model", "parts": [texto_respuesta]})

    if "LEAD_COMPLETO:" in texto_respuesta:
        lead_info = texto_respuesta.split("LEAD_COMPLETO:")[1].strip().split("\n")[0]
        mensaje_cliente = texto_respuesta.split("LEAD_COMPLETO:")[0].strip()
        await update.message.reply_text(mensaje_cliente)
        if raul_chat_id:
            await context.bot.send_message(
                chat_id=raul_chat_id,
                text=f"🚨 NUEVO LEAD — El Taxi de Raul\n\n📋 {lead_info}\n\n💬 Usuario: @{username or 'sin username'}"
            )
    else:
        await update.message.reply_text(texto_respuesta)

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))
print("🚐 Bot arrancado...")
app.run_polling()
