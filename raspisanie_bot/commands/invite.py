import io

import aiogram
import qrcode
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from aiogram.utils.callback_data import CallbackData

from ..bot_errors import bot_error
from ..bot_utils import get_group_or_bot_error, get_teacher_or_bot_error
from ..message_builder import MessageBuilder
from ..config import INVITE_SIGN_KEY
from ..database import Invite, User, Group, Teacher
from ..encoded_invite import encode_invite


def create_invite(user, data):
    set_admin = data.get("isa", False)
    if set_admin and not user.is_admin:
        bot_error("NOT_ADMIN", user=user)

    invite = Invite.create(set_group=data.get("gri"), set_teacher=data.get("tei"), set_admin=set_admin)
    code = encode_invite(INVITE_SIGN_KEY, invite.rowid)
    link = f"https://t.me/nkrp_bot?start={code}"

    img = qrcode.make(link)
    fp = io.BytesIO()
    img.save(fp, format="PNG")
    fp.seek(0)

    return InputFile(fp, "qrcode.png"), link


class InviteStates(StatesGroup):
    waiting_for_user_action = State()
    waiting_for_group = State()
    waiting_for_teacher = State()


invite_cb = CallbackData("invite", "action")


def make_invite_message(user, data=None):
    if data is None:
        data = {}

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Студенты", callback_data=invite_cb.new("set_group")),
           InlineKeyboardButton("Преподаватель", callback_data=invite_cb.new("set_teacher")))

    if user.is_admin:
        if data.get("isa"):
            text = "Не делать администратором"
        else:
            text = "Сделать администратором"

        kb.add(InlineKeyboardButton(text, callback_data=invite_cb.new("set_admin")))

    kb.add(InlineKeyboardButton("Создать", callback_data=invite_cb.new("create")))

    res = MessageBuilder().text("Приглашение позволяет указать настройки прямо в ссылке. У всех людей, активировавших"
                                " бота по ней, будут указанные здесь настройки.\nТип: ")
    if "gri" in data:
        group = Group.get_by_id(data["gri"])
        res.text("Студенты\nГруппа: ", group.string_value)

    elif "tei" in data:
        teacher = Teacher.get_by_id(data["tei"])
        res.text("Преподаватель\nФИО: ", teacher.full_name)
    else:
        res.text("Не указан")

    if data.get("isa"):
        res.text("\nПользователь *СТАНЕТ* администратором", escape=False)

    return str(res), kb


async def cmd_invite(message: aiogram.types.Message, state: FSMContext):
    user = User.from_telegram(message.from_user)
    args = message.get_args().split()

    if args:
        args = dict(((*i.split('=', 1), "true")[:2] for i in args))
        data = {}
        if args.get("admin", "false").lower() != "false":
            data["isa"] = True

        if "group" in args:
            data["gri"] = get_group_or_bot_error(user, args["group"]).rowid

        if "teacher" in args:
            data["tei"] = get_teacher_or_bot_error(user, args["teacher"]).rowid

        file, link = create_invite(user, data)
        await message.answer_photo(file, link)
        await state.reset_state()

    else:
        text, kb = make_invite_message(user)
        msg = await message.answer(text, reply_markup=kb)
        async with state.proxy() as st:
            st["msg_id"] = msg.message_id

            st.state = InviteStates.waiting_for_user_action


async def cc_invite_set_admin(call: aiogram.types.CallbackQuery, state: FSMContext):
    user = User.from_telegram(call.from_user)

    if not user.is_admin:
        bot_error("NOT_ADMIN", user=user)

    async with state.proxy() as st:
        st["isa"] = not st.get("isa", False)

        data = dict(st)

    text, kb = make_invite_message(user, data)
    await call.bot.edit_message_text(text, call.message.chat.id, data["msg_id"], reply_markup=kb)

    if data["isa"]:
        text = "Пользоваель станет администратором"
    else:
        text = "Пользоваель не станет администратором"

    await call.answer(text)


async def cc_invite_set_group(call: aiogram.types.CallbackQuery):
    await call.message.answer("Отправьте номер группы")
    await InviteStates.waiting_for_group.set()
    await call.answer()


async def cc_invite_set_teacher(call: aiogram.types.CallbackQuery):
    await call.message.answer("Отправьте ФИО преподавтеля")
    await InviteStates.waiting_for_teacher.set()
    await call.answer()


async def msg_invite_set_group(message: aiogram.types.Message, state: FSMContext):
    user = User.from_telegram(message.from_user)
    group = get_group_or_bot_error(user, message.text)

    async with state.proxy() as st:
        if "tei" in st:
            del st["tei"]

        st["gri"] = group.rowid
        st.state = InviteStates.waiting_for_user_action

        data = dict(st)

    text, kb = make_invite_message(user, data)
    await message.bot.edit_message_text(text, message.chat.id, data["msg_id"], reply_markup=kb)


async def msg_invite_set_teacher(message: aiogram.types.Message, state: FSMContext):
    user = User.from_telegram(message.from_user)
    teacher = get_teacher_or_bot_error(user, message.text)

    async with state.proxy() as st:
        if "gri" in st:
            del st["gri"]

        st["tei"] = teacher.rowid
        st.state = InviteStates.waiting_for_user_action

        data = dict(st)

    text, kb = make_invite_message(user, data)
    await message.bot.edit_message_text(text, message.chat.id, data["msg_id"], reply_markup=kb)


async def cc_invite_create(call: aiogram.types.CallbackQuery, state: FSMContext):
    user = User.from_telegram(call.from_user)

    async with state.proxy() as st:
        data = dict(st)

    file, link = create_invite(user, data)
    await call.message.answer_photo(file, link, parse_mode="")

    await call.bot.delete_message(call.message.chat.id, data["msg_id"])
    await call.answer()
    await state.finish()


def install_invite(dp, all_commands):
    dp.register_message_handler(cmd_invite, commands="invite", state='*')
    all_commands.append(aiogram.types.BotCommand("/invite", "Создать ссылку-приглашение"))

    dp.register_callback_query_handler(cc_invite_set_admin, invite_cb.filter(action="set_admin"),
                                       state=InviteStates.waiting_for_user_action)
    dp.register_callback_query_handler(cc_invite_set_group, invite_cb.filter(action="set_group"),
                                       state=InviteStates.waiting_for_user_action)
    dp.register_callback_query_handler(cc_invite_set_teacher, invite_cb.filter(action="set_teacher"),
                                       state=InviteStates.waiting_for_user_action)
    dp.register_message_handler(msg_invite_set_group, state=InviteStates.waiting_for_group)
    dp.register_message_handler(msg_invite_set_teacher, state=InviteStates.waiting_for_teacher)
    dp.register_callback_query_handler(cc_invite_create, invite_cb.filter(action="create"),
                                       state=InviteStates.waiting_for_user_action)
