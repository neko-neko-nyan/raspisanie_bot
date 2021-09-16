from raspisanie_bot import parse_group_name
from raspisanie_bot.bot_errors import bot_error
from raspisanie_bot.database import Group, Teacher


def get_group_or_none(text):
    group = parse_group_name(text, only_if_matches=True)
    if group is not None:
        group = Group.get_or_none(Group.course == group.course, Group.group == group.group,
                                  Group.subgroup == group.subgroup)

    return group


def get_group_or_bot_error(user, text):
    group = get_group_or_none(text)
    if group is None:
        bot_error("INVALID_GROUP", user=user.tg_id, group=text)

    return group


def get_teacher_or_none(text):
    # TODO: search teacher
    teacher = Teacher.get_or_none(Teacher.surname == text)
    return teacher


def get_teacher_or_bot_error(user, text):
    teacher = get_teacher_or_none(text)
    if teacher is None:
        bot_error("INVALID_TEACHER", user=user.tg_id, teacher=text)

    return teacher
