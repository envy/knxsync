import logging
from typing import Any

from .const import KNXSyncEntityBaseData, DOMAIN, CONF_KNXSYNC_BASE_ANSWER_READS

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.components.knx.const import (
    DOMAIN as DOMAIN_KNX,
    KNX_ADDRESS,
    SERVICE_KNX_EVENT_REGISTER,
)

_LOGGER = logging.getLogger(DOMAIN)


class SyncedEntity:
    hass: HomeAssistant
    synced_entity_id: str
    answer_reads: bool

    def __init__(
        self,
        hass: HomeAssistant,
        synced_entity_id: str,
        entity_config: KNXSyncEntityBaseData,
    ) -> None:
        self.hass = hass
        self.synced_entity_id = synced_entity_id
        self._config = entity_config
        self.state = self.hass.states.get(self.synced_entity_id)
        self._remove_listener = async_track_state_change_event(
            self.hass, [self.synced_entity_id], self.async_state_changed
        )

        self._set_value_from_config(CONF_KNXSYNC_BASE_ANSWER_READS, False)

    async def async_got_telegram(self, _: Event) -> None:
        pass

    async def async_state_changed(self, _: Event) -> None:
        pass

    async def async_setup_events(self) -> None:
        pass

    async def _async_remove_listener(self) -> None:
        if self._remove_listener is not None:
            _LOGGER.debug("Removing listener")
            self._remove_listener()
            self._remove_listener = None

    def _set_value_from_config(self, config_key: str, default: Any) -> None:
        setattr(self, config_key, self._config.get(config_key, default))
        _LOGGER.debug(f"{self.synced_entity_id} <- {getattr(self, config_key)}")

    async def _register_receiver(self, attr: str) -> None:
        v = getattr(self, attr)
        for address in v:
            _LOGGER.debug(f"registering receiver {address} -> {self.synced_entity_id}")
            await self.hass.services.async_call(
                DOMAIN_KNX, SERVICE_KNX_EVENT_REGISTER, {KNX_ADDRESS: address}
            )

    def shutdown(self, config_entry: ConfigEntry) -> None:
        _LOGGER.debug("Shutting down %s", self.synced_entity_id)
        config_entry.async_create_task(self.hass, self._async_remove_listener())
