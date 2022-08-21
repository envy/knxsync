import logging
from typing import Any

from homeassistant import config_entries, core, exceptions
from homeassistant.core import callback
from homeassistant.const import ATTR_ENTITY_ID, CONF_ENTITIES, CONF_ENTITY_ID, CONF_ADDRESS, SERVICE_TURN_ON, SERVICE_TURN_OFF, STATE_ON
from homeassistant.components.light import DOMAIN as DOMAIN_LIGHT
from homeassistant.components.knx.const import CONF_STATE_ADDRESS, KNX_ADDRESS
from homeassistant.components.knx.schema import LightSchema
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import entity_registry

import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, CONF_KNXSYNC_SYNCED_ENTITIES, KNXSyncEntryData, KNXSyncEntityLightData
from .helpers import get_domain, get_id

import voluptuous as vol

_LOGGER = logging.getLogger(DOMAIN)

SUPPORTED_DOMAINS = ["light"]

DEFAULT_ENTRY_DATA = KNXSyncEntryData(
    synced_entities=dict()
)

STEP_INIT_DATA_SCHEMA = vol.Schema({
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
    def async_get_options_flow(config_entry) -> config_entries.OptionsFlow:
        return KNXSyncOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        return await self.async_step_init(user_input)

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors = {}
        try:
            await self.async_set_unique_id(f"knxsync")
            self._abort_if_unique_id_configured()
            entry_data = DEFAULT_ENTRY_DATA
            return self.async_create_entry(title="KNXSync", data=entry_data)
        except Exception as ex:
            _LOGGER.exception(f"Unexpected exception: {ex}")
            errors["base"] = "unknown"

        return self.async_abort(reason="error")


class KNXSyncOptionsFlowHandler(config_entries.OptionsFlow):
    current_config: dict

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            _LOGGER.debug(f"Moving to next step")
            domain = get_domain(user_input[CONF_ENTITY_ID])
            if domain == "new":
                return await self.async_step_new()
            elif domain == "remove":
                self.selected_entity_id = user_input[CONF_ENTITY_ID]
                pass
            elif domain == DOMAIN_LIGHT:
                self.selected_entity_id = user_input[CONF_ENTITY_ID]
                return await self.async_step_light()
        
        self.current_config = self.config_entry.data
        _LOGGER.debug(f"Current config: {self.current_config}")
        synced_entities = list(self.current_config[CONF_KNXSYNC_SYNCED_ENTITIES].keys())
        _LOGGER.debug(f"Already set up entites: {synced_entities}")
        synced_entities.append("new.entity")

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(CONF_ENTITY_ID, default="new.entity"): vol.In(synced_entities),
            })
        )

    async def async_step_new(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            entity_id = user_input[CONF_ENTITY_ID]
            domain = get_domain(entity_id)
            config = None
            if domain == DOMAIN_LIGHT:
                config = KNXSyncEntityLightData()
            entry_data = DEFAULT_ENTRY_DATA | self.current_config
            entry_data[CONF_KNXSYNC_SYNCED_ENTITIES][entity_id] = config
            _LOGGER.debug(f"Saving new config: {entry_data}")
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data = entry_data,
                title = "KNXSync"
            )
            return self.async_create_entry(title="", data={})
        
        entity_reg = entity_registry.async_get(self.hass)
        all_filtered_entities = [x for x in entity_reg.entities if get_domain(x) in SUPPORTED_DOMAINS]
        # Remove all entities that are already configured.
        all_valid_entities = [x for x in all_filtered_entities if x not in self.current_config[CONF_KNXSYNC_SYNCED_ENTITIES].keys()]
        if len(all_valid_entities) == 0:
            return self.async_abort(reason="no_valid_entities")

        return self.async_show_form(
            step_id="new",
            data_schema=vol.Schema({
                vol.Required(CONF_ENTITY_ID, default=all_valid_entities[0]): vol.In(all_valid_entities),
            })
        )

    async def async_step_light(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            entry_data = DEFAULT_ENTRY_DATA | self.current_config
            entry_data[CONF_KNXSYNC_SYNCED_ENTITIES][self.selected_entity_id] = user_input
            _LOGGER.debug(f"Saving new config: {entry_data}")
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data = entry_data,
                title = "KNXSync"
            )
            return self.async_create_entry(title="", data={})

        data = self.current_config[CONF_KNXSYNC_SYNCED_ENTITIES][self.selected_entity_id]
        _LOGGER.debug(f"Config for {self.selected_entity_id}: {data}")

        return self.async_show_form(
            step_id="light",
            data_schema=vol.Schema({
                # FIXME: These optionals are for some reason not optional
                vol.Optional(CONF_ADDRESS, default=data.get(CONF_ADDRESS)): str,
                vol.Optional(CONF_STATE_ADDRESS, default=data.get(CONF_STATE_ADDRESS)): str,
                vol.Optional(LightSchema.CONF_BRIGHTNESS_ADDRESS, default=data.get(LightSchema.CONF_BRIGHTNESS_ADDRESS)): str,
                vol.Optional(LightSchema.CONF_BRIGHTNESS_STATE_ADDRESS, default=data.get(LightSchema.CONF_BRIGHTNESS_STATE_ADDRESS)): str,
                vol.Optional(LightSchema.CONF_COLOR_ADDRESS, default=data.get(LightSchema.CONF_COLOR_ADDRESS)): str,
                vol.Optional(LightSchema.CONF_COLOR_STATE_ADDRESS, default=data.get(LightSchema.CONF_COLOR_STATE_ADDRESS)): str
            })
        )