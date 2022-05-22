import datetime

import aiogram
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State

from ..bot_errors import bot_error
from ..bot_utils import get_group_or_none, get_teacher_or_none
from ..database import User, Group, Cabinet, Teacher, Pair, PairTime
from ..message_builder import MessageBuilder


def is_allow_hide_pair_comp(tm, gc, query):
    count = Pair\
        .select(gc)\
        .distinct(True)\
        .join(tm)\
        .where(query) \
        .count()
    return count == 1


async def do_search_query(message: aiogram.types.Message, user, search_type, target):
    if search_type == 'group':
        query = Pair.group == target
        allow_hide = True

    elif search_type == 'cabinet':
        query = Pair.rowid.in_(Pair.cabinets.through_model.select(Pair.cabinets.through_model.pair_id)
                               .where(Pair.cabinets.through_model.cabinet_id == target.number))
        allow_hide = is_allow_hide_pair_comp(Pair.cabinets.through_model, Pair.cabinets.through_model.cabinet_id, query)

    else:
        assert search_type == 'teacher'
        query = Pair.rowid.in_(Pair.teachers.through_model.select(Pair.teachers.through_model.pair_id)
                               .where(Pair.teachers.through_model.teacher_id == target.rowid))
        allow_hide = is_allow_hide_pair_comp(Pair.teachers.through_model, Pair.teachers.through_model.teacher_id, query)

    now = datetime.datetime.now()
    in_pair, current_pair = PairTime.by_time(now)
    today = now.date()

    prev_date = None
    res = MessageBuilder()

    for pair in Pair.select(Pair, Group).join(Group).where(query).order_by(Pair.date, Pair.pair_number):
        if pair.date != prev_date:
            res.underline().date(pair.date).no_underline().nl()
            prev_date = pair.date

        pair_time = PairTime.get_or_none(PairTime.pair_number == pair.pair_number)
        if pair_time is not None:
            res.time(pair_time.start_time).text(" - ").time(pair_time.end_time).raw(" ")

        if pair.date == today and current_pair is not None and pair.pair_number == current_pair.pair_number:
            res.code(pair.pair_number)
        else:
            res.text(pair.pair_number)

        res.raw(' ').bold(pair.name)

        if search_type != 'group':
            res.raw(' ').text(pair.group.string_value)

        if search_type != 'teacher' or not allow_hide:
            for i in pair.teachers:
                res.raw(' ')
                res.text(i.short_name)

        if search_type != 'cabinet' or not allow_hide:
            for i in pair.cabinets:
                res.raw(' ')
                res.text(i.number)

        res.nl()

    res.or_text("Нет пар")
    await message.answer(str(res))


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
            await do_search_query(message, user, 'cabinet', cabinet)
            return

    group = get_group_or_none(text)
    if group is not None:
        await do_search_query(message, user, 'group', group)
        return

    teacher = get_teacher_or_none(text)
    if teacher is not None:
        await do_search_query(message, user, 'teacher', teacher)
        return

    bot_error("NOT_FOUND", user=user, text=text)


class SearchStates(StatesGroup):
    waiting_for_text = State()


async def cmd_search(message: aiogram.types.Message, state: FSMContext):
    user = User.from_telegram(message.from_user)
    args = message.get_args()
    if args:
        await do_search(message, user, args)
        await state.reset_state()

    else:
        await message.answer("Введите текст поиска \\(преподаватель, группа или кабинет\\)")
        await SearchStates.waiting_for_text.set()


async def msg_search_text(message: aiogram.types.Message, state: FSMContext):
    user = User.from_telegram(message.from_user)
    await do_search(message, user, message.text)
    await state.finish()


def install_search(dp, all_commands):
    dp.register_message_handler(cmd_search, commands="search", state='*')
    all_commands.append(aiogram.types.BotCommand("/search", "Найти группу, преподавателя или кабинет"))

    dp.register_message_handler(msg_search_text, state=SearchStates.waiting_for_text)
