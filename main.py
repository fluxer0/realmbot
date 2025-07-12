import time
from mcstatus import JavaServer
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = "8082438304:AAEdDN2AClSQJweFSZsQfgFYu4glU4q0AxU" # Токен вашего бота
SERVER_ADDRESS = "de1.the-ae.ovh:25517"  # Адрес вашего сервера
SERVER_NAME = "Realm"      # Произвольное название
ADMIN_CHAT_ID = 1607290620                # Для уведомлений

last_request = {}
server_cache = {"timestamp": 0, "status": None}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        f"🛠️ Бот для мониторинга {SERVER_NAME}\n\n"
        "Команда /online - статус сервера"
    )

async def get_server_status() -> dict:
    """Получение статуса сервера с кэшированием и логированием ошибок"""
    now = time.time()
    if server_cache["timestamp"] > now - 5 and server_cache["status"] is not None:
        return server_cache["status"]
    try:
        server = JavaServer.lookup(SERVER_ADDRESS)
        status = await server.async_status()
        print(f"status.players: {status.players}")
        print(f"status.players.sample: {getattr(status.players, 'sample', None)}")
        # Попытка получить игроков через async_query, если sample пустой
        if getattr(status.players, 'sample', None):
            players = [p.name for p in status.players.sample[:12]]
        else:
            try:
                query = await server.async_query()
                print(f"query.players.names: {getattr(query.players, 'names', None)}")
                players = query.players.names[:12] if getattr(query.players, 'names', None) else []
            except Exception as qe:
                print(f"Ошибка получения игроков через query: {qe}")
                players = []
        result = {
            "online": True,
            "count": status.players.online,
            "max": status.players.max,
            "players": players,
            "version": status.version.name.split()[0]
        }
        server_cache["timestamp"] = now
        server_cache["status"] = result
        return result
    except Exception as e:
        print(f"Ошибка получения статуса сервера: {e}")
        result = {"online": False}
        server_cache["timestamp"] = now
        server_cache["status"] = result
        return result

async def check_online(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = getattr(update.effective_user, 'id', None)
    now = time.time()
    if user_id is None or not hasattr(update, 'message') or update.message is None:
        return
    if last_request.get(user_id, 0) > now - 5:
        await update.message.reply_text("♻ Запрос раз в 5 сек.")
        return
    last_request[user_id] = now
    try:
        status = await get_server_status()
        if status["online"]:
            message = (
                f"🟢 {SERVER_NAME}\n"
                f"👥 {status['count']} игроков\n"
            )
            if status["players"]:
                message += f"👤 Онлайн: {', '.join(status['players'])}"
            else:
                message += "🔍 Список игроков пуст"
        else:
            message = f"🔴 {SERVER_NAME} кажется упал...??"
        await update.message.reply_text(message)
    except Exception as e:
        print(f"Ошибка в check_online: {e}")
        await update.message.reply_text("⛔ Ошибка запроса")

import asyncio

async def notify_admin(app: Application) -> None:
    try:
        await app.bot.send_message(chat_id=ADMIN_CHAT_ID, text="🟢 Бот запущен")
    except Exception as e:
        print(f"Ошибка отправки сообщения в админ-чат: {e}")

def run_bot() -> None:
    try:
        app = Application.builder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("online", check_online))

        async def post_init(application):
            await notify_admin(application)

        app.post_init = post_init
        app.run_polling()
    except Exception as e:
        print(f"Ошибка запуска бота: {e}")

if __name__ == "__main__":
    print("🟢 Бот запущен")
    run_bot()
