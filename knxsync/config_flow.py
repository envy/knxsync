import logging

from homeassistant import config_entries, core, exceptions

from homeassistant.const import ATTR_ENTITY_ID, CONF_ENTITIES, CONF_ENTITY_ID, CONF_ADDRESS, SERVICE_TURN_ON, SERVICE_TURN_OFF, STATE_ON
from homeassistant.components.knx.const import CONF_STATE_ADDRESS, KNX_ADDRESS
from homeassistant.components.knx.schema import LightSchema

from .const import DOMAIN

import voluptuous as vol

_LOGGER = logging.getLogger(__name__)

STEP_INIT_DATA_SCHEMA = vol.Schema({
    vol.Required("name"): str,
    vol.Required(CONF_ENTITY_ID): str,
#    vol.Optional(CONF_ADDRESS): str,
#    vol.Optional(CONF_STATE_ADDRESS): str,
#    vol.Optional(LightSchema.CONF_BRIGHTNESS_ADDRESS): str,
#    vol.Optional(LightSchema.CONF_BRIGHTNESS_STATE_ADDRESS): str,
#    vol.Optional(LightSchema.CONF_COLOR_ADDRESS): str,
#    vol.Optional(LightSchema.CONF_COLOR_STATE_ADDRESS): str
})

class KNXSyncConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """KNXSync config flow"""

    VERSION = 1

#    @staticmethod
#    @callback
#    def async_get_options_flow(config_entry):
#        return KNXSyncOptionsFlowHandler()

    async def _validate_input(self, data: dict):
        return data

    async def async_step_user(self, user_input=None):
        return await self.async_step_init(user_input)

    async def async_step_init(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                info = await self.validate_input(user_input)
                await self.async_set_unique_id(f"knxsync_{str(info[CONF_ENTITY_ID])}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=info["name"], data=user_input)
            except Exception as ex:
                _LOGGER.exception(f"Unexpected exception: {ex}")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="init", data_schema=STEP_INIT_DATA_SCHEMA, errors=errors
        )

#class KNXSyncOptionsFlowHandler(config_entries.OptionsFlow):
#    async def async_step_init(self, user_input=None):
#        """Manage options"""
#        if user_input is not None:
#            return self.async_create_entry(title="", data=user_input)
#        
#        return self.async_show_form(
#            step_id=""
#        )