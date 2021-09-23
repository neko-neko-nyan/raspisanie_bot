import aiogram
from aiogram.dispatcher import FSMContext

from ..bot_errors import bot_error
from ..config import feature_enabled
from ..database import User


async def cmd_admin(message: aiogram.types.Message, state: FSMContext):
    user = User.from_telegram(message.from_user)

    if not user.is_admin:
        bot_error("NOT_ADMIN", user=user)

    await message.answer("В разработке admin")
    await state.reset_state()


def install_admin(dp):
    if feature_enabled("admin"):
        dp.register_message_handler(cmd_admin, commands="admin", state='*')
