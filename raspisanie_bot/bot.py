import logging

import aiogram
from aiogram.utils import executor

from raspisanie_bot import config
from raspisanie_bot.commands import install_all_commands

logging.basicConfig(level=logging.INFO)

bot = aiogram.Bot(token=config.BOT_TOKEN)
dp = aiogram.Dispatcher(bot)
install_all_commands(dp)


if __name__ == "__main__":
    executor.start_polling(dp)
