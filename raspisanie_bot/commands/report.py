import aiogram
from aiogram.dispatcher import FSMContext

from ..config import feature_enabled
from ..database import User


async def cmd_report(message: aiogram.types.Message, state: FSMContext):
    User.from_telegram(message.from_user)

    await message.answer("В разработке report")
    await state.reset_state()


def install_report(dp, all_commands):
    if feature_enabled("report"):
        dp.register_message_handler(cmd_report, commands="report", state='*')
        all_commands.append(aiogram.types.BotCommand("/report", "Сообщить об ошибке"))
