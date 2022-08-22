from .const import CONF_KNXSYNC_BASE_ANSWER_READS

from homeassistant.core import HomeAssistant

class SyncedEntity:
    hass: HomeAssistant
    synced_entity_id: str
    answer_reads: bool

    def __init__(self, hass: HomeAssistant, synced_entity_id: str, entity_config: dict):
        self.hass = hass
        self.synced_entity_id = synced_entity_id
        self.state = None
        self.answer_reads = entity_config.get(CONF_KNXSYNC_BASE_ANSWER_READS, False)
