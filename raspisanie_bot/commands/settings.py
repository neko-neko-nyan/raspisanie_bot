import aiogram

from raspisanie_bot.database import User


async def cmd_settings(message: aiogram.types.Message):
    user = User.from_telegram(message.from_user)
    await message.answer("В разработке")


def install_settings(dp):
    dp.register_message_handler(cmd_settings, commands="settings")
