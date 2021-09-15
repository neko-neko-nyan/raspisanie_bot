import aiogram
import jwt
from aiogram.dispatcher import FSMContext

from raspisanie_bot import config
from raspisanie_bot.bot_errors import bot_error
from raspisanie_bot.database import Teacher, Invite, Group, User


async def send_help(message: aiogram.types.Message, user: User):
    await message.answer("В разработке (help_text)")


async def cmd_start(message: aiogram.types.Message, state: FSMContext):
    user = User.from_telegram(message.from_user)

    args = message.get_args()
    if args:
        invite_data = jwt.decode(args, config.JWT_KEY, algorithms=["HS256"])
        if "iid" not in invite_data:
            bot_error("JWT_ERROR")

        invite = Invite.get_or_none(Invite.id == invite_data["iid"], Invite.is_used == False)

        if invite is None:
            bot_error("INVITE_USED", invite=invite_data["iid"], user=user.tg_id)

        if user.invite is not None:
            if user.invite != invite.id:
                bot_error("ANOTHER_INVITE_USED", invite=invite.id, user=user.tg_id)

            await message.reply("Вы уже использовали этот код, повторное использование ничего не меняет :(")

        else:
            user.invited_by = invite.created_by
            user.invite = invite
            invite.is_used = True

            if "isa" in invite_data:
                # Если у пользователя забрали права администратора, то все его приглашения, дававшие права
                # администратора перестанут работать.
                if not User.get_by_id(invite.created_by).is_admin:
                    bot_error("NOT_ADMIN", user=user.tg_id, invite=invite.id)

                user.is_admin = True

            if "gri" in invite_data:
                user.group = Group.get_or_none(Group.id == invite_data["gri"])

            elif "tei" in invite_data:
                user.teacher = Teacher.get_or_none(Teacher.id == invite_data["tei"])

            invite.save()
            user.save()
            await message.reply("Код приглашения активирован успешно")

    await send_help(message, user)
    await state.reset_state()


async def cmd_help(message: aiogram.types.Message, state: FSMContext):
    user = User.from_telegram(message.from_user)
    await send_help(message, user)
    await state.reset_state()


def install_start(dp):
    dp.register_message_handler(cmd_start, commands="start", state='*')
    dp.register_message_handler(cmd_help, commands="help", state='*')
