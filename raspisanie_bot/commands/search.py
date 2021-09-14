import aiogram

from raspisanie_bot.bot_errors import bot_error
from raspisanie_bot.database import User


async def do_search(message: aiogram.types.Message, user, text):
    await message.answer(f"В разработке (search; текст = {text!r})")


async def cmd_search(message: aiogram.types.Message):
    args = message.get_args()
    if args:
        user = User.from_telegram(message.from_user)
        await do_search(message, user, args)

    else:
        await message.answer("Введите текст поиска (преподаватель, группа или кабинет)")


async def cmd_search_me(message: aiogram.types.Message):
    user = User.from_telegram(message.from_user)

    if user.group is not None:
        await do_search(message, user, user.group.string_value)

    elif user.teacher is not None:
        await do_search(message, user, user.teacher.full_name)

    else:
        bot_error("NOT_CONFIGURED", user=user.tg_id)


def install_search(dp):
    dp.register_message_handler(cmd_search, commands="search")
    dp.register_message_handler(cmd_search_me, commands="search_me")
