"""
A component which syncs a HA device to KNX

For more details about this component, please refer to the documentation at
https://github.com/envy/knxsync
"""
import logging
import asyncio

import voluptuous as vol

from . import light
from .const import DOMAIN
from .helpers import get_domain, get_id

from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from homeassistant.const import CONF_ENTITY_ID
from homeassistant.components.light import DOMAIN as DOMAIN_LIGHT
from homeassistant.components.sensor import DOMAIN as DOMAIN_SENSOR

VERSION = '0.0.1'

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = KNXSyncer(hass, entry)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry) -> bool:
    hass.data[DOMAIN].pop(entry.entry_id)
    return True

class KNXSyncer:
    def __init__(self, hass, config_entry: config_entries.ConfigEntry):
        
        self.hass = hass

        entity = config_entry.data

        other_id = entity[CONF_ENTITY_ID]
        domain = get_domain(other_id)
        _LOGGER.debug(f"syncing {other_id} to KNX")

        if domain == DOMAIN_LIGHT:
            self.synced_entity = light.SyncedLight(hass, config_entry)
        else:
            _LOGGER.error(f"Unsupported domain '{domain}'")
            pass
