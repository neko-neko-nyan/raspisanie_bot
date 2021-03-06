import aiogram
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.callback_data import CallbackData

from ..bot_utils import get_group_or_bot_error, get_teacher_or_bot_error
from ..message_builder import MessageBuilder
from ..database import User

settings_cb = CallbackData("settings", "action")


async def cmd_settings(message: aiogram.types.Message, state: FSMContext):
    user = User.from_telegram(message.from_user)

    kb = InlineKeyboardMarkup()

    kb.add(InlineKeyboardButton("Студент", callback_data=settings_cb.new("set_group")),
           InlineKeyboardButton("Преподаватель", callback_data=settings_cb.new("set_teacher")))

    res = MessageBuilder().text("Тип: ")
    if user.group:
        res.text("Студент\nГруппа: ", user.group.string_value)

    elif user.teacher:
        res.text("Преподаватель\nФИО: ", user.teacher.short_name)

    else:
        res.text("Не указан")

    if user.is_admin:
        res.text("\nВы являетесь администратором.")

    await message.answer(str(res), reply_markup=kb)
    await state.reset_state()


class SettingsStates(StatesGroup):
    waiting_for_group = State()
    waiting_for_teacher = State()


async def cc_settings_set_group_teacher(call: aiogram.types.CallbackQuery, callback_data):
    if callback_data["action"] == "set_group":
        await call.message.edit_text("Отправьте номер группы")
        await SettingsStates.waiting_for_group.set()
    else:
        await call.message.edit_text("Отправьте Ваше ФИО")
        await SettingsStates.waiting_for_teacher.set()

    await call.answer()


async def msg_settings_set_group(message: aiogram.types.Message, state: FSMContext):
    user = User.from_telegram(message.from_user)
    group = get_group_or_bot_error(user, message.text)

    user.teacher = None
    user.group = group
    user.save()
    await message.answer("Группа успешно изменена")
    await state.finish()


async def msg_settings_set_teacher(message: aiogram.types.Message, state: FSMContext):
    user = User.from_telegram(message.from_user)
    teacher = get_teacher_or_bot_error(user, message.text)

    user.group = None
    user.teacher = teacher
    user.save()
    await message.answer("Сохранено успешно")
    await state.finish()


def install_settings(dp, all_commands):
    dp.register_message_handler(cmd_settings, commands="settings", state='*')
    all_commands.append(aiogram.types.BotCommand("/settings", "Настройки"))

    dp.register_callback_query_handler(cc_settings_set_group_teacher,
                                       settings_cb.filter(action=["set_group", "set_teacher"]))
    dp.register_message_handler(msg_settings_set_group, state=SettingsStates.waiting_for_group)
    dp.register_message_handler(msg_settings_set_teacher, state=SettingsStates.waiting_for_teacher)
