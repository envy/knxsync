from typing import TypedDict, Final
from collections.abc import Mapping

DOMAIN = "knxsync"

TELEGRAMTYPE_WRITE: Final = "GroupValueWrite"
TELEGRAMTYPE_READ: Final = "GroupValueRead"

CONF_KNXSYNC_SYNCED_ENTITIES: Final = "synced_entities"

CONF_KNXSYNC_BASE_ANSWER_READS: Final = "answer_reads"

CONF_KNXSYNC_LIGHT_ZERO_BRIGHTNESS_WHEN_OFF: Final = "zero_brightness_when_off"


class KNXSyncEntityBaseData(TypedDict, total=False):
    answer_reads: bool | None


class KNXSyncEntityLightData(KNXSyncEntityBaseData):
    address: list[str] | None
    state_address: list[str] | None
    brightness_address: list[str] | None
    brightness_state_address: list[str] | None
    zero_brightness_when_off: bool | None
    color_address: list[str] | None
    color_state_address: list[str] | None


class KNXSyncEntityClimateData(KNXSyncEntityBaseData):
    temperature_address: list[str] | None
    target_temperature_address: list[str] | None
    target_temperature_state_address: list[str] | None
    operation_mode_address: list[str] | None
    operation_mode_state_address: bool | None
    controller_mode_address: list[str] | None
    controller_mode_state_address: list[str] | None


class KNXSyncEntityBinarySensorData(KNXSyncEntityBaseData):
    state_address: list[str] | None


class KNXSyncEntryData(TypedDict, total=False):
    synced_entities: Mapping[
        str,
        KNXSyncEntityLightData
        | KNXSyncEntityClimateData
        | KNXSyncEntityBinarySensorData,
    ]
