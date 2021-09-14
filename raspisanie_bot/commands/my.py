import aiogram

from raspisanie_bot.database import User


async def cmd_my(message: aiogram.types.Message):
    user = User.from_telegram(message.from_user)

    if not user.is_configured():
        await message.answer("Вы не можете использовать эту команду так как Вы не указали свою группу / ФИО. Сначала "
                             "укажите свои данные через /settings. (код = 1, данные = )")
        return

    await message.answer("В разработке")


def install_my(dp):
    dp.register_message_handler(cmd_my, commands="my")
