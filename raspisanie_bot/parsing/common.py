import collections
import logging
import re
import typing

NORM_TEXT_RE = re.compile('\\s+')
NOT_DIGITS_RE = re.compile('\\D+')
GROUP_NAME_RE = re.compile('\\s*(\\d)\\s*-?\\s*([А-Я]{1,2})\\s*-?\\s*(\\d)\\s*', re.MULTILINE)
_LOG = logging.getLogger('parsing')

GroupName = collections.namedtuple('GroupName', ('course', 'group', 'subgroup'))
TimePeriod = collections.namedtuple('TimePeriod', ('begin', 'end'))


def normalize_text(s: str) -> str:
    return NORM_TEXT_RE.sub(' ', s).strip()


def parse_pair_number(s: str, default: int) -> int:
    s = NOT_DIGITS_RE.sub('', s)
    if not s:
        return default

    try:
        return int(s)
    except ValueError:
        return default


def parse_group_name(s: str, only_if_matches=False) -> typing.Optional[GroupName]:
    s = s.upper()
    match = GROUP_NAME_RE.match(s)
    if match is None:
        if only_if_matches:
            return None

        _LOG.warning("Group name re not match for %r", s)
        return GroupName(0, normalize_text(s), 1)

    return GroupName(int(match.group(1)), match.group(2), int(match.group(3)))
