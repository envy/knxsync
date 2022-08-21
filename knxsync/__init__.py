"""
A component which syncs a HA device to KNX

For more details about this component, please refer to the documentation at
https://github.com/envy/knxsync
"""
import logging
import asyncio

import voluptuous as vol

from .light import SyncedLight
from .const import DOMAIN
from .helpers import get_domain, get_id

from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from homeassistant.const import CONF_ENTITY_ID
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

class KNXSyncer:
    def __init__(self, hass: HomeAssistant, config_entry: config_entries.ConfigEntry):
        self.hass = hass

        config = config_entry.data

        synced_entity_id = config[CONF_ENTITY_ID]
        domain = get_domain(synced_entity_id)

        if domain == DOMAIN_LIGHT:
            self.synced_entity = light.SyncedLight(hass, config_entry)
        else:
            _LOGGER.error(f"Unsupported domain '{domain}'")
            pass

    async def got_telegram(self, event):
        await self.synced_entity.got_telegram(event)

    async def state_changed(self, event):
        await self.synced_entity.state_changed(event)

    async def setup_events(self, config_entry: config_entries.ConfigEntry):
        _LOGGER.debug("Setting up event listeners")
        await self.synced_entity.setup_events()

        # async_listen returns a callback for unregistering the listener
        # We register that callback here to get called when we are unloaded
        config_entry.async_on_unload(self.hass.bus.async_listen('knx_event', self.got_telegram))
        config_entry.async_on_unload(self.hass.bus.async_listen('state_changed', self.state_changed))
