import voluptuous as vol
from typing import Any
import homeassistant.helpers.config_validation as cv
import re

def get_domain(eid: str) -> str:
    return eid.split('.')[0]

def get_id(eid: str) -> str:
    return eid.split('.')[1]

def group_address(value: Any) -> str:
    str_value = str(value).lower()
    m = re.search('', str_value)
    area = m.group(0)
    line = m.group(1)
    member = m.group(2)
    # TODO: test stuff
    # return vol.Invalid(f"{value} is not a valid KNX group address.")
    return str_value
