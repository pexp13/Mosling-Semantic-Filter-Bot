# Запуск Python-версии

Python-версия делает то же самое, что и Google Apps Script, но запускается локально на вашем компьютере или на сервере.

---

## Требования

- Python 3.8+
- Groq API key
- Telegram-бот (см. [SETUP.md](SETUP.md), Шаг 1)
- Google OAuth2 credentials (см. ниже)

---

## Шаг 1. Установить зависимости

```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client requests
```

---

## Шаг 2. Получить Google OAuth2 credentials

Python-версия использует Gmail API — для этого нужен файл `credentials.json` от Google.

1. Перейдите на [console.cloud.google.com](https://console.cloud.google.com)
2. Создайте новый проект
3. Включите **Gmail API**: "API и сервисы" → "Включить API" → найдите Gmail API → Включить
4. Перейдите в "API и сервисы" → "Учётные данные" → "Создать учётные данные" → "Идентификатор клиента OAuth"
5. Тип приложения: **Приложение для ПК**
6. Скачайте JSON-файл и переименуйте его в `credentials.json`
7. Положите `credentials.json` в папку рядом со скриптом

---

## Шаг 3. Настроить переменные в скрипте

Откройте `src/main.py` и заполните в начале файла:

```python
GROQ_API_KEY = "ВАШ_GROQ_KEY"
TG_BOT_TOKEN = "ВАШ_ТОКЕН_БОТА"
TG_CHAT_ID   = "ВАШ_CHAT_ID"
```

---

## Шаг 4. Первый запуск

```bash
python src/main.py
```

При первом запуске откроется браузер с запросом разрешений Google — разрешите доступ к Gmail. После этого создастся файл `token.pickle`, и браузер больше открываться не будет.

---

## Шаг 5. Автозапуск по расписанию

### Linux / macOS (cron)

```bash
crontab -e
```

Добавьте строку (запуск каждый час):

```
0 * * * * /usr/bin/python3 /путь/до/mosling-bot/src/main.py >> /путь/до/mosling-bot/bot.log 2>&1
```

### Windows (Task Scheduler)

1. Откройте "Планировщик заданий"
2. "Создать простую задачу"
3. Триггер: ежечасно
4. Действие: запустить программу `python`, аргумент: `C:\путь\до\src\main.py`

---

## Файлы, которые создаёт скрипт

| Файл | Назначение |
|---|---|
| `token.pickle` | OAuth2 токен Google (не коммитить в git!) |
| `processed_ids.json` | ID уже обработанных писем |
| `credentials.json` | Ваш OAuth2 ключ (не коммитить в git!) |

Все три файла уже добавлены в `.gitignore`.
