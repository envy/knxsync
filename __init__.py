"""
A component which syncs a HA device to KNX

For more details about this component, please refer to the documentation at
https://github.com/envy/knxsync
"""
import logging
import asyncio

import voluptuous as vol

from .const import DOMAIN

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from homeassistant.const import ATTR_ENTITY_ID, CONF_ENTITIES, CONF_ENTITY_ID, CONF_ADDRESS, SERVICE_TURN_ON, SERVICE_TURN_OFF, STATE_ON
from homeassistant.components.light import DOMAIN as DOMAIN_LIGHT, ATTR_RGB_COLOR, ATTR_BRIGHTNESS
from homeassistant.components.sensor import DOMAIN as DOMAIN_SENSOR
from homeassistant.components.knx import DOMAIN as DOMAIN_KNX, SERVICE_KNX_SEND, SERVICE_KNX_ATTR_PAYLOAD 
from homeassistant.components.knx.const import CONF_STATE_ADDRESS, KNX_ADDRESS
from homeassistant.components.knx.schema import LightSchema
import homeassistant.helpers.config_validation as cv

from xknx.dpt.dpt_2byte_float import DPT2ByteFloat
from xknx.dpt.dpt_2byte_signed import DPT2ByteSigned

VERSION = '0.0.1'

_LOGGER = logging.getLogger(__name__)

#DATA_KNXSYNC = 'data_knxsync'

#async def async_setup(hass: HomeAssistant, config: dict) -> bool:
#    """Set up this component."""
#    _LOGGER.info('If you have ANY issues with knxsync, please report them here:'
#                 ' https://github.com/envy/knxsync')
#
#    _LOGGER.debug('KNXSync Version %s', VERSION)
#
#    hass.data.setdefault(DOMAIN, {})
#
#    #hass.data[DATA_KNXSYNC] = KNXSyncer(hass, config)
#    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data[DOMAIN][entry.entry_id] = KNXSyncer(hass, entry.data)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data[DOMAIN].pop(entry.entry_id)
    return True

def get_domain(eid: str) -> str:
    return eid.split('.')[0]

def get_id(eid: str) -> str:
    return eid.split('.')[1]

class KNXSyncer:
    def __init__(self, hass, config):
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

        entities = config[DOMAIN][CONF_ENTITIES]
        _LOGGER.debug("entities: {}".format(entities))

        for entity in entities:
            other_id = entity[CONF_ENTITY_ID]
            domain = get_domain(other_id)
            _LOGGER.debug("syncing {} to KNX".format(other_id))

            if domain == DOMAIN_LIGHT:
                if CONF_ADDRESS in entity.keys():
                    _LOGGER.debug("registering receiver {} -> {}".format(entity[CONF_ADDRESS], other_id))
                    self.entity_map[domain]['receivers_onoff'][entity[CONF_ADDRESS]] = other_id

                if CONF_STATE_ADDRESS in entity.keys():
                    _LOGGER.debug("registering sender {} -> {}".format(other_id, entity[CONF_STATE_ADDRESS]))
                    self.entity_map[domain]['senders_onoff'][other_id] = entity[CONF_STATE_ADDRESS]

                if LightSchema.CONF_BRIGHTNESS_ADDRESS in entity.keys():
                    _LOGGER.debug("registering receiver {} -> {}".format(entity[LightSchema.CONF_BRIGHTNESS_ADDRESS], other_id))
                    self.entity_map[domain]['receivers_brightness'][entity[LightSchema.CONF_BRIGHTNESS_ADDRESS]] = other_id

                if LightSchema.CONF_BRIGHTNESS_STATE_ADDRESS in entity.keys():
                    _LOGGER.debug("registering sender {} -> {}".format(other_id, entity[LightSchema.CONF_BRIGHTNESS_STATE_ADDRESS]))
                    self.entity_map[domain]['senders_brightness'][other_id] = entity[LightSchema.CONF_BRIGHTNESS_STATE_ADDRESS]

                if LightSchema.CONF_COLOR_ADDRESS in entity.keys():
                    _LOGGER.debug("registering receiver {} -> {}".format(entity[LightSchema.CONF_COLOR_ADDRESS], other_id))
                    self.entity_map[domain]['receivers_color'][entity[LightSchema.CONF_COLOR_ADDRESS]] = other_id

                if LightSchema.CONF_COLOR_STATE_ADDRESS in entity.keys():
                    _LOGGER.debug("registering sender {} -> {}".format(other_id, entity[LightSchema.CONF_COLOR_STATE_ADDRESS]))
                    self.entity_map[domain]['senders_color'][other_id] = entity[LightSchema.CONF_COLOR_STATE_ADDRESS]
            elif domain == DOMAIN_SENSOR:
                if CONF_STATE_ADDRESS in entity.keys():
                    _LOGGER.debug("registering sender {} -> {}".format(other_id, entity[CONF_STATE_ADDRESS]))
                    self.entity_map[domain]['senders_value'][other_id] = entity[CONF_STATE_ADDRESS]

        hass.bus.async_listen('knx_event', self.got_telegram)
        hass.bus.async_listen('state_changed', self.state_changed)
    
    async def state_changed(self, event):
        data = event.data
        other_id = data[ATTR_ENTITY_ID]
        domain = get_domain(other_id)
        if 'new_state' not in data.keys():
            return
        state = data['new_state']

        if domain == DOMAIN_LIGHT:
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
            if other_id in self.entity_map[domain]['senders_value'].keys():
                address = self.entity_map[domain]['senders_value'][other_id]
                value = state.state
                # TODO: maybe the datatype should be given in the config...
                try:
                    value = int(value)
                    payload = list(DPT2ByteSigned.to_knx(value))
                    await self.hass.services.async_call(DOMAIN_KNX, SERVICE_KNX_SEND, { KNX_ADDRESS: address, SERVICE_KNX_ATTR_PAYLOAD: payload})
                except ValueError:
                    try:
                        value = float(value)
                        payload = list(DPT2ByteFloat.to_knx(value))
                        await self.hass.services.async_call(DOMAIN_KNX, SERVICE_KNX_SEND, { KNX_ADDRESS: address, SERVICE_KNX_ATTR_PAYLOAD: payload})
                    except ValueError:
                        # Value is neither int nor float
                        return


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
