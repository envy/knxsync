import logging
import asyncio

from .const import (
    DOMAIN,
    TELEGRAMTYPE_READ,
    TELEGRAMTYPE_WRITE,
    CONF_KNXSYNC_LIGHT_ZERO_BRIGHTNESS_WHEN_OFF
)
from .base import SyncedEntity
from .helpers import get_domain, get_id

from homeassistant.core import Event, State, HomeAssistant
from homeassistant.const import ATTR_ENTITY_ID, CONF_ENTITY_ID, CONF_ADDRESS, SERVICE_TURN_ON, SERVICE_TURN_OFF, STATE_ON
from homeassistant.components.light import DOMAIN as DOMAIN_LIGHT, ATTR_RGB_COLOR, ATTR_BRIGHTNESS
from homeassistant.components.knx import (
    DOMAIN as DOMAIN_KNX,
    SERVICE_KNX_SEND,
    SERVICE_KNX_ATTR_PAYLOAD,
    SERVICE_KNX_ATTR_RESPONSE,
    SERVICE_KNX_EVENT_REGISTER
)
from homeassistant.components.knx.const import CONF_STATE_ADDRESS, KNX_ADDRESS
from homeassistant.components.knx.schema import LightSchema

from xknx.dpt.dpt_2byte_float import DPT2ByteFloat
from xknx.dpt.dpt_2byte_signed import DPT2ByteSigned

_LOGGER = logging.getLogger(DOMAIN)

class SyncedLight(SyncedEntity):
    def __init__(self, hass: HomeAssistant, synced_entity_id: str, entity_config: dict):
        super().__init__(hass, synced_entity_id, entity_config)
        self.address: str | None = None
        self.state_address: str | None = None
        self.brightness_address: str | None = None
        self.brightness_state_address: str | None = None
        self.zero_brightness_when_off: bool | None = None
        self.color_address: str | None = None
        self.color_state_address: str | None = None
        _LOGGER.debug(f"Setting up synced light '{self.synced_entity_id}'")

        if CONF_ADDRESS in entity_config.keys():
            self.address = entity_config[CONF_ADDRESS]
            _LOGGER.debug(f"{self.synced_entity_id} <- {self.address}")

        if CONF_STATE_ADDRESS in entity_config.keys():
            self.state_address = entity_config[CONF_STATE_ADDRESS]
            _LOGGER.debug(f"{self.synced_entity_id} -> {self.state_address}")

        if LightSchema.CONF_BRIGHTNESS_ADDRESS in entity_config.keys():
            self.brightness_address = entity_config[LightSchema.CONF_BRIGHTNESS_ADDRESS]
            _LOGGER.debug(f"{self.synced_entity_id} <- {self.brightness_address}")

        if LightSchema.CONF_BRIGHTNESS_STATE_ADDRESS in entity_config.keys():
            self.brightness_state_address = entity_config[LightSchema.CONF_BRIGHTNESS_STATE_ADDRESS]
            _LOGGER.debug(f"{self.synced_entity_id} -> {self.brightness_state_address}")

        if CONF_KNXSYNC_LIGHT_ZERO_BRIGHTNESS_WHEN_OFF in entity_config.keys():
            self.zero_brightness_when_off = entity_config[CONF_KNXSYNC_LIGHT_ZERO_BRIGHTNESS_WHEN_OFF]
            _LOGGER.debug(f"{self.synced_entity_id} will also report off as 0% brightness.")

        if LightSchema.CONF_COLOR_ADDRESS in entity_config.keys():
            self.color_address = entity_config[LightSchema.CONF_COLOR_ADDRESS]
            _LOGGER.debug(f"{self.synced_entity_id} <- {self.color_address}")

        if LightSchema.CONF_COLOR_STATE_ADDRESS in entity_config.keys():
            self.color_state_address = entity_config[LightSchema.CONF_COLOR_STATE_ADDRESS]
            _LOGGER.debug(f"{self.synced_entity_id} -> {self.color_state_address}")

    async def async_got_telegram(self, event: Event) -> None:
        data = event.data
        address = data['destination']
        type = data['telegramtype']

        if type == TELEGRAMTYPE_WRITE:
            if address == self.address:
                payload = data['data']
                if payload == 1:
                    _LOGGER.debug(f"Turning {self.synced_entity_id} on <- {self.address}")
                    await self.hass.services.async_call(DOMAIN_LIGHT, SERVICE_TURN_ON, { ATTR_ENTITY_ID: self.synced_entity_id })
                elif payload == 0:
                    _LOGGER.debug(f"Turning {self.synced_entity_id} off <- {self.address}")
                    await self.hass.services.async_call(DOMAIN_LIGHT, SERVICE_TURN_OFF, { ATTR_ENTITY_ID: self.synced_entity_id })

            if address == self.brightness_address:
                payload = data['data']
                if payload[0] == 0:
                    _LOGGER.debug(f"Turning {self.synced_entity_id} off with brightness <- {self.brightness_address}")
                    await self.hass.services.async_call(DOMAIN_LIGHT, SERVICE_TURN_OFF, { ATTR_ENTITY_ID: self.synced_entity_id })
                else:
                    _LOGGER.debug(f"Turning {self.synced_entity_id} on with brightness <- {self.brightness_address}")
                    await self.hass.services.async_call(DOMAIN_LIGHT, SERVICE_TURN_ON, { ATTR_ENTITY_ID: self.synced_entity_id, ATTR_BRIGHTNESS: payload[0] })

            if address == self.color_address:
                payload = data['data']
                if len(payload) == 3:
                    _LOGGER.debug(f"Turning {self.synced_entity_id} on with color <- {self.color_address}")
                    await self.hass.services.async_call(DOMAIN_LIGHT, SERVICE_TURN_ON, { ATTR_ENTITY_ID: self.synced_entity_id, ATTR_RGB_COLOR: payload })
        elif type == TELEGRAMTYPE_READ and self.answer_reads and self.state is not None:
            _LOGGER.debug(f"Reading state for {self.synced_entity_id} <- {address}")
            if self.state_address == address:
                await self._send_onoff(True)
            if self.brightness_state_address == address:
                await self._send_brightness(True)
            if self.color_state_address == address:
                await self._send_color(True)

    async def async_state_changed(self, event: Event) -> None:
        data = event.data

        if 'new_state' not in data.keys():
            return
        self.state = data['new_state']

        if self.state_address is not None:
            await self._send_onoff()
        if self.brightness_state_address is not None and ATTR_BRIGHTNESS in self.state.attributes.keys():
            await self._send_brightness()
        if self.color_state_address is not None and ATTR_RGB_COLOR in self.state.attributes.keys():
            await self._send_color()

    async def async_setup_events(self) -> None:
        if self.address is not None:
            _LOGGER.debug(f"registering receiver {self.address} -> {self.synced_entity_id}")
            await self.hass.services.async_call(DOMAIN_KNX, SERVICE_KNX_EVENT_REGISTER, { KNX_ADDRESS: self.address })

        if self.brightness_address is not None:
            _LOGGER.debug(f"registering receiver {self.brightness_address} -> {self.synced_entity_id}")
            await self.hass.services.async_call(DOMAIN_KNX, SERVICE_KNX_EVENT_REGISTER, { KNX_ADDRESS: self.brightness_address })

        if self.color_address is not None:
            _LOGGER.debug(f"registering receiver {self.color_address} -> {self.synced_entity_id}")
            await self.hass.services.async_call(DOMAIN_KNX, SERVICE_KNX_EVENT_REGISTER, { KNX_ADDRESS: self.color_address })

        if not self.answer_reads:
            return
        # Register for potential reads
        if self.state_address is not None:
            _LOGGER.debug(f"registering receiver {self.state_address} <- {self.synced_entity_id}")
            await self.hass.services.async_call(DOMAIN_KNX, SERVICE_KNX_EVENT_REGISTER, { KNX_ADDRESS: self.state_address })
        if self.brightness_state_address is not None:
            _LOGGER.debug(f"registering receiver {self.brightness_state_address} <- {self.synced_entity_id}")
            await self.hass.services.async_call(DOMAIN_KNX, SERVICE_KNX_EVENT_REGISTER, { KNX_ADDRESS: self.brightness_state_address })
        if self.color_state_address is not None:
            _LOGGER.debug(f"registering receiver {self.color_state_address} <- {self.synced_entity_id}")
            await self.hass.services.async_call(DOMAIN_KNX, SERVICE_KNX_EVENT_REGISTER, { KNX_ADDRESS: self.color_state_address })

    async def _send_onoff(self, response: bool = False) -> None:
        if self.state == None:
            return
        if self.state.state == STATE_ON:
            _LOGGER.debug(f"Sending {self.synced_entity_id} on -> {self.state_address}")
            payload = 1
        else:
            _LOGGER.debug(f"Sending {self.synced_entity_id} off -> {self.state_address}")
            payload = 0
        await self.hass.services.async_call(DOMAIN_KNX, SERVICE_KNX_SEND, { KNX_ADDRESS: self.state_address, SERVICE_KNX_ATTR_PAYLOAD: payload, SERVICE_KNX_ATTR_RESPONSE: response})
        if not response and self.brightness_state_address is not None and self.zero_brightness_when_off and payload == 0:
            payload = [0]
            await self.hass.services.async_call(DOMAIN_KNX, SERVICE_KNX_SEND, { KNX_ADDRESS: self.brightness_state_address, SERVICE_KNX_ATTR_PAYLOAD: payload})

    async def _send_brightness(self, response: bool = False) -> None:
        if self.state == None:
            return
        brightness = self.state.attributes[ATTR_BRIGHTNESS]
        payload = [brightness] # XKNX requires a list for 1 byte payload
        _LOGGER.debug(f"Sending {self.synced_entity_id} brightness -> {self.brightness_state_address}")
        await self.hass.services.async_call(DOMAIN_KNX, SERVICE_KNX_SEND, { KNX_ADDRESS: self.brightness_state_address, SERVICE_KNX_ATTR_PAYLOAD: payload, SERVICE_KNX_ATTR_RESPONSE: response})

    async def _send_color(self, reponse: bool = False) -> None:
        if self.state == None:
            return
        rgb = self.state.attributes[ATTR_RGB_COLOR]
        payload = list(rgb)
        _LOGGER.debug(f"Sending {self.synced_entity_id} color -> {self.color_state_address}")
        await self.hass.services.async_call(DOMAIN_KNX, SERVICE_KNX_SEND, { KNX_ADDRESS: self.color_state_address, SERVICE_KNX_ATTR_PAYLOAD: payload, SERVICE_KNX_ATTR_RESPONSE: reponse})
