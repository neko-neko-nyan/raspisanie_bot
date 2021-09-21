import re

import peewee

from raspisanie_bot import parse_group_name
from raspisanie_bot.bot_errors import bot_error
from raspisanie_bot.database import Group, Teacher


def group_from_parsed(group):
    return Group.get_or_none(Group.course == group.course, Group.group == group.group,
                             Group.subgroup == group.subgroup)


def get_group_or_none(text):
    group = parse_group_name(text)
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


NOT_WORD_RE = re.compile('\\W+')


def get_teacher_or_none(text):
    text = NOT_WORD_RE.sub(' ', text).strip().split()

    s = Teacher.select()

    for i in text:
        j = i.capitalize()
        s = s.orwhere(Teacher.surname.contains(i), Teacher.surname.startswith(j))

    try:
        return s.get()
    except peewee.DoesNotExist:
        return None


def get_teacher_or_bot_error(user, text):
    teacher = get_teacher_or_none(text)
    if teacher is None:
        bot_error("INVALID_TEACHER", user=user.tg_id, teacher=text)

    return teacher
