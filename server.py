import os
import json
from flask import Flask, request, session, jsonify, redirect, url_for
import msal
import requests
from dotenv import load_dotenv
from flask_session import Session

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
TENANT_ID = os.getenv("TENANT_ID")
REDIRECT_URI = os.getenv("REDIRECT_URI", "https://helpdeskbot-production.up.railway.app/auth/microsoft/callback")
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = ["User.Read", "Mail.Read", "Mail.Send", "Calendars.ReadWrite"]
OUTLOOK_API_BASE = os.getenv("OUTLOOK_API_BASE", "https://graph.microsoft.com/v1.0")

# Настройки Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

# Инициализация Flask
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "supersecretkey")
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_PERMANENT"] = False
Session(app)

# Инициализация MSAL
msal_app = msal.ConfidentialClientApplication(
    CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET
)

@app.route("/login", methods=["GET"])
def login():
    user_id = session.get("user_id", "temp_user")
    return redirect(url_for("auth_microsoft", user_id=user_id))

# Авторизация через Microsoft
@app.route("/auth/microsoft")
def auth_microsoft():
    """Перенаправляет пользователя на страницу входа в Microsoft"""
    user_id = request.args.get("user_id")
    if not user_id:
        return "Ошибка: user_id не передан", 400

    session["user_id"] = user_id
    auth_url = msal_app.get_authorization_request_url(SCOPE, redirect_uri=REDIRECT_URI, state=user_id)
    return redirect(auth_url)

# Обработка ответа от Microsoft и отправка сообщения в Telegram
@app.route("/auth/microsoft/callback")
def auth_callback():
    """Получает токены и отправляет email пользователя в Telegram"""
    code = request.args.get("code")
    user_id = request.args.get("state")

    if not code or not user_id:
        return "Ошибка авторизации", 400

    token_result = msal_app.acquire_token_by_authorization_code(
        code, SCOPE, redirect_uri=REDIRECT_URI
    )

    if "access_token" not in token_result:
        return f"Ошибка: {token_result.get('error_description', 'Неизвестная ошибка')}", 400

    access_token = token_result["access_token"]

    # Запрос email пользователя
    headers = {"Authorization": f"Bearer {access_token}"}
    user_info = requests.get(f"{OUTLOOK_API_BASE}/me", headers=headers).json()
    user_email = user_info.get("mail", "")

    # Определяем роль пользователя
    if user_email.endswith("@astanait.edu.kz") and user_email.split("@")[0].isdigit():
        role = "студент"
    elif "@" in user_email and user_email.endswith("@astanait.edu.kz"):
        role = "преподаватель"
    else:
        role = "неопознанный пользователь"

    # Логируем user_id перед отправкой в Telegram
    print(f"Отправка сообщения в Telegram. user_id: {user_id}")

    # Отправка сообщения пользователю в Telegram
    message = f"✅ Добро пожаловать, {role}! Ваш email: {user_email}"
    response = requests.post(TELEGRAM_API_URL, data={"chat_id": user_id, "text": message})

    # Логируем ответ API Telegram
    print("Ответ Telegram API:", response.json())

    return "Вы успешно авторизовались!"

# Запуск сервера
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
