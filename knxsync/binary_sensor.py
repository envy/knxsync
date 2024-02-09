import logging

from .const import (
    DOMAIN,
)
from .base import SyncedEntity

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_ENTITY_ID
from homeassistant.components.knx.const import (
    DOMAIN as DOMAIN_KNX,
    SERVICE_KNX_ATTR_REMOVE,
    SERVICE_KNX_ATTR_TYPE,
    SERVICE_KNX_EXPOSURE_REGISTER,
    CONF_STATE_ADDRESS,
    KNX_ADDRESS,
)
from homeassistant.components.knx.schema import ExposeSchema

_LOGGER = logging.getLogger(DOMAIN)


class SyncedBinarySensor(SyncedEntity):
    state_address: list[str]

    def __init__(
        self, hass: HomeAssistant, synced_entity_id: str, entity_config: dict
    ) -> None:
        super().__init__(hass, synced_entity_id, entity_config)
        _LOGGER.debug("Setting up synced binary sensor '%s'", self.synced_entity_id)

        self._set_value_from_config(CONF_STATE_ADDRESS, list())

    async def async_setup_events(self) -> None:
        # This directly configures knx native expose
        for address in self.state_address:
            await self.hass.services.async_call(
                DOMAIN_KNX,
                SERVICE_KNX_EXPOSURE_REGISTER,
                {
                    KNX_ADDRESS: address,
                    SERVICE_KNX_ATTR_TYPE: ExposeSchema.CONF_KNX_EXPOSE_BINARY,
                    CONF_ENTITY_ID: self.synced_entity_id,
                },
            )

    async def _async_shutdown(self) -> None:
        _LOGGER.debug("Removing exposure for binary sensor '%s'", self.synced_entity_id)
        for address in self.state_address:
            await self.hass.services.async_call(
                DOMAIN_KNX,
                SERVICE_KNX_EXPOSURE_REGISTER,
                {KNX_ADDRESS: address, SERVICE_KNX_ATTR_REMOVE: True},
            )

    def shutdown(self, config_entry: ConfigEntry) -> None:
        super().shutdown(config_entry)
        config_entry.async_create_task(self.hass, self._async_shutdown())
