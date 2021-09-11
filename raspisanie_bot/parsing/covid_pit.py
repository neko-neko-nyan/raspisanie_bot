import io
import re
import typing

from pdfminer.converter import PDFLayoutAnalyzer
from pdfminer.layout import LTPage, LTTextLine, LTTextBox, LAParams, LTChar, LTText
from pdfminer.pdfinterp import PDFPageInterpreter, PDFResourceManager
from pdfminer.pdfpage import PDFPage

from raspisanie_bot.parsing.common import TimePeriod, parse_group_name, GroupName

NORM_TIME_RE = re.compile('с\\s*(\\d+)[.,:](\\d+)\\s*до\\s*(\\d+)[.,:](\\d+)\\s*(.*)')
NORM_GROUPS_RE = re.compile('[^0-9а-я- ]+')


class LinesConverter(PDFLayoutAnalyzer):
    def __init__(self, rsrcmgr):
        PDFLayoutAnalyzer.__init__(self, rsrcmgr, laparams=LAParams())
        self.result = None

    def receive_layout(self, ltpage):
        def render(item):
            if isinstance(item, (LTPage, LTTextLine, LTTextBox)):
                res = []

                for child in item:
                    child = render(child)
                    if child:
                        res.append(child)

                if isinstance(item, (LTTextLine, LTTextBox)):
                    res = ''.join(res).strip()

                return res

            elif isinstance(item, (LTChar, LTText)):
                return item.get_text().lower()

        self.result = render(ltpage)


def parse_cvp_table(data: typing.List[str]) -> typing.Dict[GroupName, TimePeriod]:
    last_time = None
    table = {}

    for line in data:
        if line.isdigit():
            continue

        match = NORM_TIME_RE.fullmatch(line)
        if match:
            start = int(match.group(1)) * 60 + int(match.group(2))
            end = int(match.group(3)) * 60 + int(match.group(4))
            last_time = TimePeriod(start, end)
            line = match.group(5)

        if line:
            for group in NORM_GROUPS_RE.sub(' ', line).split():
                group = parse_group_name(group, only_if_matches=True)
                if group:
                    table[group] = last_time

    return table


def parse_cvp_pdf(content: bytes) -> typing.List[str]:
    rsrcmgr = PDFResourceManager()
    device = LinesConverter(rsrcmgr)
    interpreter = PDFPageInterpreter(rsrcmgr, device)

    with io.BytesIO(content) as fp:
        for page in PDFPage.get_pages(fp):
            interpreter.process_page(page)

    return device.result


def parse_cvp(content: bytes) -> typing.Dict[GroupName, TimePeriod]:
    return parse_cvp_table(parse_cvp_pdf(content))
