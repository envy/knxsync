import logging

from .const import (
    DOMAIN,
)
from .base import SyncedEntity
from .helpers import parse_group_addresses

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_ENTITY_ID
from homeassistant.components.knx import (
    DOMAIN as DOMAIN_KNX,
    SERVICE_KNX_ATTR_REMOVE,
    SERVICE_KNX_EXPOSURE_REGISTER
)
from homeassistant.components.knx.const import CONF_STATE_ADDRESS, KNX_ADDRESS
from homeassistant.components.knx.schema import ExposeSchema

_LOGGER = logging.getLogger(DOMAIN)

class SyncedBinarySensor(SyncedEntity):
    def __init__(self, hass: HomeAssistant, synced_entity_id: str, entity_config: dict):
        super().__init__(hass, synced_entity_id, entity_config)
        self.state_address: [str] | None = None
        _LOGGER.debug("Setting up synced binary sensor '%s'", self.synced_entity_id)

        if CONF_STATE_ADDRESS in entity_config.keys():
            self.state_address = parse_group_addresses(entity_config[CONF_STATE_ADDRESS])
            _LOGGER.debug("%s -> %s", self.synced_entity_id, self.state_address)

    async def async_setup_events(self) -> None:
        if self.state_address is not None:
            for address in self.state_address:
                await self.hass.services.async_call(DOMAIN_KNX, SERVICE_KNX_EXPOSURE_REGISTER, {
                    KNX_ADDRESS: address,
                    ExposeSchema.CONF_KNX_EXPOSE_TYPE: ExposeSchema.CONF_KNX_EXPOSE_BINARY,
                    CONF_ENTITY_ID: self.synced_entity_id
                })

    async def _async_shutdown(self) -> None:
        _LOGGER.debug("Removing exposure for binary sensor '%s'", self.synced_entity_id)
        if self.state_address is not None:
            for address in self.state_address:
                await self.hass.services.async_call(DOMAIN_KNX, SERVICE_KNX_EXPOSURE_REGISTER, {
                    KNX_ADDRESS: address,
                    SERVICE_KNX_ATTR_REMOVE: True
                })

    def shutdown(self, config_entry: ConfigEntry) -> None:
        super().shutdown(config_entry)
        config_entry.async_create_task(self.hass, self._async_shutdown())