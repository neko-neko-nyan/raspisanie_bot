import dataclasses
import re

from .common import normalize_text, parse_pair_number, parse_group_name

NORM_AUD_RE = re.compile('\\W+')


@dataclasses.dataclass
class PairInfo:
    name: str = None
    teachers: list = dataclasses.field(default_factory=list)
    cabinets: list = dataclasses.field(default_factory=list)
    is_substitution: bool = False
    subgroup: str = None
    raw: str = None


def parse_pair_name(s):
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
    return result


def parse_date(date: str):
    date = date.lower()

    if 'знаменатель' in date:
        date = date.replace('знаменатель', '')
        week = 1
    elif 'числитель' in date:
        date = date.replace('числитель', '')
        week = 0
    else:
        week = -1

    weekday = -1
    for i, s in enumerate(['понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота', 'воскресение']):
        if s in date:
            date = date.replace(s, '')
            weekday = i

    date = date.replace(',', ' ').strip()
    return date, weekday, week


def parse_table(table):
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


def parse_timetable(page):
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
                today.add(parse_date(text))

        elif i.tag == 'div':
            timetable.update(parse_table(i[0]))

        elif i.tag == 'table':
            timetable.update(parse_table(i))

        elif i.tag == 'font':
            continue

        else:
            print(i)

    if not today:
        today.add('Unknown date')

    if len(today) > 1:
        print("Warning: different dates")

    today = today.pop()

    return today, useful_links, timetable
