import logging
import asyncio

from .const import DOMAIN, CONF_KNXSYNC_BASE_ANSWER_READS

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_state_change_event

_LOGGER = logging.getLogger(DOMAIN)

class SyncedEntity:
    hass: HomeAssistant
    synced_entity_id: str
    answer_reads: bool

    def __init__(self, hass: HomeAssistant, synced_entity_id: str, entity_config: dict):
        self.hass = hass
        self.synced_entity_id = synced_entity_id
        self.answer_reads = entity_config.get(CONF_KNXSYNC_BASE_ANSWER_READS, False)
        self.state = self.hass.states.get(self.synced_entity_id)
        self._remove_listener = async_track_state_change_event(
            self.hass, [self.synced_entity_id], self.async_state_changed
        )

    async def async_got_telegram(self, event: Event) -> None:
        pass

    async def async_state_changed(self, event: Event) -> None:
        pass

    async def async_setup_events(self) -> None:
        pass

    async def _async_remove_listener(self) -> None:
        if self._remove_listener is not None:
            _LOGGER.debug("Removing listener")
            self._remove_listener()
            self._remove_listener = None

    def shutdown(self, config_entry: ConfigEntry) -> None:
        _LOGGER.debug("Shutting down %s", self.synced_entity_id)
        config_entry.async_create_task(self.hass, self._async_remove_listener())
