import logging
from copy import deepcopy
from typing import Any

from homeassistant import config_entries, core, exceptions
from homeassistant.core import callback
from homeassistant.const import ATTR_ENTITY_ID, CONF_ENTITIES, CONF_ENTITY_ID, CONF_ADDRESS, SERVICE_TURN_ON, SERVICE_TURN_OFF, STATE_ON
from homeassistant.components.light import DOMAIN as DOMAIN_LIGHT
from homeassistant.components.knx.const import DOMAIN as DOMAIN_KNX, CONF_STATE_ADDRESS, KNX_ADDRESS
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
    general_settings: dict
    is_new_entity: bool
    selected_entity_id: str | None

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry
        self.general_settings = {}
        self.is_new_entity = False
        self.selected_entity_id = None

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        self.current_config = self.config_entry.data
        return self.async_show_menu(
            step_id="init",
            menu_options=["new", "remove", "edit"]
        )

    async def async_step_new(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            entity_id = user_input[CONF_ENTITY_ID]
            self.selected_entity_id = entity_id
            self.is_new_entity = True
            domain = get_domain(entity_id)
            config = None
            if domain == DOMAIN_LIGHT:
                return await self.async_step_light()
            else:
                return self.async_abort(reason="not_supported")

        entity_reg = entity_registry.async_get(self.hass)
        all_filtered_entities = [id for id, entity in entity_reg.entities.data.items() if get_domain(id) in SUPPORTED_DOMAINS and entity.platform != DOMAIN_KNX]
        # Remove all entities that are already configured.
        all_valid_entities = [x for x in all_filtered_entities if x not in self.current_config[CONF_KNXSYNC_SYNCED_ENTITIES].keys()]
        if len(all_valid_entities) == 0:
            return self.async_abort(reason="no_valid_entities")

        return self.async_show_form(
            step_id="new",
            data_schema=vol.Schema({
                vol.Required(CONF_ENTITY_ID): vol.In(all_valid_entities),
            })
        )

    async def async_step_remove(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            entry_data = DEFAULT_ENTRY_DATA | self.general_settings
            entry_data[CONF_KNXSYNC_SYNCED_ENTITIES] = deepcopy(self.current_config[CONF_KNXSYNC_SYNCED_ENTITIES])
            entry_data[CONF_KNXSYNC_SYNCED_ENTITIES].pop(user_input[CONF_ENTITY_ID])
            _LOGGER.debug(f"Saving new config: {entry_data}")
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data = entry_data,
                title = "KNXSync"
            )
            return self.async_create_entry(title="", data={})

        synced_entities = list(self.current_config[CONF_KNXSYNC_SYNCED_ENTITIES].keys())
        _LOGGER.debug(f"Already set up entites: {synced_entities}")

        return self.async_show_form(
            step_id="remove",
            data_schema=vol.Schema({
                vol.Required(CONF_ENTITY_ID): vol.In(synced_entities),
            })
        )

    async def async_step_edit(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            domain = get_domain(user_input[CONF_ENTITY_ID])
            if domain == DOMAIN_LIGHT:
                self.selected_entity_id = user_input[CONF_ENTITY_ID]
                return await self.async_step_light()

        synced_entities = list(self.current_config[CONF_KNXSYNC_SYNCED_ENTITIES].keys())
        _LOGGER.debug(f"Already set up entites: {synced_entities}")

        return self.async_show_form(
            step_id="edit",
            data_schema=vol.Schema({
                vol.Required(CONF_ENTITY_ID): vol.In(synced_entities),
            })
        )

    async def async_step_light(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            entry_data = DEFAULT_ENTRY_DATA | self.general_settings
            entry_data[CONF_KNXSYNC_SYNCED_ENTITIES] = deepcopy(self.current_config[CONF_KNXSYNC_SYNCED_ENTITIES])
            entry_data[CONF_KNXSYNC_SYNCED_ENTITIES][self.selected_entity_id] = user_input
            _LOGGER.debug(f"Saving new config: {entry_data}")
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data = entry_data,
                title = "KNXSync"
            )
            return self.async_create_entry(title="", data={})

        data = KNXSyncEntityLightData()
        if not self.is_new_entity:
            data = self.current_config[CONF_KNXSYNC_SYNCED_ENTITIES][self.selected_entity_id]
        _LOGGER.debug(f"Config for {self.selected_entity_id}: {data}")

        return self.async_show_form(
            step_id="light",
            data_schema=vol.Schema({
                vol.Optional(CONF_ADDRESS, description={"suggested_value": data.get(CONF_ADDRESS)}): str,
                vol.Optional(CONF_STATE_ADDRESS, description={"suggested_value": data.get(CONF_STATE_ADDRESS)}): str,
                vol.Optional(LightSchema.CONF_BRIGHTNESS_ADDRESS, description={"suggested_value": data.get(LightSchema.CONF_BRIGHTNESS_ADDRESS)}): str,
                vol.Optional(LightSchema.CONF_BRIGHTNESS_STATE_ADDRESS, description={"suggested_value": data.get(LightSchema.CONF_BRIGHTNESS_STATE_ADDRESS)}): str,
                vol.Optional(LightSchema.CONF_COLOR_ADDRESS, description={"suggested_value": data.get(LightSchema.CONF_COLOR_ADDRESS)}): str,
                vol.Optional(LightSchema.CONF_COLOR_STATE_ADDRESS, description={"suggested_value": data.get(LightSchema.CONF_COLOR_STATE_ADDRESS)}): str
            })
        )