from typing import Optional

from .const import DOMAIN


def get_domain(eid: str) -> str:
    return eid.split(".")[0]


def get_id(eid: str) -> str:
    return eid.split(".")[1]


def parse_group_addresses(s: str) -> Optional[list[str]]:
    return list(filter(None, list(map(lambda x: x.strip(), s.split(","))))) or None
