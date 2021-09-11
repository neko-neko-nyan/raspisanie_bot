import asyncio
import hashlib

import aiohttp
from lxml import html

from raspisanie_bot import parse_timetable, parse_call_schedule, parse_cvp
from raspisanie_bot.database import Settings, PairTime, Pair, Group, db

SESSION = aiohttp.ClientSession()


async def download_content(url):
    async with SESSION.get(url) as r:
        content = await r.read()
        encoding = r.get_encoding()

    return content, encoding


async def download_webpage(url):
    content, encoding = await download_content(url)
    return html.fromstring(content.decode(encoding))


async def download_webpage_if_not_cached(url, key):
    content, encoding = await download_content(url)

    md5 = hashlib.md5(content).digest()
    value = Settings.get_or_none(Settings.name == f"last-md5.{key}", Settings.value == md5)
    if value is not None:
        return None

    Settings.create(name=f"last-md5.{key}", value=md5)
    return html.fromstring(content.decode(encoding))


async def update_cvp(today, url):
    async with SESSION.get(url) as r:
        content = await r.read()

    cvp = parse_cvp(content)

    for group, (start, end) in cvp.items():
        pass


async def update_call_schedule(today, url):
    page = await download_webpage_if_not_cached(url, "call_schedule")
    if page is None:
        return

    call_schedule = parse_call_schedule(page)

    with db.atomic():
        PairTime.delete().where(PairTime.date == today).execute()

        for pn, (start, end) in call_schedule.items():
            PairTime.create(date=today, pair_number=pn, start_time=start, end_time=end)


async def update_timetable():
    page = await download_webpage_if_not_cached("http://novkrp.ru/raspisanie.htm", "timetable")
    if page is None:
        return

    today, useful_links, timetable = parse_timetable(page)

    for name, url in useful_links.items():
        name = name.lower()
        if name == "график питания студентов в столовой":
            await update_cvp(today, url)

        elif name == "расписание звонков":
            await update_call_schedule(today, url)

    with db.atomic():
        pts = PairTime.select().where(PairTime.date == today)
        Pair.delete().where(Pair.time.in_(pts)).execute()

        for group, tab in timetable.items():
            for pn, info in tab.items():
                time = PairTime.select().where(PairTime.date == today, PairTime.pair_number == pn)
                g = Group.get_or_none(Group.course == group.course, Group.group == group.group,
                                      Group.subgroup == group.subgroup)
                if g is None:
                    g = Group.create(course=group.course, group=group.group, subgroup=group.subgroup)

                Pair.create(time=time, group=g, name=info.name, teachers=[], cabinets=[])


async def main():
    async with SESSION:
        await update_timetable()


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
