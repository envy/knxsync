"""
A component which syncs a HA device to KNX

For more details about this component, please refer to the documentation at
https://github.com/envy/knxsync
"""
import logging
import asyncio

import voluptuous as vol

from .const import DOMAIN, CONF_KNXSYNC_SYNCED_ENTITIES
from .light import SyncedLight
from .helpers import get_domain, get_id

from homeassistant import config_entries
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.const import ATTR_ENTITY_ID, CONF_ENTITY_ID
from homeassistant.components.light import DOMAIN as DOMAIN_LIGHT
from homeassistant.components.sensor import DOMAIN as DOMAIN_SENSOR

VERSION = '0.0.1'

_LOGGER = logging.getLogger(DOMAIN)

async def async_setup_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = KNXSyncer(hass, entry)
    await hass.data[DOMAIN][entry.entry_id].setup_events(entry)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry) -> bool:
    hass.data[DOMAIN].pop(entry.entry_id)
    return True

async def async_update_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)

class KNXSyncer:
    def __init__(self, hass: HomeAssistant, config_entry: config_entries.ConfigEntry):
        self.hass = hass

        self.synced_entities = {}

        config = config_entry.data
        _LOGGER.debug(f"Current config: {config}")
        for synced_entity_id, entity_config in config[CONF_KNXSYNC_SYNCED_ENTITIES].items():
            domain = get_domain(synced_entity_id)
            if domain == DOMAIN_LIGHT:
                self.synced_entities[synced_entity_id] = SyncedLight(hass, synced_entity_id, entity_config)
            else:
                _LOGGER.error(f"Unsupported domain '{domain}'")

    async def got_telegram(self, event: Event) -> None:
        for entity_id, syncer in self.synced_entities.items():
            await syncer.got_telegram(event)

    async def setup_events(self, config_entry: config_entries.ConfigEntry) -> None:
        _LOGGER.debug("Setting up event listeners")

        for entity_id, syncer in self.synced_entities.items():
            await syncer.setup_events()

        # async_listen returns a callback for unregistering the listener
        # We register that callback here to get called when we are unloaded
        config_entry.async_on_unload(config_entry.add_update_listener(async_update_entry))
        config_entry.async_on_unload(self.hass.bus.async_listen('knx_event', self.got_telegram))
        config_entry.async_on_unload(self.shutdown)

    @callback
    def shutdown(self) -> None:
        _LOGGER.debug("Shutting down...")
        for entity_id, syncer in self.synced_entities.items():
            syncer.shutdown()