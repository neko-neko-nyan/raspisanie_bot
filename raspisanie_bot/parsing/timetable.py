import dataclasses
import datetime
import logging
import re
import typing

import dateparser

from .common import normalize_text, parse_pair_number, parse_group_name, GroupName
from ..database import PairNameFix

NORM_AUD_RE = re.compile('\\W+')
DATE_DATA_PARSER = dateparser.DateDataParser(languages=['ru'], region='RU', settings={
    'PREFER_DAY_OF_MONTH': 'first',
    'PREFER_DATES_FROM': 'future',
    'PARSERS': ['absolute-time']
})
_LOG = logging.getLogger('parsing')


@dataclasses.dataclass
class PairInfo:
    name: str = None
    teachers: list = dataclasses.field(default_factory=list)
    cabinets: list = dataclasses.field(default_factory=list)
    is_substitution: bool = False
    subgroup: str = None
    raw: str = None


def parse_pair_name(s) -> typing.Optional[PairInfo]:
    array = NORM_AUD_RE.sub(' ', s).strip().split()
    if not array:
        return None

    result = PairInfo()
    result.raw = normalize_text(s)
    l_array = [i.lower() for i in array]

    if 'зам' in l_array:
        index = l_array.index('зам')
        del array[index]
        del l_array[index]

        result.is_substitution = True

    if 'ауд' in l_array:
        index = l_array.index('ауд')
        del array[index]
        del l_array[index]

        while index < len(array):
            try:
                result.cabinets.append(int(array[index]))
            except ValueError:
                break

            del array[index]
            del l_array[index]

    if 'гр' in l_array:
        index = l_array.index('гр')
        if index > 1 and l_array[index - 1] == 'п':
            try:
                result.subgroup = int(array[index - 2])
            except ValueError:
                pass
            else:
                del array[index]
                del array[index - 1]
                del array[index - 2]

        elif index > 0 and l_array[index - 1][-1] == 'п':
            try:
                result.subgroup = int(array[index - 1][:-1])
            except ValueError:
                pass
            else:
                del array[index]
                del array[index - 1]

    index = 2
    while index < len(array):
        if len(array[index]) == 1 and len(array[index - 1]) == 1:
            result.teachers.append((array[index - 2], array[index - 1], array[index]))
            del array[index]
            del array[index - 1]
            del array[index - 2]
        else:
            index += 1

    result.name = ' '.join(array)
    if result.name.startswith('МДК'):
        result.name = 'МДК.' + '.'.join(result.name.removeprefix('МДК').strip().split())

    fix = PairNameFix.get_or_none(PairNameFix.prev_name == result.name.lower())
    if fix is not None:
        result.name = fix.new_name

    return result


def parse_date(date: str) -> typing.Optional[datetime.date]:
    date = date.lower().replace('знаменатель', '').replace('числитель', '')

    res = DATE_DATA_PARSER.get_date_data(date).date_obj
    if res is None:
        return None

    return res.date()


def parse_table(table) -> typing.Dict[GroupName, typing.Dict[int, PairInfo]]:
    timetable = []

    if table[0].tag == 'tbody':
        table = table[0]

    for gn in table[0][1:]:
        group = parse_group_name(gn.text_content())
        timetable.append((group, {}))

    last_pn = 0

    for tr in table[1:]:
        pn = parse_pair_number(tr[0].text_content(), last_pn + 1)
        last_pn = pn

        for gi, td in enumerate(tr[1:]):
            pt = parse_pair_name(td.text_content())
            if pt:
                timetable[gi][1][pn] = pt

    return dict(timetable)


def parse_timetable(page) -> typing.Tuple[datetime.date, typing.Dict[str, str],
                                          typing.Dict[GroupName, typing.Dict[int, PairInfo]]]:
    useful_links = {}
    today = set()
    timetable = {}

    for i in page.body[0]:
        if i.tag == 'p':
            link = i.find('.//a')
            if link is not None:
                link = link.attrib['href']

            text = normalize_text(i.text_content())
            if link:
                useful_links[text] = link
            elif text:
                date = parse_date(text)
                if date is not None:
                    today.add(date)

        elif i.tag == 'div':
            timetable.update(parse_table(i[0]))

        elif i.tag == 'table':
            timetable.update(parse_table(i))

        elif i.tag == 'font':
            continue

        else:
            _LOG.warning("Unhandled element in timetable: %r (text=%r)", i.tag, i.text_content())

    if not today:
        today.add(datetime.date.today())

    if len(today) > 1:
        _LOG.warning("Different dates in timetable: %s (first is used)", ', '.join((repr(i) for i in today)))

    today = today.pop()

    return today, useful_links, timetable
