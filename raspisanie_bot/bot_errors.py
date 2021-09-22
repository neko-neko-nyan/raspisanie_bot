import aiogram
import jwt
from aiogram.utils.markdown import escape_md

from . import config
from .encoded_invite import InviteSignatureError

ERRORS = {
    "UNKNOWN_ERROR": [0, "Произошла ошибка во время обработки ошибки. Сообщите об этом администратору."],
    "NOT_CONFIGURED": [1, "Вы не указали группу / ФИО. Команда /settings должна помочь вам."],
    "NOT_ADMIN": [2, "Для выполнения этого действия нужно быть администратором."],

    "INVALID_GROUP": [3, "Такой группы не найдено."],
    "INVALID_TEACHER": [4, "Такого преподавателя не найдено."],
    "NOT_FOUND": [5, "По Вашему запросу ничего не найдено."],

    "INVITE_KEY": [10, "Это приглашение содержит ошибку."],
    "INVITE_NOT_EXIST": [11, "Это приглашение недействительно."],
    "INVITE_ANOTHER_USED": [12, "Вы уже использовали код приглашения однажды. Чтобы использовать другой код надо чтобы"
                                " администратор сбросил настройки вашей учетой записи."],
    "INVITE_REVOKED": [13, "Это приглашение было отозвано."],
    "INVITE_USED": [14, "Это одноразовое приглашение уже было использовано."],
}


class BotError(Exception):
    def __init__(self, name, exception, **data):
        self.name = name
        self.exception = exception
        self.data = data


def bot_error(name, exception: BaseException = None, **data):
    raise BotError(name, exception, **data)


def format_error(name, exception: BaseException = None, **data):
    error = ERRORS.get(name)
    if error is None:
        error = ERRORS["UNKNOWN_ERROR"]
        data["error_name"] = name

    if not config.ENABLE_DEBUG_DATA:
        return escape_md(error[1])

    if exception is not None:
        data["exc_type"] = type(exception).__name__
        data["exc_args"] = list(exception.args)

    data["error_code"] = error[0]
    data = jwt.encode(data, config.JWT_KEY)
    return f"{escape_md(error[1])}\n```\nКод ошибки: {error[0]}\nДанные для разработчиков: {escape_md(data)}\n```\n"


async def handle_invite_signature_error(update: aiogram.types.Update, exception: InviteSignatureError):
    message = update.message or update.edited_message
    if not message:
        if update.callback_query:
            message = update.callback_query.message
        else:
            return False

    await message.answer(format_error("INVITE_KEY", exception), parse_mode="MarkdownV2")
    return True


async def handle_bot_error(update: aiogram.types.Update, exception: BotError):
    message = update.message or update.edited_message
    if not message:
        if update.callback_query:
            message = update.callback_query.message
        else:
            return False

    await message.answer(format_error(exception.name, exception.exception, **exception.data), parse_mode="MarkdownV2")
    return True


def install_error_handlers(dp):
    dp.register_errors_handler(handle_invite_signature_error, exception=InviteSignatureError)
    dp.register_errors_handler(handle_bot_error, exception=BotError)
