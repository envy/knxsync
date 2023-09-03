import logging

from .const import DOMAIN, CONF_KNXSYNC_BASE_ANSWER_READS
from .helpers import parse_group_addresses

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.components.knx import (
    DOMAIN as DOMAIN_KNX,
    SERVICE_KNX_EVENT_REGISTER,
)
from homeassistant.components.knx.const import KNX_ADDRESS

_LOGGER = logging.getLogger(DOMAIN)


class SyncedEntity:
    hass: HomeAssistant
    synced_entity_id: str
    answer_reads: bool

    def __init__(
        self, hass: HomeAssistant, synced_entity_id: str, entity_config: dict
    ) -> None:
        self.hass = hass
        self.synced_entity_id = synced_entity_id
        self.answer_reads = entity_config.get(CONF_KNXSYNC_BASE_ANSWER_READS, False)
        self.state = self.hass.states.get(self.synced_entity_id)
        self._remove_listener = async_track_state_change_event(
            self.hass, [self.synced_entity_id], self.async_state_changed
        )

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

    def _set_value_from_config(self, config: dict, config_key: str) -> None:
        if config_key in config.keys():
            setattr(self, config_key, parse_group_addresses(config[config_key]))
            _LOGGER.debug(f"{self.synced_entity_id} <- {getattr(self, config_key)}")

    async def _register_receiver(self, attr: str) -> None:
        v = getattr(self, attr)
        if v is not None:
            for address in v:
                _LOGGER.debug(
                    f"registering receiver {address} -> {self.synced_entity_id}"
                )
                await self.hass.services.async_call(
                    DOMAIN_KNX, SERVICE_KNX_EVENT_REGISTER, {KNX_ADDRESS: address}
                )

    def shutdown(self, config_entry: ConfigEntry) -> None:
        _LOGGER.debug("Shutting down %s", self.synced_entity_id)
        config_entry.async_create_task(self.hass, self._async_remove_listener())
