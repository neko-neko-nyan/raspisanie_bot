import aiogram

from raspisanie_bot.database import User


async def do_search(message: aiogram.types.Message, user, text):
    await message.answer(f"В разработке (текст = {text!r})")


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
        await message.answer("Вы не можете использовать эту команду так как Вы не указали свою группу / ФИО. Сначала "
                             "укажите свои данные через /settings. (код = 1, данные = )")


def install_search(dp):
    dp.register_message_handler(cmd_search, commands="search")
    dp.register_message_handler(cmd_search_me, commands="search_me")
