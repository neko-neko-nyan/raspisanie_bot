import typing

from .common import parse_pair_number, parse_time, TimePeriod


def parse_call_schedule(page) -> typing.Dict[int, TimePeriod]:
    table = page.find(".//div[@id = 'main']//table")

    if table[0].tag == 'tbody':
        table = table[0]

    pair_info = {}
    last_pn = 0

    for tr in table:
        pn = parse_pair_number(tr[0].text_content(), last_pn + 1)
        last_pn = pn

        b = tr[1].text_content().strip().split()
        pair_info[pn] = TimePeriod(parse_time(b[0]), parse_time(b[-1]))

    return pair_info

"http://novkrp.ru/index.php/studentam/79-sample-data-articles/joomla/studentam/122-raspisanie-zvonkov"
