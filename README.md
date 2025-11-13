# Telegram Quiz Bot

## توضیح
یک ربات تلگرام ساده برای ساخت و برگزاری آزمون‌ها. امکانات:
- ساخت کوییز و سوال توسط ادمین
- سوالات MCQ، تشریحی و درست/نادرست
- نمره‌گذاری خودکار برای MCQ/TrueFalse
- ذخیره پاسخ‌ها و نتایج
- زمانبندی کل آزمون

## راه‌اندازی لوکال
1. فایل `.env` را بساز و متغیرها را از `.env.example` مقداردهی کن.
2. یک محیط مجازی بساز:
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # on Linux/Mac
   .venv\Scripts\activate    # on Windows (PowerShell)
   ```
3. بسته‌ها را نصب کن:
   ```bash
   pip install -r requirements.txt
   ```
4. دیتابیس را بساز (یا هنگام اولین اجرا خود برنامه اینکار را انجام می‌دهد):
   ```bash
   python -c "from db import init; import asyncio; asyncio.run(init('./quiz_bot.db'))"
   ```
5. توکن بات را از BotFather بگیر و `.env` را پر کن.
6. برنامه را اجرا کن:
   ```bash
   python bot.py
   ```

## اجرای در داکر
1. فایل `.env` را مقداردهی کن.
2. بساز:
   ```bash
   docker-compose build
   docker-compose up -d
   ```

## دستورات
- کاربر: `/start`, `/take`, `/resume`, `/help`
- ادمین: `/newquiz`, `/newquestion`, `/publish <quiz_id>`

## نکات مهم
- توکن را منتشر نکن.
- برای بار زیاد از SQLite به PostgreSQL مهاجرت کن.
- سوالات تشریحی نیاز به تصحیح دستی دارند؛ باید پنل مدیریتی اضافه شود.
