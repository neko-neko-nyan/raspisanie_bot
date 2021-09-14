import aiogram

from raspisanie_bot.bot_errors import bot_error
from raspisanie_bot.database import User


async def cmd_my(message: aiogram.types.Message):
    user = User.from_telegram(message.from_user)

    if not user.is_configured():
        bot_error("NOT_CONFIGURED", user=user.tg_id)

    await message.answer("В разработке")


def install_my(dp):
    dp.register_message_handler(cmd_my, commands="my")
