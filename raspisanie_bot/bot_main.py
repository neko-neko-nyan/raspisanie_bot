import asyncio
import logging
import signal

import aiogram
from aiogram.contrib.middlewares.logging import LoggingMiddleware

from raspisanie_bot.bot_errors import install_error_handlers
from raspisanie_bot.commands import install_all_commands
from raspisanie_bot.config import BOT_TOKEN
from raspisanie_bot.database import preload_persistent
from raspisanie_bot.parsing import UpdateService
from raspisanie_bot.sqlite_storage import SQLiteStorage


UPDATE_SERVICE = UpdateService()

bot = aiogram.Bot(token=BOT_TOKEN, parse_mode="MarkdownV2")
dp = aiogram.Dispatcher(bot, storage=SQLiteStorage())


def stop(*_):
    UPDATE_SERVICE.stop()
    dp.stop_polling()


async def a_main():
    preload_persistent()
    UPDATE_SERVICE.start()

    dp.setup_middleware(LoggingMiddleware())

    commands = install_all_commands(dp)
    install_error_handlers(dp)

    await bot.set_my_commands(commands)
    await dp.start_polling(timeout=60)
    await bot.close()


def main():
    signal.signal(signal.SIGINT, stop)
    logging.basicConfig(level=logging.INFO)
    asyncio.get_event_loop().run_until_complete(a_main())
