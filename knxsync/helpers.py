import voluptuous as vol
from typing import Optional, Any

from .const import KNXSyncEntityLightData

from homeassistant.const import CONF_ADDRESS
from homeassistant.components.knx.schema import ga_list_validator
from homeassistant.components.knx.const import CONF_STATE_ADDRESS
from homeassistant.components.knx.light import LightSchema


def get_domain(eid: str) -> str:
    return eid.split(".")[0]


def get_id(eid: str) -> str:
    return eid.split(".")[1]


def parse_group_addresses(s: str) -> Optional[list[str]]:
    return list(filter(None, list(map(lambda x: x.strip(), s.split(","))))) or None


async def async_validate_light_config(user_input: dict[str, Any]) -> dict[str, str]:
    errors = {}
    if user_input is None:
        errors["base"] = "Input was empty"
        return errors

    # TODO: does not work on empty lists...
    # TODO: also does not forward the actual error
    # try:
    #     ga_list_validator(user_input.get(CONF_ADDRESS, list()))
    # except vol.Invalid:
    #     errors[CONF_ADDRESS] = "invalid_ga"
    # try:
    #     ga_list_validator(user_input.get(CONF_STATE_ADDRESS, list()))
    # except vol.Invalid:
    #     errors[CONF_STATE_ADDRESS] = "invalid_ga"
    # try:
    #     ga_list_validator(user_input.get(LightSchema.CONF_BRIGHTNESS_ADDRESS, list()))
    # except vol.Invalid:
    #     errors[LightSchema.CONF_BRIGHTNESS_ADDRESS] = "invalid_ga"
    # try:
    #     ga_list_validator(
    #         user_input.get(LightSchema.CONF_BRIGHTNESS_STATE_ADDRESS, list())
    #     )
    # except vol.Invalid:
    #     errors[LightSchema.CONF_BRIGHTNESS_STATE_ADDRESS] = "invalid_ga"
    # try:
    #     ga_list_validator(user_input.get(LightSchema.CONF_COLOR_ADDRESS, list()))
    # except vol.Invalid:
    #     errors[LightSchema.CONF_COLOR_ADDRESS] = "invalid_ga"
    # try:
    #     ga_list_validator(user_input.get(LightSchema.CONF_COLOR_STATE_ADDRESS, list()))
    # except vol.Invalid:
    #     errors[LightSchema.CONF_COLOR_STATE_ADDRESS] = "invalid_ga"

    return errors
