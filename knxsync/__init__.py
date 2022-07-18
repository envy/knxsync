"""
A component which syncs a HA device to KNX

For more details about this component, please refer to the documentation at
https://github.com/envy/knxsync
"""
import logging
import asyncio

import voluptuous as vol

from .const import DOMAIN
from .helpers import get_domain, get_id

from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from homeassistant.const import ATTR_ENTITY_ID, CONF_ENTITIES, CONF_ENTITY_ID, CONF_ADDRESS, SERVICE_TURN_ON, SERVICE_TURN_OFF, STATE_ON
from homeassistant.components.light import DOMAIN as DOMAIN_LIGHT, ATTR_RGB_COLOR, ATTR_BRIGHTNESS
from homeassistant.components.sensor import DOMAIN as DOMAIN_SENSOR
from homeassistant.components.knx import DOMAIN as DOMAIN_KNX, SERVICE_KNX_SEND, SERVICE_KNX_ATTR_PAYLOAD, SERVICE_KNX_EVENT_REGISTER
from homeassistant.components.knx.const import CONF_STATE_ADDRESS, KNX_ADDRESS
from homeassistant.components.knx.schema import LightSchema
import homeassistant.helpers.config_validation as cv

from xknx.dpt.dpt_2byte_float import DPT2ByteFloat
from xknx.dpt.dpt_2byte_signed import DPT2ByteSigned

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
        self.entity_map = {
            DOMAIN_LIGHT: {
                'receivers_onoff': {},
                'receivers_brightness': {},
                'receivers_color': {},
                'senders_onoff': {},
                'senders_color': {},
                'senders_brightness': {}
            },
            DOMAIN_SENSOR: {
                'senders_value': {}
            }
        }
        self.hass = hass

        entity = config_entry.data

        other_id = entity[CONF_ENTITY_ID]
        domain = get_domain(other_id)
        _LOGGER.debug("syncing {} to KNX".format(other_id))

        if domain == DOMAIN_LIGHT:
            if CONF_ADDRESS in entity.keys():
                _LOGGER.debug("registering receiver {} -> {}".format(entity[CONF_ADDRESS], other_id))
                asyncio.run_coroutine_threadsafe(hass.services.async_call(DOMAIN_KNX, SERVICE_KNX_EVENT_REGISTER, { KNX_ADDRESS: entity[CONF_ADDRESS]}), hass.loop)
                self.entity_map[domain]['receivers_onoff'][entity[CONF_ADDRESS]] = other_id

            if CONF_STATE_ADDRESS in entity.keys():
                _LOGGER.debug("registering sender {} -> {}".format(other_id, entity[CONF_STATE_ADDRESS]))
                self.entity_map[domain]['senders_onoff'][other_id] = entity[CONF_STATE_ADDRESS]

            if LightSchema.CONF_BRIGHTNESS_ADDRESS in entity.keys():
                _LOGGER.debug("registering receiver {} -> {}".format(entity[LightSchema.CONF_BRIGHTNESS_ADDRESS], other_id))
                asyncio.run_coroutine_threadsafe(hass.services.async_call(DOMAIN_KNX, SERVICE_KNX_EVENT_REGISTER, { KNX_ADDRESS: entity[LightSchema.CONF_BRIGHTNESS_ADDRESS]}), hass.loop)
                self.entity_map[domain]['receivers_brightness'][entity[LightSchema.CONF_BRIGHTNESS_ADDRESS]] = other_id

            if LightSchema.CONF_BRIGHTNESS_STATE_ADDRESS in entity.keys():
                _LOGGER.debug("registering sender {} -> {}".format(other_id, entity[LightSchema.CONF_BRIGHTNESS_STATE_ADDRESS]))
                self.entity_map[domain]['senders_brightness'][other_id] = entity[LightSchema.CONF_BRIGHTNESS_STATE_ADDRESS]

            if LightSchema.CONF_COLOR_ADDRESS in entity.keys():
                _LOGGER.debug("registering receiver {} -> {}".format(entity[LightSchema.CONF_COLOR_ADDRESS], other_id))
                asyncio.run_coroutine_threadsafe(hass.services.async_call(DOMAIN_KNX, SERVICE_KNX_EVENT_REGISTER, { KNX_ADDRESS: entity[LightSchema.CONF_COLOR_ADDRESS]}), hass.loop)
                self.entity_map[domain]['receivers_color'][entity[LightSchema.CONF_COLOR_ADDRESS]] = other_id

            if LightSchema.CONF_COLOR_STATE_ADDRESS in entity.keys():
                _LOGGER.debug("registering sender {} -> {}".format(other_id, entity[LightSchema.CONF_COLOR_STATE_ADDRESS]))
                self.entity_map[domain]['senders_color'][other_id] = entity[LightSchema.CONF_COLOR_STATE_ADDRESS]
        elif domain == DOMAIN_SENSOR:
            if CONF_STATE_ADDRESS in entity.keys():
                _LOGGER.debug("registering sender {} -> {}".format(other_id, entity[CONF_STATE_ADDRESS]))
                self.entity_map[domain]['senders_value'][other_id] = entity[CONF_STATE_ADDRESS]

        # async_listen returns a callback for unregistering the listener
        # We register that callback here to get called when we are unloaded
        config_entry.async_on_unload(hass.bus.async_listen('knx_event', self.got_telegram))
        config_entry.async_on_unload(hass.bus.async_listen('state_changed', self.state_changed))

    async def state_changed(self, event):
        data = event.data
        other_id = data[ATTR_ENTITY_ID]
        domain = get_domain(other_id)
        if 'new_state' not in data.keys():
            return
        state = data['new_state']

        if domain == DOMAIN_LIGHT:
            # Also possible via native knx expose
            if other_id in self.entity_map[domain]['senders_onoff'].keys():
                address = self.entity_map[domain]['senders_onoff'][other_id]
                if state.state == STATE_ON:
                    _LOGGER.debug("Sending {} on -> {}".format(other_id, address))
                    payload = 1
                else:
                    _LOGGER.debug("Sending {} off -> {}".format(other_id, address))
                    payload = 0
                await self.hass.services.async_call(DOMAIN_KNX, SERVICE_KNX_SEND, { KNX_ADDRESS: address, SERVICE_KNX_ATTR_PAYLOAD: payload})

            if other_id in self.entity_map[domain]['senders_color'].keys() and ATTR_RGB_COLOR in state.attributes.keys():
                address = self.entity_map[domain]['senders_color'][other_id]
                rgb = state.attributes[ATTR_RGB_COLOR]
                payload = list(rgb)
                _LOGGER.debug("Sending {} color -> {}".format(other_id, address))
                await self.hass.services.async_call(DOMAIN_KNX, SERVICE_KNX_SEND, { KNX_ADDRESS: address, SERVICE_KNX_ATTR_PAYLOAD: payload})

            if other_id in self.entity_map[domain]['senders_brightness'].keys() and ATTR_BRIGHTNESS in state.attributes.keys():
                address = self.entity_map[domain]['senders_brightness'][other_id]
                brightness = state.attributes[ATTR_BRIGHTNESS]
                payload = [brightness] # XKNX requires a list for 1 byte payload
                _LOGGER.debug("Sending {} brightness -> {}".format(other_id, address))
                await self.hass.services.async_call(DOMAIN_KNX, SERVICE_KNX_SEND, { KNX_ADDRESS: address, SERVICE_KNX_ATTR_PAYLOAD: payload})
        elif domain == DOMAIN_SENSOR:
            # This is already handled by native knx expose
            pass


    async def got_telegram(self, event):
        data = event.data
        address = data['destination']
        if address in self.entity_map[DOMAIN_LIGHT]['receivers_onoff'].keys():
            other_id = self.entity_map[DOMAIN_LIGHT]['receivers_onoff'][address]
            payload = data['data']
            _LOGGER.debug("got data {} for {}".format(payload, other_id))
            if payload == 1:
                _LOGGER.debug("Turning {} on <- {}".format(other_id, address))
                await self.hass.services.async_call(DOMAIN_LIGHT, SERVICE_TURN_ON, { ATTR_ENTITY_ID: other_id })
            elif payload == 0:
                _LOGGER.debug("Turning {} off <- {}".format(other_id, address))
                await self.hass.services.async_call(DOMAIN_LIGHT, SERVICE_TURN_OFF, { ATTR_ENTITY_ID: other_id })

        if address in self.entity_map[DOMAIN_LIGHT]['receivers_color'].keys():
            other_id = self.entity_map[DOMAIN_LIGHT]['receivers_color'][address]
            payload = data['data']
            if len(payload) == 3:
                _LOGGER.debug("Turning {} on with color <- {}".format(other_id, address))
                await self.hass.services.async_call(DOMAIN_LIGHT, SERVICE_TURN_ON, { ATTR_ENTITY_ID: other_id, ATTR_RGB_COLOR: payload })

        if address in self.entity_map[DOMAIN_LIGHT]['receivers_brightness'].keys():
            other_id = self.entity_map[DOMAIN_LIGHT]['receivers_brightness'][address]
            payload = data['data']
            if payload[0] == 0:
                _LOGGER.debug("Turning {} off with brightness <- {}".format(other_id, address))
                await self.hass.services.async_call(DOMAIN_LIGHT, SERVICE_TURN_OFF, { ATTR_ENTITY_ID: other_id })
            else:
                _LOGGER.debug("Turning {} on with brightness <- {}".format(other_id, address))
                await self.hass.services.async_call(DOMAIN_LIGHT, SERVICE_TURN_ON, { ATTR_ENTITY_ID: other_id, ATTR_BRIGHTNESS: payload[0] })