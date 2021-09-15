import asyncio
import logging

import aiogram
from aiogram.utils import executor

from raspisanie_bot import config
from raspisanie_bot.bot_errors import install_error_handlers
from raspisanie_bot.commands import install_all_commands
from aiogram.contrib.middlewares.logging import LoggingMiddleware

from raspisanie_bot.sqlite_storage import SQLiteStorage
from raspisanie_bot.updater import update_timetable

logging.basicConfig(level=logging.INFO)

bot = aiogram.Bot(token=config.BOT_TOKEN)
dp = aiogram.Dispatcher(bot, storage=SQLiteStorage())
dp.setup_middleware(LoggingMiddleware())
install_all_commands(dp)
install_error_handlers(dp)


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(update_timetable())
    executor.start_polling(dp)
