"""
Mosling Semantic Filter Bot — Python версия
Запускается локально или на сервере по расписанию (cron / Task Scheduler)

Зависимости: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client requests
"""

import os
import re
import json
import base64
import pickle
import requests
from pathlib import Path
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# ===== НАСТРОЙКИ =====

GROQ_API_KEY = "YOUR_GROQ_API_KEY"    # console.groq.com
TG_BOT_TOKEN = "YOUR_TG_BOT_TOKEN"    # от @BotFather
TG_CHAT_ID   = "YOUR_TG_CHAT_ID"      # от @userinfobot
SENDER       = "mosling@googlegroups.com"

# Файл для хранения уже обработанных ID писем
PROCESSED_FILE = "processed_ids.json"

# Файл с OAuth2 credentials от Google (скачать из Google Cloud Console)
CREDENTIALS_FILE = "credentials.json"

INTERESTS = """
Мои научные интересы: анализ тональности, сентимент-анализ, динамический сентимент-анализ, 
динамический анализ тональности, эмоции в языке, аффективная лингвистика, 
субъективность в тексте, мнения и оценки в языке, эмоциональная окраска текста.

Смежные области, которые меня интересуют: прагматика, дискурс-анализ, 
корпусная лингвистика, обработка естественного языка (NLP), 
конфликтология текста, риторика, аргументация.
"""

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


# ===== АВТОРИЗАЦИЯ GMAIL =====

def get_gmail_service():
    creds = None
    token_file = "token.pickle"

    if Path(token_file).exists():
        with open(token_file, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_file, "wb") as f:
            pickle.dump(creds, f)

    return build("gmail", "v1", credentials=creds)


# ===== ЗАГРУЗКА И СОХРАНЕНИЕ ОБРАБОТАННЫХ ID =====

def load_processed_ids():
    if Path(PROCESSED_FILE).exists():
        with open(PROCESSED_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_processed_ids(ids):
    with open(PROCESSED_FILE, "w") as f:
        json.dump(list(ids), f)


# ===== ПОЛУЧЕНИЕ ПИСЕМ ИЗ GMAIL =====

def get_new_messages(service, processed_ids):
    query = f"from:{SENDER}"
    result = service.users().messages().list(userId="me", q=query).execute()
    messages = result.get("messages", [])

    new_messages = []
    for msg in messages:
        if msg["id"] not in processed_ids:
            full = service.users().messages().get(
                userId="me", id=msg["id"], format="full"
            ).execute()
            new_messages.append(full)

    return new_messages

def extract_text(message):
    subject = ""
    body = ""

    headers = message["payload"].get("headers", [])
    for h in headers:
        if h["name"] == "Subject":
            subject = h["value"]

    def get_body(payload):
        if "body" in payload and payload["body"].get("data"):
            data = payload["body"]["data"]
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
        if "parts" in payload:
            for part in payload["parts"]:
                if part.get("mimeType") == "text/plain":
                    data = part["body"].get("data", "")
                    if data:
                        return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
        return ""

    body = get_body(message["payload"])[:2000]
    return subject, body


# ===== СЕМАНТИЧЕСКАЯ ПРОВЕРКА ЧЕРЕЗ GROQ =====

def is_relevant(subject, body):
    prompt = f"""
{INTERESTS}

Вот письмо из научной рассылки.
Тема: {subject}
Текст: {body}

Определи, связано ли это письмо с моими интересами — даже косвенно или через смежные понятия.
Например, "конфликтогенность" связана с тональностью, потому что обе области изучают эмоциональную нагрузку текста.

Ответь строго в формате JSON без лишнего текста:
{{"relevant": true/false, "reason": "краткое объяснение на русском, 1-2 предложения"}}
"""

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2
            },
            timeout=30
        )
        response.raise_for_status()
        text = response.json()["choices"][0]["message"]["content"]

        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            print("Не удалось извлечь JSON из ответа Groq")
            return False, ""

        result = json.loads(match.group())
        return result.get("relevant", False), result.get("reason", "")

    except Exception as e:
        print(f"Ошибка при запросе к Groq: {e}")
        return False, ""


# ===== ОТПРАВКА В TELEGRAM =====

def send_telegram(subject, reason, message_id):
    link = f"https://mail.google.com/mail/u/0/#inbox/{message_id}"
    text = (
        f"📬 *Новое релевантное письмо в mosling*\n\n"
        f"*Тема:* {subject}\n\n"
        f"*Почему интересно:* {reason}\n\n"
        f"[Открыть письмо]({link})"
    )
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": TG_CHAT_ID,
                "text": text,
                "parse_mode": "Markdown"
            },
            timeout=10
        )
    except Exception as e:
        print(f"Ошибка при отправке в Telegram: {e}")


# ===== MAIN =====

def main():
    print("Запуск проверки писем...")

    service = get_gmail_service()
    processed_ids = load_processed_ids()
    messages = get_new_messages(service, processed_ids)

    print(f"Найдено новых писем: {len(messages)}")

    for message in messages:
        subject, body = extract_text(message)
        print(f"Проверяю: {subject}")

        relevant, reason = is_relevant(subject, body)

        if relevant:
            print(f"  ✅ Релевантно — отправляю в Telegram")
            send_telegram(subject, reason, message["id"])
        else:
            print(f"  ⬜ Нерелевантно")

        processed_ids.add(message["id"])

    save_processed_ids(processed_ids)
    print("Готово.")

if __name__ == "__main__":
    main()
