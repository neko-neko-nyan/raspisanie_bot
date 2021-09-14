import io

import aiogram
import jwt
import qrcode
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from aiogram.utils.callback_data import CallbackData

from raspisanie_bot import config, parse_group_name
from raspisanie_bot.bot_errors import bot_error
from raspisanie_bot.database import Teacher, Invite, Group, User


async def send_help(message: aiogram.types.Message, user: User):
    await message.answer("В разработке (help_text)")


def create_invite(user, group_name=None, teacher_name=None, is_admin=False):
    invite_data = {}

    if is_admin:
        if not user.is_admin:
            bot_error("NOT_ADMIN", user=user.tg_id)

        invite_data["isa"] = True

    if group_name:
        course, group, subgroup = parse_group_name(group_name)
        group = Group.get_or_none(Group.course == course, Group.group == group, Group.subgroup == subgroup)
        if group is None:
            bot_error("INVALID_GROUP", group=group_name)

        invite_data["gri"] = group.id

    if teacher_name:
        teacher = Teacher.get_or_none(teacher_name)
        if teacher is None:
            bot_error("INVALID_TEACHER", teacher=teacher_name)

        invite_data["tei"] = teacher.id

    invite_data["iid"] = Invite.create(created_by=user).id
    code = jwt.encode(invite_data, config.JWT_KEY)
    link = f"https://t.me/nkrp_bot?start={code}"

    img = qrcode.make(link)
    fp = io.BytesIO()
    img.save(fp, format="PNG")
    fp.seek(0)

    return InputFile(fp, "qrcode.png"), link


async def cmd_start(message: aiogram.types.Message):
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


async def cmd_help(message: aiogram.types.Message):
    user = User.from_telegram(message.from_user)
    await send_help(message, user)


invite_cb = CallbackData("invite", "action", "group", "teacher", "is_admin")


def make_invite_message(user, group=None, teacher=None, is_admin=False):
    kwargs = dict(group=group, teacher=teacher, is_admin=is_admin)

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Группа", callback_data=invite_cb.new("set_group", **kwargs)),
           InlineKeyboardButton("Преподаватель", callback_data=invite_cb.new("set_teacher", **kwargs)))

    if user.is_admin:
        kb.add(InlineKeyboardButton("Сделать администратором",
                                    callback_data=invite_cb.new("set_admin", **kwargs)))

    kb.add(InlineKeyboardButton("Создать", callback_data=invite_cb.new("create", **kwargs)))

    text = ["Тип: "]
    if group:
        text += ["Студент\nГруппа: ", group]

    elif teacher:
        text += ["Преподаватель\nФИО: ", teacher]
    else:
        text.append("Не указан")

    if is_admin:
        text.append("\nПользователь СТАНЕТ администратором")

    return ''.join(text), kb


async def cmd_invite(message: aiogram.types.Message):
    user = User.from_telegram(message.from_user)
    args = message.get_args().split()

    if args:
        args = dict(((*i.split('=', 1), "true")[:2] for i in args))
        file, link = create_invite(user, args.get("group"), args.get("teacher"),
                                   args.get("admin", "false").lower() != "false")
        await message.answer_photo(file, link)

    else:
        text, kb = make_invite_message(user)
        await message.answer(text, reply_markup=kb)


async def cc_invite_set_admin(call: aiogram.types.CallbackQuery, callback_data):
    user = User.from_telegram(call.from_user)
    text, kb = make_invite_message(user, callback_data["group"], callback_data["teacher"],
                                   not callback_data["is_admin"])
    await call.answer()
    await call.message.edit_text(text, reply_markup=kb)


async def cc_invite_set_group(call: aiogram.types.CallbackQuery, callback_data):
    await call.answer()
    await call.message.answer("cc_invite_set_group")


async def cc_invite_set_teacher(call: aiogram.types.CallbackQuery, callback_data):
    await call.answer()
    await call.message.answer("cc_invite_set_teacher")


async def cc_invite_create(call: aiogram.types.CallbackQuery, callback_data):
    user = User.from_telegram(call.from_user)
    file, link = create_invite(user, callback_data["group"], callback_data["teacher"], callback_data["is_admin"])

    await call.answer()
    await call.message.answer_photo(file, link)


def install_help_invite(dp):
    dp.register_message_handler(cmd_start, commands="start")
    dp.register_message_handler(cmd_help, commands="help")
    dp.register_message_handler(cmd_invite, commands="invite")
    dp.register_callback_query_handler(cc_invite_set_admin, invite_cb.filter(action="set_admin"))
    dp.register_callback_query_handler(cc_invite_set_group, invite_cb.filter(action="set_group"))
    dp.register_callback_query_handler(cc_invite_set_teacher, invite_cb.filter(action="set_teacher"))
    dp.register_callback_query_handler(cc_invite_create, invite_cb.filter(action="create"))
