import logging
import asyncio

from .const import (
    DOMAIN,
    TELEGRAMTYPE_READ,
    TELEGRAMTYPE_WRITE,
    CONF_KNXSYNC_LIGHT_ZERO_BRIGHTNESS_WHEN_OFF
)
from .base import SyncedEntity
from .helpers import get_domain, get_id

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, State, HomeAssistant
from homeassistant.const import ATTR_ENTITY_ID, CONF_ENTITY_ID, CONF_ADDRESS, SERVICE_TURN_ON, SERVICE_TURN_OFF, STATE_ON
from homeassistant.components.binary_sensor import DOMAIN as DOMAIN_BINARY_SENSOR
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
        self.state_address: str | None = None
        _LOGGER.debug("Setting up synced binary sensor '%s'", self.synced_entity_id)

        if CONF_STATE_ADDRESS in entity_config.keys():
            self.state_address = entity_config[CONF_STATE_ADDRESS]
            _LOGGER.debug("%s -> %s", self.synced_entity_id, self.state_address)

    async def async_setup_events(self) -> None:
        await self.hass.services.async_call(DOMAIN_KNX, SERVICE_KNX_EXPOSURE_REGISTER, {
            KNX_ADDRESS: self.state_address,
            ExposeSchema.CONF_KNX_EXPOSE_TYPE: ExposeSchema.CONF_KNX_EXPOSE_BINARY,
            CONF_ENTITY_ID: self.synced_entity_id
        })

    async def _async_shutdown(self) -> None:
        _LOGGER.debug("Removing exposure for binary sensor '%s'", self.synced_entity_id)
        await self.hass.services.async_call(DOMAIN_KNX, SERVICE_KNX_EXPOSURE_REGISTER, {
            KNX_ADDRESS: self.state_address,
            SERVICE_KNX_ATTR_REMOVE: True
        })

    def shutdown(self, config_entry: ConfigEntry) -> None:
        super().shutdown(config_entry)
        config_entry.async_create_task(self.hass, self._async_shutdown())