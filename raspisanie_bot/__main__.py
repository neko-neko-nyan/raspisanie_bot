import asyncio
import logging

import aiogram
from aiogram.contrib.middlewares.logging import LoggingMiddleware

from raspisanie_bot import config
from raspisanie_bot.bot_errors import install_error_handlers
from raspisanie_bot.commands import install_all_commands
from raspisanie_bot.parsing import UpdateService
from raspisanie_bot.sqlite_storage import SQLiteStorage

UPDATE_SERVICE = UpdateService()


async def main():
    UPDATE_SERVICE.start()

    bot = aiogram.Bot(token=config.BOT_TOKEN)
    dp = aiogram.Dispatcher(bot, storage=SQLiteStorage())
    dp.setup_middleware(LoggingMiddleware())

    install_all_commands(dp)
    install_error_handlers(dp)

    await bot.set_my_commands([
        aiogram.types.BotCommand("/my", "Мое расписание"),
        aiogram.types.BotCommand("/search", "Найти группу, преподавателя или кабинет"),
        aiogram.types.BotCommand("/search_me", "Найти себя"),

        aiogram.types.BotCommand("/invite", "Создать ссылку-приглашение"),

        aiogram.types.BotCommand("/cancel", "Отмена действия"),
        aiogram.types.BotCommand("/settings", "Настройки"),
        aiogram.types.BotCommand("/help", "Справка"),
        aiogram.types.BotCommand("/start", "Справка, использовать код приглашения"),
    ])

    await dp.start_polling()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.get_event_loop().run_until_complete(main())
