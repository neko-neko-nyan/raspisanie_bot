import logging
import re
import typing

from .common import parse_pair_number, TimePeriod

NORM_TIME_RE = re.compile('\\s*(\\d+)[.,:](\\d+)\\s*.\\s*(\\d+)[.,:](\\d+)\\s*')
_LOG = logging.getLogger('parsing')


def parse_call_schedule(page) -> typing.Dict[int, TimePeriod]:
    table = page.find(".//div[@id = 'main']//table")

    if table[0].tag == 'tbody':
        table = table[0]

    pair_info = {}
    last_pn = 0

    for rn, tr in enumerate(table):
        col1 = tr[0].text_content()
        if col1.isspace():
            continue

        pn = parse_pair_number(col1, last_pn + 1)
        last_pn = pn

        col2 = tr[1].text_content()
        match = NORM_TIME_RE.fullmatch(col2)
        if match is None:
            _LOG.warning("Time re not matches: %r", col2, )
            _LOG.info("NOTE: While parsing row %s, pair number %s", rn, pn)
            continue

        start = int(match.group(1)) * 60 + int(match.group(2))
        end = int(match.group(3)) * 60 + int(match.group(4))
        pair_info[pn] = TimePeriod(start, end)

    return pair_info
