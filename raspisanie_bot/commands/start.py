import aiogram
from aiogram.dispatcher import FSMContext

from ..bot_errors import bot_error
from ..config import INVITE_SIGN_KEY
from ..database import Invite, User
from ..encoded_invite import decode_invite


HELP_TEXT = """\
⭐ Нажмите кнопку *меню* в левом нижнем углу чтобы открыть список команд\\.
⭐ Нажмите /settings чтобы зайти в настройки и указать свою группу\\. После этого ваше расписание будет доступно по команде /my\\.
⭐ /search \\- поиск по группе, фамилии преподавателя или номеру кабинета\\.
⭐ /time \\- посмотреть расписание звонков\\.
"""


async def send_help(message: aiogram.types.Message, user: User):
    await message.answer(HELP_TEXT)


async def cmd_start(message: aiogram.types.Message, state: FSMContext):
    user = User.from_telegram(message.from_user)

    args = message.get_args()
    if args:
        iid = decode_invite(INVITE_SIGN_KEY, args)
        invite = Invite.get_or_none(Invite.rowid == iid)

        if invite is None:
            bot_error("INVITE_NOT_EXIST", invite=iid, user=user)

        if user.invite is not None:
            if user.invite.rowid != invite.rowid:
                bot_error("INVITE_ANOTHER_USED", invite=invite, user=user)

            await message.reply("Вы уже использовали этот код, повторное использование ничего не меняет")

        else:
            user.invite = invite

            if invite.set_admin:
                if invite.is_used:
                    bot_error("INVITE_USED", user=user, invite=invite)

                # Если у пользователя забрали права администратора, то все его приглашения, дававшие права
                # администратора перестанут работать.
                if not invite.author.get().is_admin:
                    bot_error("NOT_ADMIN", user=user, invite=invite)

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
    dp.register_message_handler(cmd_cancel, commands="cancel", state='*')


def install_start(dp, all_commands):
    all_commands.append(aiogram.types.BotCommand("/cancel", "Отмена действия"))

    dp.register_message_handler(cmd_start, commands="start", state='*')

    dp.register_message_handler(cmd_help, commands="help", state='*')
    all_commands.append(aiogram.types.BotCommand("/help", "Справка"))
