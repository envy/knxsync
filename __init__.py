"""
A component which syncs a HA device to KNX

For more details about this component, please refer to the documentation at
https://github.com/envy/knxsync
"""
import logging

import voluptuous as vol
from aiohttp import web
from homeassistant.const import ATTR_ENTITY_ID, CONF_ADDRESS, STATE_ON, STATE_OFF
from homeassistant.components.knx.light import CONF_STATE_ADDRESS, CONF_BRIGHTNESS_ADDRESS, CONF_BRIGHTNESS_STATE_ADDRESS, CONF_COLOR_ADDRESS, CONF_COLOR_STATE_ADDRESS
import homeassistant.helpers.config_validation as cv

VERSION = '0.0.1'

_LOGGER = logging.getLogger(__name__)

DATA_KNXSYNC = 'data_knxsync'

DOMAIN = 'knxsync'
DOMAIN_KNX = 'knx'

CONF_SYNC = 'sync'
CONF_OTHER_ID = 'other_id'

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_SYNC): vol.All(cv.ensure_list, [vol.Schema({
            vol.Required(CONF_OTHER_ID): cv.string,
            vol.Optional(CONF_ADDRESS) : cv.string,
            vol.Optional(CONF_STATE_ADDRESS): cv.string,
            vol.Optional(CONF_BRIGHTNESS_ADDRESS) : cv.string,
            vol.Optional(CONF_BRIGHTNESS_STATE_ADDRESS): cv.string,
            vol.Optional(CONF_COLOR_ADDRESS) : cv.string,
            vol.Optional(CONF_COLOR_STATE_ADDRESS): cv.string
        }, extra=vol.ALLOW_EXTRA)])
    })
}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass, config):
    """Set up this component."""
    _LOGGER.info('if you have ANY issues with this, please report them here:'
                 ' https://github.com/envy/knxsync')

    _LOGGER.debug('Version %s', VERSION)

    hass.data[DATA_KNXSYNC] = KNXSyncer(hass, config)
    return True

def get_domain(eid: str):
    return eid.split('.')[0]

def get_id(eid: str):
    return eid.split('.')[1]

class KNXSyncer:
    def __init__(self, hass, config):
        self.receivers_onoff = {}
        self.receivers_brightness = {}
        self.receivers_color = {}
        self.senders_onoff = {}
        self.senders_brightness = {}
        self.senders_color = {}
        self.hass = hass

        syncs = config[DOMAIN][CONF_SYNC]
        _LOGGER.debug("syncs: {}".format(syncs))

        for sync in syncs:
            other_id = sync[CONF_OTHER_ID]
            _LOGGER.debug("syncing {} to KNX".format(other_id))

            if get_domain(other_id) == 'light':
                if CONF_ADDRESS in sync.keys():
                    _LOGGER.debug("registering receiver {} -> {}".format(sync[CONF_ADDRESS], other_id))
                    self.receivers_onoff[sync[CONF_ADDRESS]] = other_id
                
                if CONF_STATE_ADDRESS in sync.keys():
                    _LOGGER.debug("registering sender {} -> {}".format(other_id, sync[CONF_STATE_ADDRESS]))
                    self.senders_onoff[other_id] = sync[CONF_STATE_ADDRESS]
                
                if CONF_BRIGHTNESS_ADDRESS in sync.keys():
                    _LOGGER.debug("registering receiver {} -> {}".format(sync[CONF_BRIGHTNESS_ADDRESS], other_id))
                    self.receivers_brightness[sync[CONF_BRIGHTNESS_ADDRESS]] = other_id
                
                if CONF_BRIGHTNESS_STATE_ADDRESS in sync.keys():
                    _LOGGER.debug("registering sender {} -> {}".format(other_id, sync[CONF_BRIGHTNESS_STATE_ADDRESS]))
                    self.senders_brightness[other_id] = sync[CONF_BRIGHTNESS_STATE_ADDRESS]

                if CONF_COLOR_ADDRESS in sync.keys():
                    _LOGGER.debug("registering receiver {} -> {}".format(sync[CONF_COLOR_ADDRESS], other_id))
                    self.receivers_color[sync[CONF_COLOR_ADDRESS]] = other_id
                
                if CONF_COLOR_STATE_ADDRESS in sync.keys():
                    _LOGGER.debug("registering sender {} -> {}".format(other_id, sync[CONF_COLOR_STATE_ADDRESS]))
                    self.senders_color[other_id] = sync[CONF_COLOR_STATE_ADDRESS]

        hass.bus.async_listen('knx_event', self.got_telegram)
        hass.bus.async_listen('state_changed', self.state_changed)
    
    async def state_changed(self, event):
        from homeassistant.components.light import ATTR_RGB_COLOR
        data = event.data
        other_id = data[ATTR_ENTITY_ID]
        domain = get_domain(other_id)
        if 'new_state' in data.keys():
            state = data['new_state']
            if other_id in self.senders_onoff.keys():
                address = self.senders_onoff[other_id]
                if domain == 'light':
                    if state.state == STATE_ON:
                        _LOGGER.debug("Sending {} on -> {}".format(other_id, address))
                        payload = [1]
                    else:
                        _LOGGER.debug("Sending {} off -> {}".format(other_id, address))
                        payload = [0]
                    await self.hass.services.async_call('knx', 'send', { 'address': address, 'payload': payload})

            if other_id in self.senders_color.keys() and ATTR_RGB_COLOR in state.attributes.keys():
                address = self.senders_color[other_id]
                rgb = state.attributes[ATTR_RGB_COLOR]
                if domain == 'light':
                    payload = list(rgb)
                    _LOGGER.debug("Sending {} color -> {}".format(other_id, address))
                    await self.hass.services.async_call('knx', 'send', { 'address': address, 'payload': payload})

            if other_id in self.senders_brightness.keys() and 'brightness' in state.attributes.keys():
                address = self.senders_brightness[other_id]
                brightness = state.attributes['brightness']
                if domain == 'light':
                    payload = [brightness] # XKNX requires a list for 1 byte payload
                    _LOGGER.debug("Sending {} brightness -> {}".format(other_id, address))
                    await self.hass.services.async_call('knx', 'send', { 'address': address, 'payload': payload})

    async def got_telegram(self, event):
        data = event.data
        address = data['address']
        if address in self.receivers_onoff.keys():
            other_id = self.receivers_onoff[address]
            payload = data['data']
            _LOGGER.debug("got data {} for {}".format(payload, other_id))
            if get_domain(other_id) == 'light':
                if payload == 1:
                    _LOGGER.debug("Turning {} on <- {}".format(other_id, address))
                    await self.hass.services.async_call('light', 'turn_on', { 'entity_id': other_id })
                elif payload == 0:
                    _LOGGER.debug("Turning {} off <- {}".format(other_id, address))
                    await self.hass.services.async_call('light', 'turn_off', { 'entity_id': other_id })
            
        if address in self.receivers_color.keys():
            other_id = self.receivers_color[address]
            payload = data['data']
            if get_domain(other_id) == 'light':
                if len(payload) == 3:
                    _LOGGER.debug("Turning {} on with color <- {}".format(other_id, address))
                    await self.hass.services.async_call('light', 'turn_on', { 'entity_id': other_id, 'rgb_color': payload })

        if address in self.receivers_brightness.keys():
            other_id = self.receivers_brightness[address]
            payload = data['data']
            if get_domain(other_id) == 'light':
                if payload[0] == 0:
                    _LOGGER.debug("Turning {} off with brightness <- {}".format(other_id, address))
                    await self.hass.services.async_call('light', 'turn_off', { 'entity_id': other_id })
                else:
                    _LOGGER.debug("Turning {} oon with brightness <- {}".format(other_id, address))
                    await self.hass.services.async_call('light', 'turn_on', { 'entity_id': other_id, 'brightness': payload[0] })
