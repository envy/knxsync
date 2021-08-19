import logging

from homeassistant import config_entries, core, exceptions
from homeassistant.core import callback
from homeassistant.const import ATTR_ENTITY_ID, CONF_ENTITIES, CONF_ENTITY_ID, CONF_ADDRESS, SERVICE_TURN_ON, SERVICE_TURN_OFF, STATE_ON
from homeassistant.components.light import DOMAIN as DOMAIN_LIGHT
from homeassistant.components.knx.const import CONF_STATE_ADDRESS, KNX_ADDRESS
from homeassistant.components.knx.schema import LightSchema

import homeassistant.helpers.config_validation as cv

from .const import DOMAIN
from .helpers import get_domain, get_id

import voluptuous as vol

_LOGGER = logging.getLogger(__name__)

STEP_INIT_DATA_SCHEMA = vol.Schema({
    vol.Required("name"): cv.string,
    vol.Required(CONF_ENTITY_ID): cv.string
})

STEP_LIGHT_DATA_SCHEMA = vol.Schema({
    vol.Optional(CONF_ADDRESS): str,
    vol.Optional(CONF_STATE_ADDRESS): str,
    vol.Optional(LightSchema.CONF_BRIGHTNESS_ADDRESS): str,
    vol.Optional(LightSchema.CONF_BRIGHTNESS_STATE_ADDRESS): str,
    vol.Optional(LightSchema.CONF_COLOR_ADDRESS): str,
    vol.Optional(LightSchema.CONF_COLOR_STATE_ADDRESS): str
})

class KNXSyncConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """KNXSync config flow"""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return KNXSyncOptionsFlowHandler(config_entry)

    def __init__(self):
        self.setup_data = None

    async def _validate_input_init(self, data: dict):
        return data

    async def _validate_input_light(self, data: dict):
        return data

    async def async_step_user(self, user_input=None):
        return await self.async_step_init(user_input)

    async def async_step_init(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                info = await self._validate_input_init(user_input)
                await self.async_set_unique_id(f"knxsync_{str(info[CONF_ENTITY_ID])}")
                self._abort_if_unique_id_configured()
                self.setup_data = info
                entity_domain = get_domain(info[CONF_ENTITY_ID])
                if entity_domain == DOMAIN_LIGHT:
                    return await self.async_step_light()
                errors["base"] = "unsupported_domain"
            except Exception as ex:
                _LOGGER.exception(f"Unexpected exception: {ex}")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="init", data_schema=STEP_INIT_DATA_SCHEMA, errors=errors
        )

    async def async_step_light(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                info = await self._validate_input_light(user_input)
                info["name"] = self.setup_data["name"]
                info[CONF_ENTITY_ID] = self.setup_data[CONF_ENTITY_ID]
                return self.async_create_entry(title=self.setup_data["name"], data=user_input)
            except Exception as ex:
                _LOGGER.exception(f"Unexpected exception: {ex}")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="light", data_schema=STEP_LIGHT_DATA_SCHEMA, errors=errors
        )

class KNXSyncOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if get_domain(self.config_entry.data[CONF_ENTITY_ID]) == DOMAIN_LIGHT:
            return await self.async_step_light()

        # Domain not supported, should not happen
        return self.async_create_entry(title="", data=self.config_entry.data)

    async def async_step_light(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="light", data_schema=vol.Schema({
                vol.Required("name", default=self.config_entry.data["name"]): cv.string,
                vol.Optional(CONF_ADDRESS, default=self.config_entry.data[CONF_ADDRESS]): str,
                vol.Optional(CONF_STATE_ADDRESS, default=self.config_entry.data[CONF_STATE_ADDRESS]): str,
                vol.Optional(LightSchema.CONF_BRIGHTNESS_ADDRESS, default=self.config_entry.data.get(LightSchema.CONF_BRIGHTNESS_ADDRESS)): str,
                vol.Optional(LightSchema.CONF_BRIGHTNESS_STATE_ADDRESS, default=self.config_entry.data.get(LightSchema.CONF_BRIGHTNESS_STATE_ADDRESS)): str,
                vol.Optional(LightSchema.CONF_COLOR_ADDRESS, default=self.config_entry.data.get(LightSchema.CONF_COLOR_ADDRESS)): str,
                vol.Optional(LightSchema.CONF_COLOR_STATE_ADDRESS, default=self.config_entry.data.get(LightSchema.CONF_COLOR_STATE_ADDRESS)): str
            })
        )