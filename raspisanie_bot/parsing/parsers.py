import collections
import hashlib
import io
import logging
import re

import aiohttp
import dateparser
# noinspection PyPackageRequirements
import pdfminer.converter
# noinspection PyPackageRequirements
import pdfminer.layout
# noinspection PyPackageRequirements
import pdfminer.pdfinterp
# noinspection PyPackageRequirements
import pdfminer.pdfpage
from lxml import html

from ..config import feature_enabled

GroupName = collections.namedtuple('GroupName', ('course', 'group', 'subgroup'))


class ParserBase:
    SPACES_RE = re.compile('\\s+')
    NOT_DIGITS_RE = re.compile('\\D+')
    GROUP_NAME_RE = re.compile('\\s*(\\d)\\s*-?\\s*([А-Я]{1,2})\\s*-?\\s*(\\d)\\s*', re.MULTILINE)
    TIME_PERIOD_RE = re.compile('\\s*с?\\s*(\\d+)[.,:](\\d+)\\s*(?:до|.)\\s*(\\d+)[.,:](\\d+)\\s*(.*)')

    NOT_WORD_RE = re.compile('\\W+')

    DATE_DATA_PARSER = dateparser.DateDataParser(languages=['ru'], region='RU', settings={
        'PREFER_DAY_OF_MONTH': 'first',
        'PREFER_DATES_FROM': 'future',
        'PARSERS': ['absolute-time']
    })

    def __init__(self, finder_class, handler_class):
        self.LOG = logging.getLogger(type(self).__name__)
        self.finder = finder_class(self)
        self.handler = handler_class(self)

    def normalize_text(self, text: str) -> str:
        return self.SPACES_RE.sub(' ', text).strip()

    def parse_pair_number(self, text: str) -> int:
        text = self.NOT_DIGITS_RE.sub('', text)

        try:
            return int(text)
        except ValueError:
            pass

    # noinspection PyMethodMayBeStatic
    def parse_group_name(self, text: str):
        return parse_group_name(text)

    def parse_time_period(self, text):
        match = self.TIME_PERIOD_RE.fullmatch(text)
        if match is None:
            return None, None, text

        start = int(match.group(1)) * 60 + int(match.group(2))
        end = int(match.group(3)) * 60 + int(match.group(4))
        return start, end, match.group(5)

    def parse_date(self, line):
        res = self.DATE_DATA_PARSER.get_date_data(line).date_obj
        if res is None:
            return None

        return res.date()

    # noinspection PyMethodMayBeStatic
    def parse_html(self, text):
        return html.fromstring(text)


class CallScheduleParser(ParserBase):
    def parse_call_schedule(self, text):
        self.parse_call_schedule_page(self.parse_html(text))

    def parse_call_schedule_page(self, page):
        table = page.find(".//div[@id = 'main']//table")

        if table[0].tag == 'tbody':
            table = table[0]

        self.handler.handle_new_call_schedule()

        for tr in table:
            col1 = tr[0].text_content()
            if col1.isspace():
                continue

            pn = self.parse_pair_number(col1)
            start, end, _ = self.parse_time_period(tr[1].text_content())
            if start is None:
                self.LOG.warning("Time re not matches: %r", tr[1].text_content())
            else:
                self.handler.handle_pair_time(pn, start, end)


class CVPParser(ParserBase):
    NORM_GROUPS_RE = re.compile('[^0-9а-яА-Я-]+')

    def parse_cvp(self, content: bytes):
        rsrcmgr = pdfminer.pdfinterp.PDFResourceManager()
        device = LinesConverter(rsrcmgr, self)
        interpreter = pdfminer.pdfinterp.PDFPageInterpreter(rsrcmgr, device)

        with io.BytesIO(content) as fp:
            for page in pdfminer.pdfpage.PDFPage.get_pages(fp):
                interpreter.process_page(page)

    def parse_groups_list(self, text):
        for group in self.NORM_GROUPS_RE.sub(' ', text).split():
            group = self.finder.find_group(group)
            if group is not None:
                yield group


class LinesConverter(pdfminer.converter.PDFLayoutAnalyzer):
    def __init__(self, rsrcmgr, parser):
        super().__init__(rsrcmgr, laparams=pdfminer.layout.LAParams())
        self.parser = parser
        self._text = []

    def receive_layout(self, ltpage):
        last_time = None
        date = None

        for child in ltpage:
            if not isinstance(child, pdfminer.layout.LTText):
                continue

            line = child.get_text().strip()
            if not line or line.isdigit():
                continue

            if line.startswith("на "):
                line = line.removeprefix("на").strip()
                date = self.parser.parse_date(line)
                self.parser.handler.handle_new_cvp_date(date)
                continue

            start, end, line = self.parser.parse_time_period(line)
            if start is not None:
                last_time = (start, end)

            if line and last_time is not None:
                for group in self.parser.parse_groups_list(line):
                    self.parser.handler.handle_cvp_item(date, group, *last_time)

    # Removed for optimization

    def begin_figure(self, name, bbox, matrix):
        pass

    def end_figure(self, _):
        pass

    def render_image(self, name, stream):
        pass

    def paint_path(self, gstate, stroke, fill, evenodd, path):
        pass


class TimetableParser(ParserBase):
    def parse_timetable(self, text):
        self.parse_timetable_page(self.parse_html(text))

    def parse_timetable_page(self, page):
        date = None

        for i in page.body[0]:
            if i.tag == 'p':
                link = i.find('.//a')
                if link is not None:
                    link = link.attrib['href']

                text = self.normalize_text(i.text_content())
                if link:
                    self.handler.handle_link(text, link)
                elif text:
                    new_date = self.parse_date(text.lower().replace('знаменатель', '').replace('числитель', ''))
                    if new_date is not None:
                        if new_date != date:
                            self.handler.handle_new_date(new_date, date)

                        date = new_date

            elif i.tag == 'div':
                self.parse_table(date, i[0])

            elif i.tag == 'table':
                self.parse_table(date, i)

            elif i.tag == 'font':
                continue

            else:
                self.LOG.warning("Unhandled element in timetable: %r (text=%r)", i.tag, i.text_content())

    def parse_table(self, date, table):
        if table[0].tag == 'tbody':
            table = table[0]

        skipped = {}  # pair_no -> [gi]
        groups = []
        for gn in table[0][1:]:
            groups.append(self.finder.find_group(gn.text_content()))

        for tr in table[1:]:
            pair = self.finder.find_pair_number(tr[0].text_content())
            skipped.setdefault(pair, [])
            if pair is None:
                continue

            curr_spans = 0
            next_common_pair = 0
            prev_text = None
            for gi, group in enumerate(groups):
                if gi in skipped[pair]:
                    curr_spans += 1
                    continue

                if next_common_pair:
                    next_common_pair -= 1
                    curr_spans += 1
                    if group is not None and prev_text is not None:
                        self.parse_pair(date, group, pair, prev_text)
                    continue

                if gi + 1 - curr_spans >= len(tr):
                    break
                td = tr[gi + 1 - curr_spans]

                if 'rowspan' in td.attrib:
                    for i in range(int(td.attrib['rowspan']) - 1):
                        skipped.setdefault(pair + i + 1, []).append(gi)

                if 'colspan' in td.attrib:
                    next_common_pair = int(td.attrib['colspan']) - 1

                if group is not None:
                    prev_text = td.text_content()
                    self.parse_pair(date, group, pair, prev_text)

    def parse_pair(self, date, group, pair_number, text):
        array = self.NOT_WORD_RE.sub(' ', text).strip().split()
        if not array:
            return None

        teachers = []
        cabinets = []
        subgroup = None
        is_substitution = False

        l_array = [i.lower() for i in array]

        if 'зам' in l_array:
            index = l_array.index('зам')
            del array[index]
            del l_array[index]

            is_substitution = True

        if 'ауд' in l_array:
            index = l_array.index('ауд')
            del array[index]
            del l_array[index]

            while index < len(array):
                cabinet = self.finder.find_cabinet(array[index])
                if cabinet is None:
                    index += 1
                    continue

                cabinets.append(cabinet)
                del array[index]
                del l_array[index]

        if 'гр' in l_array:
            index = l_array.index('гр')
            if index > 1 and l_array[index - 1] == 'п':
                try:
                    subgroup = int(array[index - 2])
                except ValueError:
                    pass
                else:
                    del array[index]
                    del array[index - 1]
                    del array[index - 2]

            elif index > 0 and l_array[index - 1][-1] == 'п':
                try:
                    subgroup = int(array[index - 1][:-1])
                except ValueError:
                    pass
                else:
                    del array[index]
                    del array[index - 1]

        index = 2
        while index < len(array):
            if len(array[index]) == 1 and len(array[index - 1]) == 1:
                teacher = self.finder.find_teacher(array[index - 2], array[index - 1], array[index])
                if teacher is None:
                    index += 1
                    continue

                teachers.append(teacher)
                del array[index]
                del array[index - 1]
                del array[index - 2]
            else:
                index += 1

        pair = self.finder.find_pair(' '.join(array))
        self.handler.handle_parsed_pair(date, group, pair_number, pair, teachers, cabinets, subgroup, is_substitution)


class AsyncParser(ParserBase):
    def __init__(self, finder_class, handler_class):
        super().__init__(finder_class, handler_class)
        self._sess = aiohttp.ClientSession()
        self._pending = set()

    def then(self, coro):
        self._pending.add(coro)

    async def process_pending(self):
        while self._pending:
            coro = self._pending.pop()
            await coro

    async def close(self):
        await self._sess.close()

    async def download_content(self, url):
        async with self._sess.get(url) as r:
            content = await r.read()
            encoding = r.get_encoding()

        return content, encoding

    async def download_bytes(self, url):
        async with self._sess.get(url) as r:
            return await r.read()

    async def download_text(self, url):
        async with self._sess.get(url) as r:
            return await r.text()


class TimetableUpdater(AsyncParser, TimetableParser, CallScheduleParser, CVPParser):
    def __init__(self, finder_class, handler_class):
        super().__init__(finder_class, handler_class)
        self._last_tt_md5 = None

    async def update_timetable(self, link, force=False):
        self.LOG.info("Updating timetable started")
        content, encoding = await self.download_content(link)

        md5 = hashlib.md5(content).digest()
        if self._last_tt_md5 == md5 and not force:
            self.LOG.info("Timetable not updated due to cache")
            return

        self.parse_timetable(content.decode(encoding))
        self._last_tt_md5 = md5

        self.LOG.info("Timetable updated successfully")

    async def update_cvp(self, link):
        self.LOG.info("Updating CVP started")
        self.parse_cvp(await self.download_bytes(link))
        self.LOG.info("CVP updated successfully")

    async def update_call_schedule(self, link):
        self.LOG.info("Updating call schedule started")
        self.parse_call_schedule(await self.download_text(link))
        self.LOG.info("Call schedule updated successfully")


class Finder:
    __slots__ = ('parser', )

    def __init__(self, parser):
        self.parser = parser

    def find_group(self, text):
        return self.parser.parse_group_name(text)

    def find_pair_number(self, text):
        return self.parser.parse_pair_number(text)

    def find_cabinet(self, text):
        try:
            return int(text)
        except ValueError:
            return None

    def find_teacher(self, surname, name, patronymic):
        return surname, name, patronymic

    def find_pair(self, text):
        if text.startswith('МДК'):
            return 'МДК.' + '.'.join(text.removeprefix('МДК').strip().split())

        if text.startswith('МИДК'):
            return 'МИДК.' + '.'.join(text.removeprefix('МИДК').strip().split())

        return text


class Handler:
    __slots__ = ('parser', )

    def __init__(self, parser):
        self.parser = parser

    def handle_link(self, name, link):
        name = name.lower()
        if name == "график питания студентов в столовой":
            self.handle_cvp(link)

        elif name == "расписание звонков":
            self.handle_call_schedule(link)

    # ==== CVP ====

    def handle_cvp(self, link):
        pass

    def handle_new_cvp_date(self, date):
        pass

    def handle_cvp_item(self, date, group, start: int, end: int):
        pass

    # ==== CS ====

    def handle_call_schedule(self, link):
        pass

    def handle_new_call_schedule(self):
        pass

    def handle_pair_time(self, pair, start: int, end: int):
        pass

    # ==== TT ====

    def handle_new_date(self, new_date, old_date):
        if old_date is not None:
            self.parser.LOG.warning("Different dates in timetable: %r, %r", old_date, new_date)

    def handle_parsed_pair(self, date, group, pair_number, pair, teachers, cabinets, subgroup: int,
                           is_substitution: bool):
        pass


class SubpagesParsingHandler(Handler):
    __slots__ = ()

    def handle_cvp(self, link):
        if feature_enabled("cvp_parse"):
            self.parser.then(self.parser.update_cvp(link))

    def handle_call_schedule(self, link):
        self.parser.then(self.parser.update_call_schedule(link))


def parse_group_name(text: str):
    match = ParserBase.GROUP_NAME_RE.match(text.upper())
    if match is None:
        return None

    return GroupName(int(match.group(1)), match.group(2), int(match.group(3)))
