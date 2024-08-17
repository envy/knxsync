import logging

from typing import Final

from .const import (
    KNXSyncEntityClimateData,
    DOMAIN,
    TELEGRAMTYPE_READ,
    TELEGRAMTYPE_WRITE,
)
from .base import SyncedEntity

from homeassistant.core import Event, HomeAssistant
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.components.climate import (
    DOMAIN as DOMAIN_CLIMATE,
    ATTR_CURRENT_TEMPERATURE,
    ATTR_TEMPERATURE,
    ATTR_HVAC_MODE,
    ATTR_HVAC_MODES,
    SERVICE_SET_TEMPERATURE,
    SERVICE_SET_HVAC_MODE,
    HVACMode,
)
from homeassistant.components.knx.schema import ClimateSchema
from homeassistant.components.knx.const import (
    DOMAIN as DOMAIN_KNX,
    SERVICE_KNX_SEND,
    SERVICE_KNX_ATTR_PAYLOAD,
    SERVICE_KNX_ATTR_RESPONSE,
    SERVICE_KNX_ATTR_TYPE,
    KNX_ADDRESS,
)
from xknx.dpt.dpt_9 import DPT2ByteFloat
from xknx.dpt.dpt_20 import DPTHVACContrMode, HVACControllerMode
from xknx.dpt.payload import DPTArray

_LOGGER = logging.getLogger(DOMAIN)

HA_HVAC_CONTROLLER_MODE_MAP: Final = {
    HVACMode.AUTO: HVACControllerMode.AUTO,
    HVACMode.COOL: HVACControllerMode.COOL,
    HVACMode.DRY: HVACControllerMode.DEHUMIDIFICATION,
    HVACMode.FAN_ONLY: HVACControllerMode.FAN_ONLY,
    HVACMode.HEAT: HVACControllerMode.HEAT,
    # HVACMode.HEAT_COOL: HVACControllerMode.AUTO,
    HVACMode.OFF: HVACControllerMode.OFF,
}

XKNX_HVAC_CONTROLLER_MODE_MAP = dict(
    (v, k) for k, v in HA_HVAC_CONTROLLER_MODE_MAP.items()
)


def ha_to_xknx_controller_mode(ha: HVACMode) -> HVACControllerMode:
    return HA_HVAC_CONTROLLER_MODE_MAP[ha]


def xknx_to_ha_controller_mode(knx: HVACControllerMode) -> HVACMode:
    return XKNX_HVAC_CONTROLLER_MODE_MAP[knx]


class SyncedClimate(SyncedEntity):
    temperature_address: list[str]
    target_temperature_address: list[str]
    target_temperature_state_address: list[str]
    operation_mode_address: list[str]
    operation_mode_state_address: list[str]
    controller_mode_address: list[str]
    controller_mode_state_address: list[str]

    def __init__(
        self,
        hass: HomeAssistant,
        synced_entity_id: str,
        entity_config: KNXSyncEntityClimateData,
    ):
        super().__init__(hass, synced_entity_id, entity_config)

        _LOGGER.debug(f"Setting up synced climate '{self.synced_entity_id}'")

        self._set_value_from_config(ClimateSchema.CONF_TEMPERATURE_ADDRESS, list())
        self._set_value_from_config(
            ClimateSchema.CONF_TARGET_TEMPERATURE_ADDRESS, list()
        )
        self._set_value_from_config(
            ClimateSchema.CONF_TARGET_TEMPERATURE_STATE_ADDRESS, list()
        )
        self._set_value_from_config(ClimateSchema.CONF_OPERATION_MODE_ADDRESS, list())
        self._set_value_from_config(
            ClimateSchema.CONF_OPERATION_MODE_STATE_ADDRESS, list()
        )
        self._set_value_from_config(ClimateSchema.CONF_CONTROLLER_MODE_ADDRESS, list())
        self._set_value_from_config(
            ClimateSchema.CONF_CONTROLLER_MODE_STATE_ADDRESS, list()
        )

    async def async_got_telegram(self, event: Event) -> None:
        data = event.data
        address = data["destination"]
        type = data["telegramtype"]

        if type == TELEGRAMTYPE_WRITE:
            payload = data["data"]
            if address in self.target_temperature_address:
                value = DPT2ByteFloat.from_knx(DPTArray(payload))
                _LOGGER.debug(
                    f"Setting setpoint of {self.synced_entity_id} <- {address}"
                )
                await self.hass.services.async_call(
                    DOMAIN_CLIMATE,
                    SERVICE_SET_TEMPERATURE,
                    {ATTR_ENTITY_ID: self.synced_entity_id, ATTR_TEMPERATURE: value},
                )
            if address in self.controller_mode_address:
                value = xknx_to_ha_controller_mode(
                    DPTHVACContrMode.from_knx(DPTArray(payload))
                )
                _LOGGER.debug(
                    f"Setting operation mode of {self.synced_entity_id} <- {address}"
                )
                if self.state != None:
                    if value in self.state.attributes[ATTR_HVAC_MODES]:
                        await self.hass.services.async_call(
                            DOMAIN_CLIMATE,
                            SERVICE_SET_HVAC_MODE,
                            {
                                ATTR_ENTITY_ID: self.synced_entity_id,
                                ATTR_HVAC_MODE: value,
                            },
                        )
                    else:
                        _LOGGER.error(
                            f"Could not set controller mode of {self.synced_entity_id}: Requested mode '{value}' is not in reported available modes '{self.state.attributes[ATTR_HVAC_MODES]}'"
                        )
                else:
                    _LOGGER.error(
                        f"Could not set controller mode of {self.synced_entity_id}: No state available to check if mode is suported."
                    )
        elif type == TELEGRAMTYPE_READ and self.answer_reads and self.state is not None:
            _LOGGER.debug(f"Reading state for {self.synced_entity_id} <- {address}")
            if address in self.temperature_address:
                await self._send_current_temperature(True)
            if address in self.target_temperature_state_address:
                await self._send_setpoint_temperature(True)
            if address in self.controller_mode_state_address:
                await self._send_controller_mode(True)

    async def async_state_changed(self, event: Event) -> None:
        data = event.data

        if "new_state" not in data.keys():
            return
        self.state = data["new_state"]

        _LOGGER.debug(f"new state: {self.state}")

        if (
            self.temperature_address
            and self.state.attributes[ATTR_CURRENT_TEMPERATURE] is not None
        ):
            await self._send_current_temperature()
        if (
            self.target_temperature_state_address
            and self.state.attributes[ATTR_TEMPERATURE] is not None
        ):
            await self._send_setpoint_temperature()
        if self.controller_mode_state_address:
            await self._send_controller_mode()

    async def _send_current_temperature(self, response: bool = False) -> None:
        if self.state == None:
            return
        current_temperature = self.state.attributes[ATTR_CURRENT_TEMPERATURE]
        _LOGGER.debug(
            f"Sending {self.synced_entity_id} current temperature -> {self.temperature_address}"
        )
        payload = current_temperature
        for address in self.temperature_address:
            await self.hass.services.async_call(
                DOMAIN_KNX,
                SERVICE_KNX_SEND,
                {
                    KNX_ADDRESS: address,
                    SERVICE_KNX_ATTR_PAYLOAD: payload,
                    SERVICE_KNX_ATTR_TYPE: "temperature",
                    SERVICE_KNX_ATTR_RESPONSE: response,
                },
            )

    async def _send_setpoint_temperature(self, response: bool = False) -> None:
        if self.state == None:
            return
        setpoint_temperature = self.state.attributes[ATTR_TEMPERATURE]
        if setpoint_temperature is None:
            return
        payload = setpoint_temperature
        _LOGGER.debug(
            f"Sending {self.synced_entity_id} setpoint temperarute -> {self.target_temperature_state_address}"
        )
        for address in self.target_temperature_state_address:
            await self.hass.services.async_call(
                DOMAIN_KNX,
                SERVICE_KNX_SEND,
                {
                    KNX_ADDRESS: address,
                    SERVICE_KNX_ATTR_PAYLOAD: payload,
                    SERVICE_KNX_ATTR_TYPE: "temperature",
                    SERVICE_KNX_ATTR_RESPONSE: response,
                },
            )

    async def _send_controller_mode(self, response: bool = False) -> None:
        if self.state == None:
            return
        op_mode = self.state.state
        if op_mode is None:
            return
        payload = list(
            DPTHVACContrMode.to_knx(ha_to_xknx_controller_mode(op_mode)).value
        )
        _LOGGER.debug(
            f"Sending {self.synced_entity_id} controller mode -> {self.controller_mode_state_address}"
        )
        for address in self.controller_mode_state_address:
            await self.hass.services.async_call(
                DOMAIN_KNX,
                SERVICE_KNX_SEND,
                {
                    KNX_ADDRESS: address,
                    SERVICE_KNX_ATTR_PAYLOAD: payload,
                    SERVICE_KNX_ATTR_RESPONSE: response,
                },
            )

    async def async_setup_events(self) -> None:
        await self._register_receiver(ClimateSchema.CONF_TEMPERATURE_ADDRESS)
        await self._register_receiver(ClimateSchema.CONF_TARGET_TEMPERATURE_ADDRESS)
        await self._register_receiver(ClimateSchema.CONF_OPERATION_MODE_ADDRESS)
        await self._register_receiver(ClimateSchema.CONF_CONTROLLER_MODE_ADDRESS)

        if not self.answer_reads:
            return

        # Register for potential reads
        await self._register_receiver(
            ClimateSchema.CONF_TARGET_TEMPERATURE_STATE_ADDRESS
        )
        await self._register_receiver(ClimateSchema.CONF_OPERATION_MODE_STATE_ADDRESS)
        await self._register_receiver(ClimateSchema.CONF_CONTROLLER_MODE_STATE_ADDRESS)
