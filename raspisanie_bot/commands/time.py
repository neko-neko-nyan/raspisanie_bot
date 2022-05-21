import aiogram
from aiogram.dispatcher import FSMContext

from ..database import User, PairTime
from ..message_builder import MessageBuilder


async def cmd_time(message: aiogram.types.Message, state: FSMContext):
    User.from_telegram(message.from_user)

    res = MessageBuilder()
    for i in PairTime.select():
        if i.is_current:
            res.code(i.pair_number)
        else:
            res.text(i.pair_number)
        res.text(". ").time(i.start_time).text(" - ").time(i.end_time).text("\n")

    res.or_text("Расписание звонков недоступно")
    await message.answer(str(res))


def install_time(dp, all_commands):
    dp.register_message_handler(cmd_time, commands="time", state='*')
    all_commands.append(aiogram.types.BotCommand("/time", "Расписание звонков"))
