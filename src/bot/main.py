"""Bot entry point — application setup and startup."""

import logging

from aiohttp import web
from redis.asyncio import from_url as redis_from_url
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
)

from bot.ai_client import AIClient
from bot.config import get_settings
from bot.handlers import Handlers
from bot.memory import ConversationMemory
from bot.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


async def health_handler(request: web.Request) -> web.Response:
    return web.Response(text="OK")


async def run_health_server(port: int) -> web.AppRunner:
    app = web.Application()
    app.router.add_get("/health", health_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info("Health check server running on port %d", port)
    return runner


def main() -> None:
    settings = get_settings()

    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
    )

    logger.info("Starting bot")

    app = ApplicationBuilder().token(settings.telegram_bot_token).build()

    async def post_init(application) -> None:
        redis = redis_from_url(
            settings.redis_url, decode_responses=True
        )
        application.bot_data["redis"] = redis

        ai_client = AIClient(settings)
        memory = ConversationMemory(settings, redis)
        rate_limiter = RateLimiter(settings, redis)
        handlers = Handlers(ai_client, memory, rate_limiter)

        application.bot_data["ai_client"] = ai_client
        application.bot_data["health_runner"] = await run_health_server(
            settings.health_check_port
        )

        application.add_handler(
            CommandHandler("start", handlers.start)
        )
        application.add_handler(
            CommandHandler("help", handlers.help_command)
        )
        application.add_handler(
            CommandHandler("clear", handlers.clear)
        )
        application.add_handler(
            CommandHandler("system", handlers.system)
        )
        application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND, handlers.message
            )
        )

        logger.info("Bot initialized")

    async def post_shutdown(application) -> None:
        ai_client = application.bot_data.get("ai_client")
        if ai_client:
            await ai_client.close()

        redis = application.bot_data.get("redis")
        if redis:
            await redis.close()

        health_runner = application.bot_data.get("health_runner")
        if health_runner:
            await health_runner.cleanup()

        logger.info("Bot shut down")

    app.post_init = post_init
    app.post_shutdown = post_shutdown
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
