# tell-g

ערוץ הדילים: https://t.me/dandell1

בוט שרץ כל שעתיים ב-GitHub Actions, מחפש דילים קיצוניים (ברירת מחדל: 50% הנחה ומעלה)
בביגוד והנעלה לגברים, נשים וילדים, ורק כאלה שיש להם משלוח לישראל. כל דיל חדש עולה לערוץ.

## הגדרה (Settings ← Secrets and variables ← Actions)
- `TELEGRAM_BOT_TOKEN` – ה-Token מ-BotFather
- `TELEGRAM_CHAT_ID` – `@dandell1`
- אופציונלי, קישורי שותפים:
  - `AMAZON_TAG` – ה-Tag מ-Amazon Associates
  - `AFFILIATE_TEMPLATE_ALIEXPRESS_COM` – תבנית עם `{url}`, למשל `https://s.click.aliexpress.com/deep_link.htm?dl_target_url={url}&aff_short_key=XXXX`
  - `AFFILIATE_TEMPLATE_SHEIN_COM` – כנ"ל

## התאמה
`sources.json`: מקורות, אתרים שמשלחים לישראל, סף הנחה (`min_discount_percent`) ומספר פרסומים מקסימלי לכל הרצה.

## הרצה מקומית
`python3 bot.py` בלי סודות מדפיס את הדילים בלבד (dry run). בדיקות: `python3 -I tests/test_bot.py`.
