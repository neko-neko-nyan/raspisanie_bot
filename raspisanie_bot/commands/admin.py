import aiogram
from aiogram.dispatcher import FSMContext

from ..bot_errors import bot_error
from ..database import User


async def cmd_admin(message: aiogram.types.Message, state: FSMContext):
    user = User.from_telegram(message.from_user)

    if not user.is_admin:
        bot_error("NOT_ADMIN", user=user)

    arg = message.get_args()
    if arg == "update":
        from .. import bot_main
        bot_main.UPDATE_SERVICE.force_update()
        await message.answer("Обновление инициировано")
    else:
        await message.answer("В разработке admin")
    await state.reset_state()


def install_admin(dp):
    dp.register_message_handler(cmd_admin, commands="admin", state='*')
