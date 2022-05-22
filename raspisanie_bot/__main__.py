import asyncio
import logging

import aiogram
from aiogram.contrib.middlewares.logging import LoggingMiddleware

from raspisanie_bot.bot_errors import install_error_handlers
from raspisanie_bot.commands import install_all_commands
from raspisanie_bot.database import preload_persistent
from raspisanie_bot.config import BOT_TOKEN
from raspisanie_bot.parsing import UpdateService
from raspisanie_bot.sqlite_storage import SQLiteStorage

UPDATE_SERVICE = UpdateService()


async def main():
    preload_persistent()
    UPDATE_SERVICE.start()

    bot = aiogram.Bot(token=BOT_TOKEN, parse_mode="MarkdownV2")
    dp = aiogram.Dispatcher(bot, storage=SQLiteStorage())
    dp.setup_middleware(LoggingMiddleware())

    commands = install_all_commands(dp)
    install_error_handlers(dp)

    await bot.set_my_commands(commands)
    await dp.start_polling(timeout=60)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
