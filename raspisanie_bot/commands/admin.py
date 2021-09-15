import aiogram
from aiogram.dispatcher import FSMContext

from raspisanie_bot.bot_errors import bot_error
from raspisanie_bot.database import User


async def cmd_admin(message: aiogram.types.Message, state: FSMContext):
    user = User.from_telegram(message.from_user)

    if not user.is_admin:
        bot_error("NOT_ADMIN", user=user.tg_id)

    await message.answer("В разработке (admin)")
    await state.reset_state()


def install_admin(dp):
    dp.register_message_handler(cmd_admin, commands="admin", state='*')
