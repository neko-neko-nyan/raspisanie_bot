import aiogram
from aiogram.dispatcher import FSMContext

from ..bot_errors import bot_error
from ..database import User, Group, Teacher, PairTime, Pair, CVPItem
from ..message_builder import MessageBuilder


async def my_for_students(message: aiogram.types.Message, user, group):
    results = []

    for pair in Pair.select().where(Pair.group == group).order_by(Pair.date, Pair.pair_number):
        pair_time = PairTime.get(PairTime.pair_number == pair.pair_number)
        results.append((pair.date, pair_time.start_time, pair_time.end_time, pair, pair_time))

    for item in CVPItem.select().where(CVPItem.group == group).order_by(CVPItem.date):
        results.append((item.date, item.start_time, item.end_time, None, None))

    results.sort(key=lambda x: (x[0], x[1], -x[2]))

    prev_date = None
    res = MessageBuilder()

    for date, start_time, end_time, pair, pair_time in results:
        if date != prev_date:
            res.underline().date(date).no_underline().nl()
            prev_date = date

        res.time(start_time).text(" - ").time(end_time).raw(" ")

        if pair is None:
            res.bold("Столовая")
        else:
            if pair_time.is_current:
                res.code(pair.pair_number)
            else:
                res.text(pair.pair_number)

            res.raw(" ").bold(pair.name)

            for i in pair.teachers:
                res.text(" ", i.short_name)

            for i in pair.cabinets:
                res.text(" ", i.number)

        res.nl()

    res.or_text("Нет пар")
    await message.answer(str(res))


async def my_for_teachers(message: aiogram.types.Message, user, teacher):
    prev_date = None
    res = MessageBuilder()

    for pair in Pair.select().where(Pair.rowid.in_(
            Pair.teachers.through_model.select(Pair.teachers.through_model.pair_id)
                    .where(Pair.teachers.through_model.teacher_id == teacher.rowid)
    )).order_by(Pair.date, Pair.pair_number):
        if pair.date != prev_date:
            res.underline().date(pair.date).no_underline().nl()
            prev_date = pair.date

        pair_time = PairTime.get(PairTime.pair_number == pair.pair_number)
        res.time(pair_time.start_time).text(" - ").time(pair_time.end_time).raw(" ")

        if pair_time.is_current:
            res.code(pair.pair_number)
        else:
            res.text(pair.pair_number)

        res.raw(" ").bold(pair.name).text(" ", pair.group.string_value)

        for i in pair.cabinets:
            res.text(" ", i.number)

        res.nl()

    res.or_text("Нет пар")
    await message.answer(str(res))


async def cmd_my(message: aiogram.types.Message, state: FSMContext):
    user = User.from_telegram(message.from_user)

    if user.group is not None:
        await my_for_students(message, user, Group.get_by_id(user.group))

    elif user.teacher is not None:
        await my_for_teachers(message, user, Teacher.get_by_id(user.teacher))

    else:
        bot_error("NOT_CONFIGURED", user=user)

    await state.reset_state()


def install_my(dp, all_commands):
    dp.register_message_handler(cmd_my, commands="my", state='*')
    all_commands.append(aiogram.types.BotCommand("/my", "Мое расписание"))
