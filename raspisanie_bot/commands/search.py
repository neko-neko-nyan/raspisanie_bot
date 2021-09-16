import aiogram
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State

from raspisanie_bot.bot_errors import bot_error
from raspisanie_bot.bot_utils import get_group_or_none, get_teacher_or_none
from raspisanie_bot.database import User, Group, Cabinet, Teacher


async def do_search_cabinet(message: aiogram.types.Message, user, cabinet):
    await message.answer("В разработке (do_search_cabinet)")


async def do_search_group(message: aiogram.types.Message, user, group):
    await message.answer("В разработке (do_search_group)")


async def do_search_teacher(message: aiogram.types.Message, user, teacher):
    await message.answer("В разработке (do_search_teacher)")


async def do_search(message: aiogram.types.Message, user, text):
    text = text.lower().strip()

    try:
        if text == "спортзал":
            cabinet = 200
        else:
            cabinet = int(text)

    except ValueError:
        pass

    else:
        cabinet = Cabinet.get_or_none(Cabinet.number == cabinet)
        if cabinet is not None:
            await do_search_cabinet(message, user, cabinet)
            return

    group = get_group_or_none(text)
    if group is not None:
        await do_search_group(message, user, group)
        return

    teacher = get_teacher_or_none(text)
    if teacher is not None:
        await do_search_teacher(message, user, teacher)
        return

    bot_error("NOT_FOUND", user=user.tg_id, text=text)


class SearchStates(StatesGroup):
    waiting_for_text = State()


async def cmd_search(message: aiogram.types.Message, state: FSMContext):
    user = User.from_telegram(message.from_user)
    args = message.get_args()
    if args:
        await do_search(message, user, args)
        await state.reset_state()

    else:
        await message.answer("Введите текст поиска (преподаватель, группа или кабинет)")
        await SearchStates.waiting_for_text.set()


async def msg_search_text(message: aiogram.types.Message, state: FSMContext):
    user = User.from_telegram(message.from_user)
    await do_search(message, user, message.text)
    await state.finish()


async def cmd_search_me(message: aiogram.types.Message, state: FSMContext):
    user = User.from_telegram(message.from_user)

    if user.group is not None:
        await do_search_group(message, user, Group.get_by_id(user.group))

    elif user.teacher is not None:
        await do_search_teacher(message, user, Teacher.get_by_id(user.teacher))

    else:
        bot_error("NOT_CONFIGURED", user=user.tg_id)

    await state.reset_state()


def install_search(dp):
    dp.register_message_handler(cmd_search, commands="search", state='*')
    dp.register_message_handler(cmd_search_me, commands="search_me", state='*')
    dp.register_message_handler(msg_search_text, state=SearchStates.waiting_for_text)
