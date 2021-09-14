import aiogram


async def cmd_admin(message: aiogram.types.Message):
    await message.answer("В разработке")


def install_admin(dp):
    dp.register_message_handler(cmd_admin, commands="admin")
