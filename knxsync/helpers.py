import logging
from typing import Optional

from .const import DOMAIN

from homeassistant.components.knx import (
    DOMAIN as DOMAIN_KNX,
    SERVICE_KNX_EVENT_REGISTER,
)
from homeassistant.components.knx.const import KNX_ADDRESS

from .base import SyncedEntity

_LOGGER = logging.getLogger(DOMAIN)


def get_domain(eid: str) -> str:
    return eid.split(".")[0]


def get_id(eid: str) -> str:
    return eid.split(".")[1]


def parse_group_addresses(s: str) -> Optional[list[str]]:
    return list(filter(None, list(map(lambda x: x.strip(), s.split(","))))) or None


def set_value_from_config(entity: SyncedEntity, config: dict, config_key: str) -> None:
    if config_key in config.keys():
        setattr(entity, config_key, parse_group_addresses(config[config_key]))
        _LOGGER.debug(f"{entity.synced_entity_id} <- {getattr(entity, config_key)}")


async def register_receiver(entity: SyncedEntity, attr: str) -> None:
    v = getattr(entity, attr)
    if v is not None:
        for address in v:
            _LOGGER.debug(
                f"registering receiver {address} -> {entity.synced_entity_id}"
            )
            await entity.hass.services.async_call(
                DOMAIN_KNX, SERVICE_KNX_EVENT_REGISTER, {KNX_ADDRESS: address}
            )
