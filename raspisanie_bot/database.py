import datetime
import pathlib

from peewee import *
from playhouse.sqlite_ext import SqliteExtDatabase, RowIDField

from .config import config

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


# #################################################################################################################### #
#                                                                                                                      #
#                               Базовые неизменяемые компоненты: teacher, group, cabinet                               #
#                                                                                                                      #
# #################################################################################################################### #


class Teacher(BaseModel):
    rowid = RowIDField()

    surname = CharField(max_length=64)
    name = CharField(max_length=64)
    patronymic = CharField(max_length=64)

    @property
    def full_name(self):
        return f"{self.surname} {self.name} {self.patronymic}"

    @property
    def short_name(self):
        return f"{self.surname} {self.name[0]}. {self.patronymic[0]}."

    class Meta:
        indexes = (
            (('surname', 'name', 'patronymic'), True),
        )


class Group(BaseModel):
    rowid = RowIDField()

    course = IntegerField()
    group = CharField(max_length=8)
    subgroup = IntegerField()

    @property
    def string_value(self):
        if self.course == 0:
            return self.group.upper()

        return f"{self.course}-{self.group.upper()}-{self.subgroup}"

    class Meta:
        indexes = (
            (('course', 'group', 'subgroup'), True),
        )


class Cabinet(BaseModel):
    number = IntegerField(primary_key=True)


# #################################################################################################################### #
#                                                                                                                      #
#                             Базовые изменяемые компоненты через парсинг: pair, pair_time                             #
#                                                                                                                      #
# #################################################################################################################### #


class Pair(BaseModel):
    rowid = RowIDField()

    date = DateField()
    pair_number = IntegerField()
    group = ForeignKeyField(Group)

    name = CharField(max_length=128)
    teachers = ManyToManyField(Teacher, on_delete='CASCADE')
    cabinets = ManyToManyField(Cabinet, on_delete='CASCADE')

    class Meta:
        indexes = (
            (('date', 'pair_number', 'group'), True),
        )


class PairTime(BaseModel):
    pair_number = IntegerField(primary_key=True)
    start_time = IntegerField()
    end_time = IntegerField()

    @classmethod
    def current(cls):
        return cls.by_time(datetime.datetime.now())

    @classmethod
    def by_time(cls, curr_time):
        # in_pair, non_prev_pair
        curr_time = curr_time.hour * 60 + curr_time.minute

        try:
            pt = cls.select() \
                .where(curr_time < cls.end_time) \
                .order_by(cls.pair_number) \
                .get()
        except cls.DoesNotExist:
            return False, None

        return curr_time >= pt.start_time, pt

    @property
    def is_current(self):
        curr_time = datetime.datetime.now()
        curr_time = curr_time.hour * 60 + curr_time.minute
        return self.start_time <= curr_time < self.end_time

    @property
    def is_next(self):
        curr_time = datetime.datetime.now()
        curr_time = curr_time.hour * 60 + curr_time.minute
        return curr_time < self.start_time


# #################################################################################################################### #
#                                                                                                                      #
#                                         Расписание столовой (covid_pit.pdt)                                          #
#                                                                                                                      #
# #################################################################################################################### #


class CVPItem(BaseModel):
    rowid = RowIDField()

    date = DateField()
    group = ForeignKeyField(Group)
    start_time = IntegerField()
    end_time = IntegerField()


# #################################################################################################################### #
#                                                                                                                      #
#                                     Взаимодействие с пользователем: user, invite                                     #
#                                                                                                                      #
# #################################################################################################################### #


class User(BaseModel):
    rowid = RowIDField()

    is_admin = BooleanField(default=False)

    group = ForeignKeyField(Group, null=True)
    teacher = ForeignKeyField(Teacher, null=True)

    @classmethod
    def from_telegram(cls, telegram_user):
        user = User.get_or_none(User.rowid == telegram_user.id)
        if user is not None:
            user.save()
            return user

        count = User.select().count()
        return User.create(rowid=telegram_user.id, is_admin=count == 0)

    def is_configured(self):
        return self.group is not None or self.teacher is not None


class Invite(BaseModel):
    rowid = RowIDField()

    set_group = ForeignKeyField(Group, null=True)
    set_teacher = ForeignKeyField(Teacher, null=True)
    set_admin = BooleanField(default=False)


# #################################################################################################################### #
#                                                                                                                      #
#                                  Состояния telegram-бота: StorageState, StorageData                                  #
#                                                                                                                      #
# #################################################################################################################### #


class StorageState(BaseModel):
    id = CharField(64, primary_key=True)
    state = CharField(64, null=True)


class StorageData(BaseModel):
    id = CharField(64)
    key = CharField(64)
    value = BareField()

    class Meta:
        primary_key = CompositeKey('id', 'key')


DeferredForeignKey.resolve(Invite)
db.create_tables((
    Teacher, Group, Cabinet,
    Pair, Pair.teachers.through_model, Pair.cabinets.through_model, PairTime,
    CVPItem,
    User, Invite,
    StorageState, StorageData
))


def preload_persistent():
    from .parsing import parse_group_name

    cabinets = config.get("cabinets")
    if cabinets:
        Cabinet.insert_many(((i, ) for i in cabinets), fields=[Cabinet.number]).on_conflict_ignore().execute()

    groups = config.get("groups")
    if groups:
        Group.insert_many((parse_group_name(i) for i in groups), fields=[Group.course, Group.group, Group.subgroup])\
            .on_conflict_ignore().execute()

    teachers = config.get("teachers")
    if teachers:
        Teacher.insert_many(teachers, fields=[Teacher.surname, Teacher.name, Teacher.patronymic]).on_conflict_ignore()\
            .execute()
