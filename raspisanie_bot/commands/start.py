import aiogram
from aiogram.dispatcher import FSMContext

from raspisanie_bot import config, encoded_invite
from raspisanie_bot.bot_errors import bot_error
from raspisanie_bot.database import Invite, User


async def send_help(message: aiogram.types.Message, user: User):
    await message.answer("В разработке (help_text)")


async def cmd_start(message: aiogram.types.Message, state: FSMContext):
    user = User.from_telegram(message.from_user)

    args = message.get_args()
    if args:
        iid = encoded_invite.decode_invite(config.JWT_KEY, args)
        invite = Invite.get_or_none(Invite.id == iid)

        if invite is None:
            bot_error("INVITE_NOT_EXIST", invite=iid, user=user.tg_id)

        if user.invite is not None:
            if user.invite.id != invite.id:
                bot_error("INVITE_ANOTHER_USED", invite=invite.id, user=user.tg_id)

            await message.reply("Вы уже использовали этот код, повторное использование ничего не меняет :(")

        else:
            user.invite = invite

            if invite.set_admin:
                if invite.is_used:
                    bot_error("INVITE_USED", user=user.tg_id, invite=invite.id)

                # Если у пользователя забрали права администратора, то все его приглашения, дававшие права
                # администратора перестанут работать.
                if not invite.author.get().is_admin:
                    bot_error("NOT_ADMIN", user=user.tg_id, invite=invite.id)

                user.is_admin = True

            if invite.set_group is not None:
                user.group = invite.set_group

            elif invite.set_teacher is not None:
                user.teacher = invite.set_teacher

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


def install_cancel(dp):
    dp.register_message_handler(cmd_cancel, lambda msg: msg.text.lower().strip() == 'отмена', state='*')


def install_start(dp, all_commands):
    dp.register_message_handler(cmd_cancel, commands="cancel", state='*')
    all_commands.append(aiogram.types.BotCommand("/cancel", "Отмена действия"))

    dp.register_message_handler(cmd_start, commands="start", state='*')

    dp.register_message_handler(cmd_help, commands="help", state='*')
    all_commands.append(aiogram.types.BotCommand("/help", "Справка"))
