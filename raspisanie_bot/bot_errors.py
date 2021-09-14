import aiogram
import jwt


ERROR_DATA_JWT_KEY = b"ERROR CODE"
ERRORS = {
    "UNKNOWN_ERROR": [0, "Произошла ошибка во время обработки ошибки. Сообщите об этом администратору."],
    "NOT_CONFIGURED": [1, "Вы не указали группу / ФИО. Команда /settings должна помочь вам."],
    "NOT_ADMIN": [2, "Для выполнения этого действия нужно быть администратором."],

    "INVALID_GROUP": [3, "Такой группы не найдено."],
    "INVALID_TEACHER": [4, "Такого преподавателя не найдено."],

    "JWT_ERROR": [10, "Это приглашение содержит ошибку или недействительно."],
    "ANOTHER_INVITE_USED": [11, "Вы уже использовали код приглашения однажды. Чтобы использовать другой код надо чтобы"
                                " администратор сбросил настройки вашей учетой записи."],
    "INVITE_USED": [12, "Это приглашение содержит ошибку или недействительно."],
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

    if exception is not None:
        data["exc_type"] = type(exception).__name__
        data["exc_args"] = list(exception.args)

    data["error_code"] = error[0]
    data = jwt.encode(data, ERROR_DATA_JWT_KEY)
    return error[1] + f" (код = {error[0]}, данные для разработчиков = {data})"


async def handle_jwt_error(update: aiogram.types.Update, exception: jwt.PyJWTError):
    message = update.message or update.edited_message
    if not message:
        if update.callback_query:
            message = update.callback_query.message
        else:
            return False

    await message.answer(format_error("JWT_ERROR", exception))
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
    dp.register_errors_handler(handle_jwt_error, exception=jwt.PyJWTError)
    dp.register_errors_handler(handle_bot_error, exception=BotError)
