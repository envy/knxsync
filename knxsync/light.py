import logging

from .const import (
    KNXSyncEntityLightData,
    DOMAIN,
    TELEGRAMTYPE_READ,
    TELEGRAMTYPE_WRITE,
    CONF_KNXSYNC_LIGHT_ZERO_BRIGHTNESS_WHEN_OFF,
)
from .base import SyncedEntity

from homeassistant.core import Event, HomeAssistant
from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_ADDRESS,
    SERVICE_TURN_ON,
    SERVICE_TURN_OFF,
    STATE_ON,
    STATE_UNKNOWN,
    STATE_UNAVAILABLE,
)
from homeassistant.components.light import (
    DOMAIN as DOMAIN_LIGHT,
    ATTR_RGB_COLOR,
    ATTR_BRIGHTNESS,
)
from homeassistant.components.knx.const import (
    DOMAIN as DOMAIN_KNX,
    SERVICE_KNX_SEND,
    SERVICE_KNX_ATTR_PAYLOAD,
    SERVICE_KNX_ATTR_RESPONSE,
    CONF_STATE_ADDRESS,
    KNX_ADDRESS,
)
from homeassistant.components.knx.schema import LightSchema

_LOGGER = logging.getLogger(DOMAIN)


class SyncedLight(SyncedEntity):
    address: list[str]
    state_address: list[str]
    brightness_address: list[str]
    brightness_state_address: list[str]
    zero_brightness_when_off: bool
    color_address: list[str]
    color_state_address: list[str]

    def __init__(
        self,
        hass: HomeAssistant,
        synced_entity_id: str,
        entity_config: KNXSyncEntityLightData,
    ):
        super().__init__(hass, synced_entity_id, entity_config)
        _LOGGER.debug(f"Setting up synced light '{self.synced_entity_id}'")

        self._set_value_from_config(CONF_ADDRESS, list())
        self._set_value_from_config(CONF_STATE_ADDRESS, list())
        self._set_value_from_config(LightSchema.CONF_BRIGHTNESS_ADDRESS, list())
        self._set_value_from_config(LightSchema.CONF_BRIGHTNESS_STATE_ADDRESS, list())
        self._set_value_from_config(CONF_KNXSYNC_LIGHT_ZERO_BRIGHTNESS_WHEN_OFF, False)
        self._set_value_from_config(LightSchema.CONF_COLOR_ADDRESS, list())
        self._set_value_from_config(LightSchema.CONF_COLOR_STATE_ADDRESS, list())

    async def async_got_telegram(self, event: Event) -> None:
        data = event.data
        address = data["destination"]
        type = data["telegramtype"]

        if type == TELEGRAMTYPE_WRITE:
            if address in self.address:
                payload = data["data"]
                if payload == 1:
                    _LOGGER.debug(f"Turning {self.synced_entity_id} on <- {address}")
                    await self.hass.services.async_call(
                        DOMAIN_LIGHT,
                        SERVICE_TURN_ON,
                        {ATTR_ENTITY_ID: self.synced_entity_id},
                    )
                elif payload == 0:
                    _LOGGER.debug(f"Turning {self.synced_entity_id} off <- {address}")
                    await self.hass.services.async_call(
                        DOMAIN_LIGHT,
                        SERVICE_TURN_OFF,
                        {ATTR_ENTITY_ID: self.synced_entity_id},
                    )

            if address in self.brightness_address:
                payload = data["data"]
                if payload[0] == 0:
                    _LOGGER.debug(
                        f"Turning {self.synced_entity_id} off with brightness <- {address}"
                    )
                    await self.hass.services.async_call(
                        DOMAIN_LIGHT,
                        SERVICE_TURN_OFF,
                        {ATTR_ENTITY_ID: self.synced_entity_id},
                    )
                else:
                    _LOGGER.debug(
                        f"Turning {self.synced_entity_id} on with brightness <- {address}"
                    )
                    await self.hass.services.async_call(
                        DOMAIN_LIGHT,
                        SERVICE_TURN_ON,
                        {
                            ATTR_ENTITY_ID: self.synced_entity_id,
                            ATTR_BRIGHTNESS: payload[0],
                        },
                    )

            if address in self.color_address:
                payload = data["data"]
                if len(payload) == 3:
                    _LOGGER.debug(
                        f"Turning {self.synced_entity_id} on with color <- {address}"
                    )
                    await self.hass.services.async_call(
                        DOMAIN_LIGHT,
                        SERVICE_TURN_ON,
                        {
                            ATTR_ENTITY_ID: self.synced_entity_id,
                            ATTR_RGB_COLOR: payload,
                        },
                    )
        elif type == TELEGRAMTYPE_READ and self.answer_reads and self.state is not None:
            _LOGGER.debug(f"Reading state for {self.synced_entity_id} <- {address}")
            if address in self.state_address:
                await self._send_onoff(True)
            if address in self.brightness_state_address:
                await self._send_brightness(True)
            if address in self.color_state_address:
                await self._send_color(True)

    async def async_state_changed(self, event: Event) -> None:
        data = event.data

        if "new_state" not in data.keys():
            return
        self.state = data["new_state"]
        if self.state is None:
            return

        if self.state.state == STATE_UNKNOWN or self.state.state == STATE_UNAVAILABLE:
            _LOGGER.debug(f"{self.synced_entity_id} is unknown/unavailable")
            await self._send_onoff()
            return

        if self.state_address:
            await self._send_onoff()
        if (
            self.brightness_state_address
            and self.state.attributes[ATTR_BRIGHTNESS] is not None
        ):
            await self._send_brightness()
        if self.color_state_address and self.state.attributes[ATTR_RGB_COLOR] is not None:
            await self._send_color()

    async def async_setup_events(self) -> None:
        await self._register_receiver(CONF_ADDRESS)
        await self._register_receiver(LightSchema.CONF_BRIGHTNESS_ADDRESS)
        await self._register_receiver(LightSchema.CONF_COLOR_ADDRESS)

        if not self.answer_reads:
            return

        # Register for potential reads
        await self._register_receiver(CONF_STATE_ADDRESS)
        await self._register_receiver(LightSchema.CONF_BRIGHTNESS_STATE_ADDRESS)
        await self._register_receiver(LightSchema.CONF_COLOR_STATE_ADDRESS)

    async def _send_onoff(self, response: bool = False) -> None:
        if self.state == None:
            return
        if self.state.state == STATE_ON:
            _LOGGER.debug(f"Sending {self.synced_entity_id} on -> {self.state_address}")
            payload = 1
        else:
            _LOGGER.debug(
                f"Sending {self.synced_entity_id} off -> {self.state_address}"
            )
            payload = 0
        for address in self.state_address:
            await self.hass.services.async_call(
                DOMAIN_KNX,
                SERVICE_KNX_SEND,
                {
                    KNX_ADDRESS: address,
                    SERVICE_KNX_ATTR_PAYLOAD: payload,
                    SERVICE_KNX_ATTR_RESPONSE: response,
                },
            )
        if (
            not response
            and self.brightness_state_address is not None
            and self.zero_brightness_when_off
            and payload == 0
        ):
            payload = [0]
            for address in self.brightness_state_address:
                await self.hass.services.async_call(
                    DOMAIN_KNX,
                    SERVICE_KNX_SEND,
                    {KNX_ADDRESS: address, SERVICE_KNX_ATTR_PAYLOAD: payload},
                )

    async def _send_brightness(self, response: bool = False) -> None:
        if self.state == None:
            return
        brightness = self.state.attributes[ATTR_BRIGHTNESS]
        if brightness is None:
            return
        # brightness is an int between 0 and 255, no conversion needed
        payload = [brightness]  # XKNX requires a list for 1 byte payload
        _LOGGER.debug(
            f"Sending {self.synced_entity_id} brightness -> {self.brightness_state_address}"
        )
        for address in self.brightness_state_address:
            await self.hass.services.async_call(
                DOMAIN_KNX,
                SERVICE_KNX_SEND,
                {
                    KNX_ADDRESS: address,
                    SERVICE_KNX_ATTR_PAYLOAD: payload,
                    SERVICE_KNX_ATTR_RESPONSE: response,
                },
            )

    async def _send_color(self, reponse: bool = False) -> None:
        if self.state == None:
            return
        rgb = self.state.attributes[ATTR_RGB_COLOR]
        if rgb is None:
            return
        # rgb is a tuple, so convert to a list
        payload = list(rgb)
        _LOGGER.debug(
            f"Sending {self.synced_entity_id} color -> {self.color_state_address}"
        )
        for address in self.color_state_address:
            await self.hass.services.async_call(
                DOMAIN_KNX,
                SERVICE_KNX_SEND,
                {
                    KNX_ADDRESS: address,
                    SERVICE_KNX_ATTR_PAYLOAD: payload,
                    SERVICE_KNX_ATTR_RESPONSE: reponse,
                },
            )
