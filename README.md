# Telegram Quiz Bot

This project is a simple Telegram quiz bot built using **python-telegram-bot** and **SQLite**. It presents users with a series of questions, evaluates their answers, and stores their score.

The bot is fully compatible with **Render** deployment using the included `Dockerfile`.

## Features
- Start command to register user
- Quiz command to begin the test
- Automatic question progression
- Stores user score and current question
- Score command to view results

## Files Included
- `bot.py` — Main bot logic
- `db.py` — SQLite handler for storing user progress
- `requirements.txt` — Python dependencies
- `Dockerfile` — Needed for Render deployment

## Deployment on Render
1. Push project to GitHub
2. Create a *Web Service* on Render
3. Select **Docker** as Environment
4. Add an environment variable:
   - `BOT_TOKEN` = Your Telegram bot token
5. Deploy

## Requirements
```
python-telegram-bot==20.7
aiosqlite==0.19.0
```

## Running Locally
```
python bot.py
```
