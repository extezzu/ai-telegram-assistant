# AI Telegram Assistant

A production-ready Telegram bot with OpenAI GPT-4 integration, conversation memory, and multi-user support.

## Features

- **GPT-4o-mini Integration** — Powered by OpenAI's chat completions API
- **Conversation Memory** — Remembers context per user (configurable history length)
- **Redis Storage** — Persistent conversation storage across bot restarts
- **Rate Limiting** — Per-user rate limiting with sliding window algorithm
- **Custom System Prompts** — Each user can set their own AI personality
- **Token Tracking** — Logs token usage for cost monitoring
- **Smart Message Splitting** — Auto-splits long responses for Telegram's 4096 char limit
- **Docker Deployment** — One-command deployment with Docker Compose

## Architecture

```
┌─────────────────────────────────────────────┐
│                Telegram API                  │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│              Bot Application                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────────┐│
│  │ Handlers │ │ AI Client│ │ Rate Limiter ││
│  └────┬─────┘ └────┬─────┘ └──────┬───────┘│
│       │             │              │         │
│  ┌────▼─────────────▼──────────────▼───────┐│
│  │          Conversation Memory             ││
│  └──────────────────┬──────────────────────┘│
└─────────────────────┼───────────────────────┘
                      │
         ┌────────────▼────────────┐
         │     Redis (Storage)     │
         └─────────────────────────┘
```

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message and bot introduction |
| `/help` | Show available commands and tips |
| `/clear` | Clear your conversation history |
| `/system <prompt>` | Set a custom system prompt |

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- OpenAI API Key (from [platform.openai.com](https://platform.openai.com))

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/extezzu/ai-telegram-assistant.git
   cd ai-telegram-assistant
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Run with Docker Compose**
   ```bash
   docker compose up -d
   ```

4. **Check logs**
   ```bash
   docker compose logs -f bot
   ```

### Local Development

1. **Install dependencies**
   ```bash
   pip install -e ".[dev]"
   ```

2. **Start Redis**
   ```bash
   docker run -d -p 6379:6379 redis:7-alpine
   ```

3. **Run the bot**
   ```bash
   cd src && python -m bot.main
   ```

4. **Run tests**
   ```bash
   python -m pytest tests/ -v
   ```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | — | Telegram Bot API token (required) |
| `OPENAI_API_KEY` | — | OpenAI API key (required) |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model to use |
| `OPENAI_MAX_TOKENS` | `1024` | Max tokens in AI response |
| `OPENAI_TEMPERATURE` | `0.7` | Response creativity (0.0–2.0) |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `MAX_CONVERSATION_LENGTH` | `20` | Messages to keep per user |
| `RATE_LIMIT_PER_MINUTE` | `10` | Max messages per user per minute |
| `DEFAULT_SYSTEM_PROMPT` | `You are a helpful AI assistant...` | Default AI behavior |
| `HEALTH_CHECK_PORT` | `8080` | Health check HTTP port |
| `LOG_LEVEL` | `INFO` | Logging level |

## Project Structure

```
ai-telegram-assistant/
├── src/bot/
│   ├── main.py          # Entry point, bot setup
│   ├── handlers.py      # Command and message handlers
│   ├── ai_client.py     # OpenAI API wrapper
│   ├── memory.py        # Conversation memory (Redis)
│   ├── rate_limiter.py  # Per-user rate limiting
│   ├── config.py        # Settings from .env
│   └── utils.py         # Text splitting, formatting
├── tests/               # Unit tests
├── docker-compose.yml   # Docker deployment
├── Dockerfile           # Container image
└── pyproject.toml       # Project configuration
```

## Tech Stack

- **Python 3.11+** — Modern async/await
- **python-telegram-bot v20+** — Async Telegram Bot API
- **OpenAI Python SDK** — GPT-4 integration
- **Redis** — Persistent conversation storage
- **Pydantic Settings** — Type-safe configuration
- **Docker Compose** — One-command deployment

## License

MIT
