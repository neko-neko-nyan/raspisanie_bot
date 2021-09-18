from . import Finder, Handler, SubpagesParsingHandler
from ..database import Cabinet, Teacher, Group, PairNameFix, Pair, PairTime


class DatabaseFinder(Finder):
    __slots__ = ()

    def find_cabinet(self, text):
        number = super().find_cabinet(text)
        if number is None:
            return None

        # return Cabinet.get_or_none(Cabinet.number == number)
        return Cabinet.get_or_create(number=number, floor=number // 100, name="")[0]

    def find_teacher(self, surname, name, patronymic):
        surname, name, patronymic = super().find_teacher(surname, name, patronymic)
        surname = surname.capitalize()
        name = name.capitalize()
        patronymic = patronymic.capitalize()
        # return Teacher.get_or_none(Teacher.surname == surname,
        #                            Teacher.name.startswith(name),
        #                            Teacher.patronymic.startswith(patronymic))
        return Teacher.get_or_create(surname=surname, name=name, patronymic=patronymic)[0]

    def find_group(self, text):
        group = super().find_group(text)
        if group is None:
            return None

        # return Group.get_or_none(Group.course == group.course, Group.group == group.group,
        #                          Group.subgroup == group.subgroup)
        return Group.get_or_create(course=group.course, group=group.group, subgroup=group.subgroup)[0]

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
        print(f"CVP {date}")

    def handle_cvp_item(self, date, group, start, end):
        super().handle_cvp_item(date, group, start, end)
        print(f"CVP {date} {group} {start} {end}")

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

    def handle_parsed_pair(self, date, group, pair_number, pair, teachers, cabinets, subgroup, is_substitution):
        super().handle_parsed_pair(date, group, pair_number, pair, teachers, cabinets, subgroup, is_substitution)

        pair = Pair(date=date, pair_number=pair_number, group=group, name=pair)
        pair.save()
        pair.teachers.add(teachers)
        pair.cabinets.add(cabinets)


class UniversalHandler(DatabaseHandler, SubpagesParsingHandler):
    __slots__ = ()
