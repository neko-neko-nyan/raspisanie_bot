import aiogram
from aiogram.dispatcher import FSMContext

from raspisanie_bot import config, encoded_invite
from raspisanie_bot.bot_errors import bot_error
from raspisanie_bot.database import Teacher, Invite, Group, User


async def send_help(message: aiogram.types.Message, user: User):
    await message.answer("В разработке (help_text)")


async def cmd_start(message: aiogram.types.Message, state: FSMContext):
    user = User.from_telegram(message.from_user)

    args = message.get_args()
    if args:
        iid, gri, tei, isa = encoded_invite.decode_invite(config.JWT_KEY, args)
        invite = Invite.get_or_none(Invite.id == iid, Invite.is_used == False)

        if invite is None:
            bot_error("INVITE_USED", invite=iid, user=user.tg_id)

        if user.invite is not None:
            if user.invite != invite.id:
                bot_error("ANOTHER_INVITE_USED", invite=invite.id, user=user.tg_id)

            await message.reply("Вы уже использовали этот код, повторное использование ничего не меняет :(")

        else:
            user.invited_by = invite.created_by
            user.invite = invite
            invite.is_used = True

            if isa:
                # Если у пользователя забрали права администратора, то все его приглашения, дававшие права
                # администратора перестанут работать.
                if not User.get_by_id(invite.created_by).is_admin:
                    bot_error("NOT_ADMIN", user=user.tg_id, invite=invite.id)

                user.is_admin = True

            if gri is not None:
                user.group = Group.get_or_none(Group.id == gri)

            elif tei is not None:
                user.teacher = Teacher.get_or_none(Teacher.id == tei)

            invite.save()
            user.save()
            await message.reply("Код приглашения активирован успешно")

    await send_help(message, user)
    await state.reset_state()


async def cmd_help(message: aiogram.types.Message, state: FSMContext):
    user = User.from_telegram(message.from_user)
    await send_help(message, user)
    await state.reset_state()


async def cmd_cancel(message: aiogram.types.Message, state: FSMContext):
    User.from_telegram(message.from_user)
    await message.answer("Действие отменено")
    await state.reset_state()


def install_start(dp):
    # Должен быть всегда первым для работы команды /cancel
    dp.register_message_handler(cmd_cancel, commands="cancel", state='*')
    dp.register_message_handler(cmd_cancel, lambda msg: msg.text.lower().strip() == 'отмена', state='*')

    dp.register_message_handler(cmd_start, commands="start", state='*')
    dp.register_message_handler(cmd_help, commands="help", state='*')
