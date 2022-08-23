from .const import CONF_KNXSYNC_BASE_ANSWER_READS

from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_state_change_event

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
            self.hass, [self.synced_entity_id], self.state_changed
        )

    async def state_changed(self, event: Event) -> None:
        pass

    def shutdown(self) -> None:
        if self._remove_listener is not None:
            self._remove_listener()
            self._remove_listener = None