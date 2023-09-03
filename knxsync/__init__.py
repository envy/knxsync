"""
A component which syncs a HA device to KNX

For more details about this component, please refer to the documentation at
https://github.com/envy/knxsync
"""
import logging

from .binary_sensor import SyncedBinarySensor
from .const import DOMAIN, CONF_KNXSYNC_SYNCED_ENTITIES
from .light import SyncedLight
from .climate import SyncedClimate
from .helpers import get_domain

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.components.binary_sensor import DOMAIN as DOMAIN_BINARY_SENSOR
from homeassistant.components.light import DOMAIN as DOMAIN_LIGHT
from homeassistant.components.climate import DOMAIN as DOMAIN_CLIMATE

VERSION = '0.1.0'

_LOGGER = logging.getLogger(DOMAIN)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = KNXSyncer(hass, entry)
    await hass.data[DOMAIN][entry.entry_id].async_setup_events(entry)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data[DOMAIN].pop(entry.entry_id)
    return True

async def async_update_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)

class KNXSyncer:
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry):
        self.hass = hass
        self.config_entry = config_entry
        self.synced_entities = {}

        config = config_entry.data
        _LOGGER.debug(f"Current config: {config}")
        for synced_entity_id, entity_config in config[CONF_KNXSYNC_SYNCED_ENTITIES].items():
            domain = get_domain(synced_entity_id)
            if domain == DOMAIN_LIGHT:
                self.synced_entities[synced_entity_id] = SyncedLight(hass, synced_entity_id, entity_config)
            elif domain == DOMAIN_CLIMATE:
                self.synced_entities[synced_entity_id] = SyncedClimate(hass, synced_entity_id, entity_config)
            elif domain == DOMAIN_BINARY_SENSOR:
                self.synced_entities[synced_entity_id] = SyncedBinarySensor(hass, synced_entity_id, entity_config)
            else:
                _LOGGER.error(f"Unsupported domain '{domain}'")

    async def async_got_telegram(self, event: Event) -> None:
        for syncer in self.synced_entities.values():
            await syncer.async_got_telegram(event)

    async def async_setup_events(self, config_entry: ConfigEntry) -> None:
        _LOGGER.debug("Setting up event listeners")

        for syncer in self.synced_entities.values():
            await syncer.async_setup_events()

        # async_listen returns a callback for unregistering the listener
        # We register that callback here to get called when we are unloaded
        config_entry.async_on_unload(config_entry.add_update_listener(async_update_entry))
        config_entry.async_on_unload(self.hass.bus.async_listen('knx_event', self.async_got_telegram))
        config_entry.async_on_unload(self.shutdown)

    @callback
    def shutdown(self) -> None:
        _LOGGER.debug("Shutting down...")
        for syncer in self.synced_entities.values():
            syncer.shutdown(self.config_entry)
