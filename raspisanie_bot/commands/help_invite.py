import aiogram
import jwt
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from raspisanie_bot import config
from raspisanie_bot.database import Teacher, Invite, Group, User


async def send_help(message: aiogram.types.Message, user: User):
    await message.answer("В разработке")


async def cmd_start(message: aiogram.types.Message):
    user = User.from_telegram(message.from_user)

    args = message.get_args()
    if len(args) == 1:
        if user.invite is not None:
            await message.reply("Вы уже использовали код приглашения однажды. Чтобы использовать другой код надо чтобы"
                                " администратор сбросил настройки вашей учетой записи. (код = 12, данные = )")
            return

        token = jwt.decode(args[0], config.JWT_TOKEN, algorithms=["HS256"])

        group = token.get("gri")
        teacher = token.get("tei")
        is_admin = token.get("isa", False)
        invite_id = token["iid"]

        invite = Invite.get(Invite.id == invite_id)

        user.invited_by = invite.created_by
        user.invite = invite

        if is_admin:
            user.is_admin = True

        if group:
            user.group = Group.get(Group.id == group)

        elif teacher:
            user.teacher = Teacher.get(Teacher.id == teacher)

        user.save()
        await message.reply("Код приглашения активирован успешно")

    await send_help(message, user)


async def cmd_help(message: aiogram.types.Message):
    user = User.from_telegram(message.from_user)
    await send_help(message, user)


async def cmd_invite(message: aiogram.types.Message):
    user = User.from_telegram(message.from_user)
    args = message.get_args().split()

    if args:
        invite_data = {}

        if "admin" in args:
            if not user.is_admin:
                await message.reply("Вы не можете создать приглашение для администратора так как сами не являетесь "
                                    "администратором. (код = 11, данные = )")
                return

            invite_data["isa"] = True
            args.remove("admin")

        # noinspection PyTypeChecker
        args = dict((i.split('=', 1) for i in args))

        group = args.get("group")
        if group:
            group = Group.get(group)
            invite_data["gri"] = group.id

        teacher = args.get("teacher")
        if teacher:
            teacher = Teacher.get(teacher)
            invite_data["tei"] = teacher.id

        invite_data["iid"] = Invite.create(created_by=user).id
        code = jwt.encode(invite_data, config.JWT_TOKEN)
        await message.answer(f"https://t.me/nkrp_bot?start={code}")

    else:
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("Группа", callback_data="i.sg"),
               InlineKeyboardButton("Преподаватель", callback_data="i.st"))

        if user.is_admin:
            kb.add(InlineKeyboardButton("Сделать администратором", callback_data="i.sa"))

        kb.add(InlineKeyboardButton("Создать", callback_data="i.c"))
        await message.answer("Тип: НЕ УКАЗАН", reply_markup=kb)


def install_help_invite(dp):
    dp.register_message_handler(cmd_start, commands="start")
    dp.register_message_handler(cmd_help, commands="help")
    dp.register_message_handler(cmd_invite, commands="invite")
