# Digital Support Bot

A Telegram Customer Support bot built with FastAPI, Aiogram, and PostgreSQL.

## Features
- **Customer**: Private chat with bot, messages forwarded to Agent Group.
- **Agent**: Reply in Agent Group to talk to customers.
- **Commands**: `/lock`, `/unlock`, `/close`, `/list` to manage conversations.
- **Tech Stack**: Python 3.11, FastAPI, Aiogram 3, SQLAlchemy Async, Alembic, Docker.

## Setup

1. **Environment Variables**
   Copy `.env.example` to `.env` and fill in your values:
   ```bash
   cp .env.example .env
   ```
   - `BOT_TOKEN`: From @BotFather.
   - `AGENT_GROUP_ID`: The ID of the group where agents are. (Add bot to group, send message, retrieve ID).

2. **Docker Run**
   ```bash
   docker-compose up --build
   ```
   This will:
   - Start Postgres.
   - Build the App image.
   - Run migrations (auto-create tables).
   - Start the FastAPI app + Bot polling.

3. **Migrations (Manual)**
   If running locally without Docker:
   ```bash
   # Install dependencies
   pip install -r requirements.txt
   
   # Run migrations
   alembic upgrade head
   
   # Generate new migration (after model changes)
   alembic revision --autogenerate -m "description"
   ```

## Development
- run `uvicorn app.main:app --reload` for local dev (requires local Postgres).

## Usage
- **Start**: User sends `/start` or any message.
- **Agent**:
  - Reply to forwarded message: Sends message to user.
  - `/list`: See open tickets.
  - `/lock <conversation_id>`: Claim a ticket.
  - `/close <conversation_id>`: Close ticket.
