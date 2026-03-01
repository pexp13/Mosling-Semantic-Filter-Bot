// ===== НАСТРОЙКИ =====
// Заполните эти четыре переменные своими данными

const GROQ_API_KEY = "YOUR_GROQ_API_KEY";       // console.groq.com — бесплатно, без карты
const TG_BOT_TOKEN = "YOUR_TG_BOT_TOKEN";       // от @BotFather в Telegram
const TG_CHAT_ID   = "YOUR_TG_CHAT_ID";         // от @userinfobot в Telegram
const SENDER       = "mosling@googlegroups.com"; // не менять

// Опишите свои интересы — чем подробнее, тем точнее фильтр
const INTERESTS = `
Мои научные интересы: анализ тональности, сентимент-анализ, динамический сентимент-анализ, 
динамический анализ тональности, эмоции в языке, аффективная лингвистика, 
субъективность в тексте, мнения и оценки в языке, эмоциональная окраска текста.

Смежные области, которые меня интересуют: прагматика, дискурс-анализ, 
корпусная лингвистика, обработка естественного языка (NLP), 
конфликтология текста, риторика, аргументация.
`;

// Название метки в Gmail для уже обработанных писем (не менять без необходимости)
const LABEL_NAME = "mosling_processed";


// ===== ОСНОВНАЯ ФУНКЦИЯ =====
// Запускается по триггеру раз в час

function checkMoslingEmails() {
  let label = GmailApp.getUserLabelByName(LABEL_NAME);
  if (!label) {
    label = GmailApp.createLabel(LABEL_NAME);
  }

  const threads = GmailApp.search(`from:${SENDER} -label:${LABEL_NAME}`);

  for (const thread of threads) {
    const messages = thread.getMessages();
    for (const message of messages) {
      const subject = message.getSubject();
      const body = message.getPlainBody().substring(0, 2000);

      const result = isRelevant(subject, body);

      if (result.yes) {
        sendTelegramNotification(subject, result.reason);
      }
    }
    thread.addLabel(label);
  }
}


// ===== СЕМАНТИЧЕСКАЯ ПРОВЕРКА ЧЕРЕЗ GROQ =====

function isRelevant(subject, body) {
  const prompt = `
${INTERESTS}

Вот письмо из научной рассылки.
Тема: ${subject}
Текст: ${body}

Определи, связано ли это письмо с моими интересами — даже косвенно или через смежные понятия.
Например, "конфликтогенность" связана с тональностью, потому что обе области изучают эмоциональную нагрузку текста.

Ответь строго в формате JSON без лишнего текста:
{"relevant": true/false, "reason": "краткое объяснение на русском, 1-2 предложения"}
`;

  const url = "https://api.groq.com/openai/v1/chat/completions";

  const payload = {
    model: "llama-3.3-70b-versatile",
    messages: [{ role: "user", content: prompt }],
    temperature: 0.2
  };

  try {
    const response = UrlFetchApp.fetch(url, {
      method: "post",
      contentType: "application/json",
      headers: {
        "Authorization": "Bearer " + GROQ_API_KEY
      },
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    });

    const json = JSON.parse(response.getContentText());
    const text = json.choices[0].message.content;

    const match = text.match(/\{[\s\S]*\}/);
    if (!match) {
      Logger.log("Не удалось извлечь JSON из ответа Groq");
      return { yes: false };
    }

    const result = JSON.parse(match[0]);
    return { yes: result.relevant === true, reason: result.reason || "" };

  } catch (e) {
    Logger.log("Ошибка при запросе к Groq: " + e.toString());
    return { yes: false };
  }
}


// ===== ОТПРАВКА УВЕДОМЛЕНИЯ В TELEGRAM =====

function sendTelegramNotification(subject, reason) {
  const text = `📬 *Новое релевантное письмо в mosling*\n\n*Тема:* ${subject}\n\n*Почему интересно:* ${reason}`;
  const url = `https://api.telegram.org/bot${TG_BOT_TOKEN}/sendMessage`;

  try {
    UrlFetchApp.fetch(url, {
      method: "post",
      contentType: "application/json",
      payload: JSON.stringify({
        chat_id: TG_CHAT_ID,
        text: text,
        parse_mode: "Markdown"
      }),
      muteHttpExceptions: true
    });
  } catch (e) {
    Logger.log("Ошибка при отправке в Telegram: " + e.toString());
  }
}
