import os
import logging
import requests
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Загружаем токен
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEB_APP_URL = "https://helpdeskbot-production.up.railway.app"  # Обновленный URL Railway

# Проверка наличия токена
if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не найден в .env!")

FLASK_URL = "https://helpdeskbot-production.up.railway.app"  # Обновленный URL Railway

# Логирование
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Просит пользователя авторизоваться."""
    await update.message.reply_text("Пожалуйста, авторизуйтесь. Введите /login.")

# Авторизация через Microsoft
async def login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет кнопку для входа через Web App."""
    user_id = update.message.from_user.id
    login_url = f"{WEB_APP_URL}/login?user_id={user_id}"

    keyboard = [[InlineKeyboardButton("🔑 Войти через Microsoft", url=login_url)]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("Для входа используйте кнопку ниже:", reply_markup=reply_markup)

# Проверка email и приветствие
async def authenticate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Определяет роль пользователя по email и отправляет приветствие."""
    user_email = update.message.text.strip()

    if user_email.endswith("@astanait.edu.kz") and user_email.split("@")[0].isdigit():
        role = "студент"
    elif "@" in user_email and user_email.endswith("@astanait.edu.kz"):
        role = "преподаватель"
    else:
        await update.message.reply_text("Некорректный email. Попробуйте снова.")
        return

    await update.message.reply_text(f"Добро пожаловать, {role}! Ваш email: {user_email}")

# Получение писем
async def get_mails(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Получает последние письма и отправляет их в Telegram."""
    try:
        response = requests.get(f"{FLASK_URL}/mails")
        if response.status_code != 200:
            await update.message.reply_text("Ошибка при получении писем.")
            return

        emails = response.json()
        if not emails:
            await update.message.reply_text("У вас нет новых писем.")
            return

        result = "*Последние письма:*\n\n"
        for email in emails:
            result += f"✉️ *От:* {email['from']}\n📌 *Тема:* {email['subject']}\n\n"

        await update.message.reply_text(result, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {str(e)}")

# Запуск бота
def main():
    application = Application.builder().token(TOKEN).build()

    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("login", login))
    application.add_handler(CommandHandler("mails", get_mails))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, authenticate))

    # Запуск
    application.run_polling()

if __name__ == "__main__":
    main()
