import aiogram
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.callback_data import CallbackData

from raspisanie_bot import parse_group_name
from raspisanie_bot.bot_errors import bot_error
from raspisanie_bot.database import User, Group, Teacher

settings_cb = CallbackData("settings", "action")


async def cmd_settings(message: aiogram.types.Message, state: FSMContext):
    user = User.from_telegram(message.from_user)

    kb = InlineKeyboardMarkup()

    kb.add(InlineKeyboardButton("Группа", callback_data=settings_cb.new("set_group")),
           InlineKeyboardButton("Преподаватель", callback_data=settings_cb.new("set_teacher")))

    kb.add(InlineKeyboardButton("Уведомления", callback_data=settings_cb.new("notifications")))

    text = ["Тип: "]
    if user.group:
        text += ["Студент\nГруппа: ", user.group.string_value]

    elif user.teacher:
        text += ["Преподаватель\nФИО: ", user.teacher.short_name]

    else:
        text.append("Не указан")

    await message.answer(''.join(text), reply_markup=kb)
    await state.reset_state()


class Settings(StatesGroup):
    waiting_for_group = State()
    waiting_for_teacher = State()


async def cc_settings_set_group_teacher(call: aiogram.types.CallbackQuery, callback_data):
    if callback_data["action"] == "set_group":
        await call.message.edit_text("Отправьте номер группы")
        await Settings.waiting_for_group.set()
    else:
        await call.message.edit_text("Отправьте Ваше ФИО")
        await Settings.waiting_for_teacher.set()

    await call.answer()


async def msg_settings_set_group(message: aiogram.types.Message, state: FSMContext):
    user = User.from_telegram(message.from_user)

    group = parse_group_name(message.text, only_if_matches=True)
    if group is None:
        bot_error("INVALID_GROUP", user=user.tg_id, group=message.text)

    group = Group.get_or_none(Group.course == group.course, Group.group == group.group,
                              Group.subgroup == group.subgroup)
    if group is None:
        bot_error("INVALID_GROUP", user=user.tg_id, group=message.text)

    user.teacher = None
    user.group = group
    user.save()
    await message.answer("Группа успешно изменена")
    await state.finish()


async def msg_settings_set_teacher(message: aiogram.types.Message, state: FSMContext):
    user = User.from_telegram(message.from_user)

    teacher = Teacher.get_or_none(Teacher.surname == message.text)
    # TODO: search teacher
    if teacher is None:
        bot_error("INVALID_TEACHER", user=user.tg_id, teacher=message.text)

    user.group = None
    user.teacher = teacher
    user.save()
    await message.answer("Сохранено успешно")
    await state.finish()


async def cc_settings_notifications(call: aiogram.types.CallbackQuery, callback_data):
    await call.answer("В разработке (cc_settings_notifications)", show_alert=True)


def install_settings(dp):
    dp.register_message_handler(cmd_settings, commands="settings", state='*')
    dp.register_callback_query_handler(cc_settings_set_group_teacher,
                                       settings_cb.filter(action=["set_group", "set_teacher"]))
    dp.register_message_handler(msg_settings_set_group, state=Settings.waiting_for_group)
    dp.register_message_handler(msg_settings_set_teacher, state=Settings.waiting_for_teacher)
    dp.register_callback_query_handler(cc_settings_notifications, settings_cb.filter(action=["notifications"]))
