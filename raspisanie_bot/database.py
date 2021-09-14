import datetime
import pathlib

from peewee import *


db = SqliteDatabase(pathlib.Path(__file__).parent.parent / "database.sqlite")


class BaseModel(Model):
    class Meta:
        database = db
        legacy_table_names = False


class Teacher(BaseModel):
    id = AutoField()

    surname = CharField(max_length=64)
    name = CharField(max_length=64)
    patronymic = CharField(max_length=64)


class Group(BaseModel):
    id = AutoField()
    owner = ForeignKeyField(Teacher)

    course = IntegerField()
    group = CharField(max_length=8)
    subgroup = IntegerField()


class Cabinet(BaseModel):
    id = AutoField()
    owner = ForeignKeyField(Teacher)

    number = IntegerField()
    floor = IntegerField()


class PairTime(BaseModel):
    pair_number = IntegerField()
    date = DateField()

    start_time = IntegerField()
    end_time = IntegerField()


class Pair(BaseModel):
    time = ForeignKeyField(PairTime)
    group = ForeignKeyField(Group)

    name = CharField(max_length=128)
    teachers = ManyToManyField(Teacher)
    cabinets = ManyToManyField(Cabinet)


class User(BaseModel):
    tg_id = IntegerField(primary_key=True)

    group = ForeignKeyField(Group, null=True)
    teacher = ForeignKeyField(Teacher, null=True)

    first_activity = DateTimeField(default=datetime.datetime.now)
    last_activity = DateTimeField(default=datetime.datetime.now)

    notification_flags = BitField()

    notify_new_timetable = notification_flags.flag()
    notify_timetable_changes = notification_flags.flag()

    notify_first_pair_start = notification_flags.flag()
    notify_pair_start = notification_flags.flag()
    notify_first_pair_end = notification_flags.flag()
    notify_pair_end = notification_flags.flag()

    notify_new_cvp = notification_flags.flag()
    notify_cvp_changes = notification_flags.flag()

    notify_cvp_start = notification_flags.flag()
    notify_cvp_end = notification_flags.flag()

    pre_pair_start_time = IntegerField(default=0)
    pre_cvp_start_time = IntegerField(default=0)


class Settings(BaseModel):
    name = CharField(64, primary_key=True)
    value = BareField(null=True)


class PairNameFix(BaseModel):
    prev_name = CharField(64, primary_key=True)
    new_name = CharField(64)


db.create_tables((Teacher, Group, Cabinet, PairTime, Pair, User, Settings, PairNameFix, Pair.teachers.through_model,
                  Pair.cabinets.through_model))
