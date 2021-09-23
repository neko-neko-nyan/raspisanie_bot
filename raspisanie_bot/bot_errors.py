import aiogram
import jwt

from .message_builder import MessageBuilder
from .config import feature_enabled, JWT_KEY_FOR_ERRORS
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
    data = {k: getattr(v, 'rowid', v) for k, v in data.items()}
    error = ERRORS.get(name)
    if error is None:
        error = ERRORS["UNKNOWN_ERROR"]
        data["error_name"] = name

    res = MessageBuilder()
    res.text(error[1])
    if not feature_enabled("debug_info"):
        return str(res)

    if exception is not None:
        data["exc_type"] = type(exception).__name__
        data["exc_args"] = list(exception.args)

    data["error_code"] = error[0]
    data = jwt.encode(data, JWT_KEY_FOR_ERRORS)
    res.nl().pre("Код ошибки: ", error[0], "\nДанные для разработчиков: ", data)
    return str(res)


async def handle_invite_signature_error(update: aiogram.types.Update, exception: InviteSignatureError):
    message = update.message or update.edited_message
    if not message:
        if update.callback_query:
            message = update.callback_query.message
        else:
            return False

    await message.answer(format_error("INVITE_KEY", exception))
    return True


async def handle_bot_error(update: aiogram.types.Update, exception: BotError):
    message = update.message or update.edited_message
    if not message:
        if update.callback_query:
            message = update.callback_query.message
        else:
            return False

    await message.answer(format_error(exception.name, exception.exception, **exception.data))
    return True


def install_error_handlers(dp):
    dp.register_errors_handler(handle_invite_signature_error, exception=InviteSignatureError)
    dp.register_errors_handler(handle_bot_error, exception=BotError)
