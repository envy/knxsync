"""
A component which syncs a HA device to KNX

For more details about this component, please refer to the documentation at
https://github.com/envy/knxsync
"""
import logging

import voluptuous as vol
from homeassistant.const import ATTR_ENTITY_ID, CONF_ENTITIES, CONF_ENTITY_ID, CONF_ADDRESS, SERVICE_TURN_ON, SERVICE_TURN_OFF, STATE_ON
from homeassistant.components.light import DOMAIN as DOMAIN_LIGHT, ATTR_RGB_COLOR, ATTR_BRIGHTNESS
from homeassistant.components.knx import DOMAIN as DOMAIN_KNX, SERVICE_KNX_SEND, SERVICE_KNX_ATTR_ADDRESS, SERVICE_KNX_ATTR_PAYLOAD 
from homeassistant.components.knx.light import CONF_STATE_ADDRESS, CONF_BRIGHTNESS_ADDRESS, CONF_BRIGHTNESS_STATE_ADDRESS, CONF_COLOR_ADDRESS, CONF_COLOR_STATE_ADDRESS
import homeassistant.helpers.config_validation as cv

VERSION = '0.0.1'

_LOGGER = logging.getLogger(__name__)

DATA_KNXSYNC = 'data_knxsync'

DOMAIN = 'knxsync'

CONF_BRIGHTNESS_STEP_ADDRESS = 'brightness_step_address'

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_ENTITIES): vol.All(cv.ensure_list, [vol.Schema({
            vol.Required(CONF_ENTITY_ID): cv.string,
            vol.Optional(CONF_ADDRESS) : cv.string,
            vol.Optional(CONF_STATE_ADDRESS): cv.string,
            vol.Optional(CONF_BRIGHTNESS_ADDRESS) : cv.string,
            vol.Optional(CONF_BRIGHTNESS_STEP_ADDRESS) : cv.string,
            vol.Optional(CONF_BRIGHTNESS_STATE_ADDRESS): cv.string,
            vol.Optional(CONF_COLOR_ADDRESS) : cv.string,
            vol.Optional(CONF_COLOR_STATE_ADDRESS): cv.string
        }, extra=vol.ALLOW_EXTRA)])
    })
}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass, config):
    """Set up this component."""
    _LOGGER.info('if you have ANY issues with knxsync, please report them here:'
                 ' https://github.com/envy/knxsync')

    _LOGGER.debug('KNXSync Version %s', VERSION)

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
        self.receivers_brightness_step = {}
        self.receivers_color = {}
        self.senders_onoff = {}
        self.senders_brightness = {}
        self.senders_color = {}
        self.hass = hass

        entities = config[DOMAIN][CONF_ENTITIES]
        _LOGGER.debug("entities: {}".format(entities))

        for entity in entities:
            other_id = entity[CONF_ENTITY_ID]
            _LOGGER.debug("syncing {} to KNX".format(other_id))

            if get_domain(other_id) == 'light':
                if CONF_ADDRESS in entity.keys():
                    _LOGGER.debug("registering receiver {} -> {}".format(entity[CONF_ADDRESS], other_id))
                    self.receivers_onoff[entity[CONF_ADDRESS]] = other_id

                if CONF_STATE_ADDRESS in entity.keys():
                    _LOGGER.debug("registering sender {} -> {}".format(other_id, entity[CONF_STATE_ADDRESS]))
                    self.senders_onoff[other_id] = entity[CONF_STATE_ADDRESS]

                if CONF_BRIGHTNESS_ADDRESS in entity.keys():
                    _LOGGER.debug("registering receiver {} -> {}".format(entity[CONF_BRIGHTNESS_ADDRESS], other_id))
                    self.receivers_brightness[entity[CONF_BRIGHTNESS_ADDRESS]] = other_id

                if CONF_BRIGHTNESS_STEP_ADDRESS in entity.keys():
                    _LOGGER.debug("registering receiver {} -> {}".format(entity[CONF_BRIGHTNESS_ADDRESS], other_id))
                    self.receivers_brightness_step[entity[CONF_BRIGHTNESS_ADDRESS]] = other_id

                if CONF_BRIGHTNESS_STATE_ADDRESS in entity.keys():
                    _LOGGER.debug("registering sender {} -> {}".format(other_id, entity[CONF_BRIGHTNESS_STATE_ADDRESS]))
                    self.senders_brightness[other_id] = entity[CONF_BRIGHTNESS_STATE_ADDRESS]

                if CONF_COLOR_ADDRESS in entity.keys():
                    _LOGGER.debug("registering receiver {} -> {}".format(entity[CONF_COLOR_ADDRESS], other_id))
                    self.receivers_color[entity[CONF_COLOR_ADDRESS]] = other_id

                if CONF_COLOR_STATE_ADDRESS in entity.keys():
                    _LOGGER.debug("registering sender {} -> {}".format(other_id, entity[CONF_COLOR_STATE_ADDRESS]))
                    self.senders_color[other_id] = entity[CONF_COLOR_STATE_ADDRESS]

        hass.bus.async_listen('knx_event', self.got_telegram)
        hass.bus.async_listen('state_changed', self.state_changed)
    
    async def state_changed(self, event):
        data = event.data
        other_id = data[ATTR_ENTITY_ID]
        domain = get_domain(other_id)
        if 'new_state' not in data.keys():
            return

        state = data['new_state']
        if other_id in self.senders_onoff.keys():
            address = self.senders_onoff[other_id]
            if domain == DOMAIN_LIGHT:
                if state.state == STATE_ON:
                    _LOGGER.debug("Sending {} on -> {}".format(other_id, address))
                    payload = [1]
                else:
                    _LOGGER.debug("Sending {} off -> {}".format(other_id, address))
                    payload = [0]
                await self.hass.services.async_call(DOMAIN_KNX, SERVICE_KNX_SEND, { SERVICE_KNX_ATTR_ADDRESS: address, SERVICE_KNX_ATTR_PAYLOAD: payload})

        if other_id in self.senders_color.keys() and ATTR_RGB_COLOR in state.attributes.keys():
            address = self.senders_color[other_id]
            rgb = state.attributes[ATTR_RGB_COLOR]
            if domain == DOMAIN_LIGHT:
                payload = list(rgb)
                _LOGGER.debug("Sending {} color -> {}".format(other_id, address))
                await self.hass.services.async_call(DOMAIN_KNX, SERVICE_KNX_SEND, { SERVICE_KNX_ATTR_ADDRESS: address, SERVICE_KNX_ATTR_PAYLOAD: payload})

        if other_id in self.senders_brightness.keys() and ATTR_BRIGHTNESS in state.attributes.keys():
            address = self.senders_brightness[other_id]
            brightness = state.attributes[ATTR_BRIGHTNESS]
            if domain == DOMAIN_LIGHT:
                payload = [brightness] # XKNX requires a list for 1 byte payload
                _LOGGER.debug("Sending {} brightness -> {}".format(other_id, address))
                await self.hass.services.async_call(DOMAIN_KNX, SERVICE_KNX_SEND, { SERVICE_KNX_ATTR_ADDRESS: address, SERVICE_KNX_ATTR_PAYLOAD: payload})

    async def got_telegram(self, event):
        data = event.data
        address = data['address']
        if address in self.receivers_onoff.keys():
            other_id = self.receivers_onoff[address]
            payload = data['data']
            _LOGGER.debug("got data {} for {}".format(payload, other_id))
            if get_domain(other_id) == DOMAIN_LIGHT:
                if payload == 1:
                    _LOGGER.debug("Turning {} on <- {}".format(other_id, address))
                    await self.hass.services.async_call(DOMAIN_LIGHT, SERVICE_TURN_ON, { ATTR_ENTITY_ID: other_id })
                elif payload == 0:
                    _LOGGER.debug("Turning {} off <- {}".format(other_id, address))
                    await self.hass.services.async_call(DOMAIN_LIGHT, SERVICE_TURN_OFF, { ATTR_ENTITY_ID: other_id })

        if address in self.receivers_color.keys():
            other_id = self.receivers_color[address]
            payload = data['data']
            if get_domain(other_id) == DOMAIN_LIGHT:
                if len(payload) == 3:
                    _LOGGER.debug("Turning {} on with color <- {}".format(other_id, address))
                    await self.hass.services.async_call(DOMAIN_LIGHT, SERVICE_TURN_ON, { ATTR_ENTITY_ID: other_id, ATTR_RGB_COLOR: payload })

        if address in self.receivers_brightness.keys():
            other_id = self.receivers_brightness[address]
            payload = data['data']
            if get_domain(other_id) == DOMAIN_LIGHT:
                if payload[0] == 0:
                    _LOGGER.debug("Turning {} off with brightness <- {}".format(other_id, address))
                    await self.hass.services.async_call(DOMAIN_LIGHT, SERVICE_TURN_OFF, { ATTR_ENTITY_ID: other_id })
                else:
                    _LOGGER.debug("Turning {} on with brightness <- {}".format(other_id, address))
                    await self.hass.services.async_call(DOMAIN_LIGHT, SERVICE_TURN_ON, { ATTR_ENTITY_ID: other_id, ATTR_BRIGHTNESS: payload[0] })

        if address in self.receivers_brightness_step.keys():
            other_id = self.receivers_brightness_step[address]
            payload = data['data']
            if get_domain(other_id) == DOMAIN_LIGHT:
                if payload == 0:
                    # we need to stop
                    pass
                else:
                    sign = payload & 0b1000
                    # we assume the stepwidth is going to be 100%
                    if sign > 0:
                        # we need to increase brightness
                        pass
                    else:
                        # we need to decrease brightness
                        pass
                