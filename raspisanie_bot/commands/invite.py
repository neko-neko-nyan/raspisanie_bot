import io

import aiogram
import jwt
import qrcode
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from aiogram.utils.callback_data import CallbackData

from raspisanie_bot import config
from raspisanie_bot.bot_errors import bot_error
from raspisanie_bot.bot_utils import get_group_or_bot_error, get_teacher_or_bot_error
from raspisanie_bot.database import Invite, User, Group, Teacher


def create_invite(user, data=None, user_data=None):
    data = data or {}
    user_data = user_data or {}

    invite_data = {}

    if user_data.get("admin", "false").lower() != "false" or data.get("isa"):
        if not user.is_admin:
            bot_error("NOT_ADMIN", user=user.tg_id)

        invite_data["isa"] = True

    if "group" in user_data:
        group = get_group_or_bot_error(user, user_data["group"])
        invite_data["gri"] = group.id

    if "gri" in data:
        invite_data["gri"] = data["gri"]

    if "teacher" in user_data:
        teacher = get_teacher_or_bot_error(user, user_data["teacher"])
        invite_data["tei"] = teacher.id

    if "tei" in data:
        invite_data["tei"] = data["tei"]

    invite_data["iid"] = Invite.create(created_by=user).id
    code = jwt.encode(invite_data, config.JWT_KEY)
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
        kb.add(InlineKeyboardButton("Сделать администратором", callback_data=invite_cb.new("set_admin")))

    kb.add(InlineKeyboardButton("Создать", callback_data=invite_cb.new("create")))

    text = ["Тип: "]
    if "gri" in data:
        group = Group.get_by_id(data["gri"])
        text += ["Студенты\nГруппа: ", group.string_value]

    elif "tei" in data:
        teacher = Teacher.get_by_id(data["tei"])
        text += ["Преподаватель\nФИО: ", teacher.full_name]
    else:
        text.append("Не указан")

    if data.get("isa"):
        text.append("\nПользователь СТАНЕТ администратором")

    return ''.join(text), kb


async def cmd_invite(message: aiogram.types.Message, state: FSMContext):
    user = User.from_telegram(message.from_user)
    args = message.get_args().split()

    if args:
        args = dict(((*i.split('=', 1), "true")[:2] for i in args))
        file, link = create_invite(user, user_data=args)
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
        bot_error("NOT_ADMIN", user=user.tg_id)

    async with state.proxy() as st:
        st["isa"] = not st.get("isa", False)

        data = dict(st)

    text, kb = make_invite_message(user, data)
    await call.bot.edit_message_text(text, call.message.chat.id, data["msg_id"], reply_markup=kb)
    await call.answer()


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

        st["gri"] = group.id
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

        st["tei"] = teacher.id
        st.state = InviteStates.waiting_for_user_action

        data = dict(st)

    text, kb = make_invite_message(user, data)
    await message.bot.edit_message_text(text, message.chat.id, data["msg_id"], reply_markup=kb)


async def cc_invite_create(call: aiogram.types.CallbackQuery, state: FSMContext):
    user = User.from_telegram(call.from_user)

    async with state.proxy() as st:
        data = dict(st)

    file, link = create_invite(user, data)
    await call.message.answer_photo(file, link)

    await call.bot.delete_message(call.message.chat.id, data["msg_id"])
    await call.answer()
    await state.finish()


def install_invite(dp):
    dp.register_message_handler(cmd_invite, commands="invite", state='*')
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
