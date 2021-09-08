import io
import re

import requests
from pdfminer.converter import PDFLayoutAnalyzer
from pdfminer.layout import LTPage, LTTextLine, LTTextBox, LAParams, LTChar, LTText
from pdfminer.pdfinterp import PDFPageInterpreter, PDFResourceManager
from pdfminer.pdfpage import PDFPage

from raspisanie_bot.parsing.common import TimePeriod, parse_group_name

NORM_TIME_RE = re.compile('с\\s*(\\d+)[.:](\\d+)\\s*до\\s*(\\d+)[.:](\\d+)\\s*(.*)')
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


def parse_covid_pit(url):
    with requests.get(url) as r:
        content = r.content

    rsrcmgr = PDFResourceManager()
    device = LinesConverter(rsrcmgr)
    interpreter = PDFPageInterpreter(rsrcmgr, device)

    with io.BytesIO(content) as fp:
        for page in PDFPage.get_pages(fp):
            interpreter.process_page(page)

    last_time = None
    table = {}

    for line in device.result:
        if line.isdigit():
            continue

        match = NORM_TIME_RE.fullmatch(line)
        if match:
            start = int(match.group(1)) * 60 + int(match.group(2))
            end = int(match.group(3)) * 60 + int(match.group(4))
            last_time = TimePeriod(start, end)
            line = match.group(5)

        if line:
            res = []
            for i in NORM_GROUPS_RE.sub(' ', line).split():
                i = parse_group_name(i, only_if_matches=True)
                if i:
                    res.append(i)

            if res:
                table[last_time] = res

    return table


"http://www.novkrp.ru/data/covid_pit.pdf"
