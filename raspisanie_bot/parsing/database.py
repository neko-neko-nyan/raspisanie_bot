import datetime

from .parsers import Finder, Handler, SubpagesParsingHandler
from ..config import feature_enabled
from ..database import Cabinet, Teacher, Group, PairNameFix, Pair, PairTime, CVPItem


class DatabaseFinder(Finder):
    __slots__ = ()

    def find_cabinet(self, text):
        number = super().find_cabinet(text)
        if number is None:
            return None

        if feature_enabled("create_missing_persist"):
            return Cabinet.get_or_create(rowid=number, floor=number // 100, name="")[0]
        return Cabinet.get_or_none(Cabinet.rowid == number)

    def find_teacher(self, surname, name, patronymic):
        surname, name, patronymic = super().find_teacher(surname, name, patronymic)
        surname = surname.capitalize()
        name = name.capitalize()
        patronymic = patronymic.capitalize()

        if feature_enabled("create_missing_persist"):
            return Teacher.get_or_create(surname=surname, name=name, patronymic=patronymic)[0]
        return Teacher.get_or_none(Teacher.surname == surname, Teacher.name.startswith(name),
                                   Teacher.patronymic.startswith(patronymic))

    def find_group(self, text):
        group = super().find_group(text)
        if group is None:
            return None

        if feature_enabled("create_missing_persist"):
            return Group.get_or_create(course=group.course, group=group.group, subgroup=group.subgroup)[0]
        return Group.get_or_none(Group.course == group.course, Group.group == group.group,
                                 Group.subgroup == group.subgroup)

    def find_pair(self, text):
        text = super().find_pair(text)

        fix = PairNameFix.get_or_none(PairNameFix.prev_name == text)
        if fix:
            return fix.new_name

        return text


class DatabaseHandler(Handler):
    __slots__ = ()

    def handle_new_cvp_date(self, date):
        super().handle_new_cvp_date(date)
        CVPItem.delete().where(CVPItem.date == date).execute()

        if feature_enabled("remove_old_data"):
            CVPItem.delete().where(CVPItem.date < datetime.date.today()).execute()

    def handle_cvp_item(self, date, group, start, end):
        super().handle_cvp_item(date, group, start, end)
        CVPItem.create(date=date, group=group, start_time=start, end_time=end)

    def handle_new_call_schedule(self):
        super().handle_new_call_schedule()
        PairTime.delete().execute()

    def handle_pair_time(self, pair, start, end):
        super().handle_pair_time(pair, start, end)
        PairTime.create(pair_number=pair, start_time=start, end_time=end)

    def handle_new_date(self, new_date, old_date):
        super().handle_new_date(new_date, old_date)

        if old_date is None:
            Pair.delete().where(Pair.date == new_date).execute()

            if feature_enabled("remove_old_data"):
                Pair.delete().where(Pair.date < datetime.date.today()).execute()

    def handle_parsed_pair(self, date, group, pair_number, pair, teachers, cabinets, subgroup, is_substitution):
        super().handle_parsed_pair(date, group, pair_number, pair, teachers, cabinets, subgroup, is_substitution)

        pair = Pair(date=date, pair_number=pair_number, group=group, name=pair)
        pair.save()

        try:
            pair.teachers.add(teachers)
        except peewee.IntegrityError:
            pass

        try:
            pair.cabinets.add(cabinets)
        except peewee.IntegrityError:
            pass


class UniversalHandler(DatabaseHandler, SubpagesParsingHandler):
    __slots__ = ()
