import datetime
import pathlib

from peewee import *
from playhouse.sqlite_ext import SqliteExtDatabase

db = SqliteExtDatabase(pathlib.Path(__file__).parent.parent / "database.sqlite", pragmas=(
    ('cache_size', -1024 * 64),  # 64MB page-cache.
    ('encoding', '\'UTF-8\''),
    ('foreign_keys', 1),  # Enforce foreign-key constraints.
    ('journal_mode', 'wal'),  # Use WAL-mode (you should always use this!).
))


class BaseModel(Model):
    class Meta:
        database = db
        legacy_table_names = False


class Teacher(BaseModel):
    id = AutoField()

    surname = CharField(max_length=64)
    name = CharField(max_length=64)
    patronymic = CharField(max_length=64)

    @property
    def full_name(self):
        return f"{self.surname} {self.name} {self.patronymic}".capitalize()

    @property
    def short_name(self):
        return f"{self.surname} {self.name[0]}. {self.patronymic[0]}.".capitalize()


class Group(BaseModel):
    id = AutoField()
    owner = ForeignKeyField(Teacher)

    course = IntegerField()
    group = CharField(max_length=8)
    subgroup = IntegerField()

    @property
    def string_value(self):
        if self.course == 0:
            return self.group.upper()

        return f"{self.course}-{self.group.upper()}-{self.subgroup}"


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

    invited_by = ForeignKeyField('self', null=True)
    invite = IntegerField(null=True)

    is_admin = BooleanField(default=False)

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

    @classmethod
    def from_telegram(cls, telegram_user):
        user = User.get_or_none(User.tg_id == telegram_user.id)
        if user is not None:
            user.last_activity = datetime.datetime.now()
            user.save()
            return user

        return User.create(tg_id=telegram_user.id)

    def is_configured(self):
        return self.group is not None or self.teacher is not None


class Invite(BaseModel):
    id = IntegerField(primary_key=True)
    created_by = ForeignKeyField(User)
    is_used = BooleanField(default=False)


class Settings(BaseModel):
    name = CharField(64, primary_key=True)
    value = BareField(null=True)


class PairNameFix(BaseModel):
    prev_name = CharField(64, primary_key=True)
    new_name = CharField(64)


class StorageState(BaseModel):
    id = CharField(64, primary_key=True)
    state = CharField(64, null=True)


class StorageData(BaseModel):
    id = CharField(64)
    key = CharField(64)
    value = BareField()

    class Meta:
        primary_key = CompositeKey('id', 'key')


db.create_tables((Teacher, Group, Cabinet, PairTime, Pair, User, Invite, Settings, PairNameFix, StorageState,
                  StorageData, Pair.teachers.through_model, Pair.cabinets.through_model))
