import peewee

from raspisanie_bot import parse_group_name
from raspisanie_bot.bot_errors import bot_error
from raspisanie_bot.database import Group, Teacher


def group_from_parsed(group):
    return Group.get_or_none(Group.course == group.course, Group.group == group.group,
                             Group.subgroup == group.subgroup)


def get_group_or_none(text):
    group = parse_group_name(text, only_if_matches=True)
    if group is not None:
        group = group_from_parsed(group)

    return group


def get_group_or_bot_error(user, text):
    group = get_group_or_none(text)
    if group is None:
        bot_error("INVALID_GROUP", user=user.tg_id, group=text)

    return group


def teacher_from_parsed(teacher):
    surname, n, p = teacher

    try:
        return Teacher.select().where(
            (Teacher.surname == surname).collate("NOCASE"),
            Teacher.name.startswith(n).collate("NOCASE"),
            Teacher.patronymic.startswith(p).collate("NOCASE")
        ).get()
    except peewee.DoesNotExist:
        pass


def get_teacher_or_none(text):
    # TODO: search teacher
    teacher = Teacher.get_or_none(Teacher.surname == text)
    return teacher


def get_teacher_or_bot_error(user, text):
    teacher = get_teacher_or_none(text)
    if teacher is None:
        bot_error("INVALID_TEACHER", user=user.tg_id, teacher=text)

    return teacher
