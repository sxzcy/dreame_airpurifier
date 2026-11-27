"""Button platform for Dreame FP10 Air Purifier maintenance actions."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import const as C
from .coordinator import DreameConfigEntry, DreameCoordinator
from .entity import DreameEntity


@dataclass(frozen=True, kw_only=True)
class DreameButtonDescription(ButtonEntityDescription):
    """Describe a Dreame FP10 MIOT action button."""

    siid: int
    aiid: int


BUTTON_DESCRIPTIONS: tuple[DreameButtonDescription, ...] = (
    DreameButtonDescription(
        key="start_self_cleaning",
        translation_key="start_self_cleaning",
        icon="mdi:broom",
        siid=C.FP10_SELF_CLEAN_SIID,
        aiid=C.FP10_SELF_CLEAN_START_AIID,
    ),
    DreameButtonDescription(
        key="confirm_self_cleaning",
        translation_key="confirm_self_cleaning",
        icon="mdi:check-circle-outline",
        siid=C.FP10_SELF_CLEAN_SIID,
        aiid=C.FP10_SELF_CLEAN_CONFIRM_AIID,
    ),
    DreameButtonDescription(
        key="reset_hepa_filter",
        translation_key="reset_hepa_filter",
        icon="mdi:air-filter",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        siid=C.FP10_FILTER_RESET_SIID,
        aiid=C.FP10_HEPA_RESET_AIID,
    ),
    DreameButtonDescription(
        key="reset_combbox",
        translation_key="reset_combbox",
        icon="mdi:tray-remove",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        siid=C.FP10_FILTER_RESET_SIID,
        aiid=C.FP10_COMBBOX_RESET_AIID,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DreameConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Dreame FP10 action buttons."""
    coordinator = entry.runtime_data
    async_add_entities(DreameActionButton(coordinator, desc) for desc in BUTTON_DESCRIPTIONS)


class DreameActionButton(DreameEntity, ButtonEntity):
    """Button triggering a Dreame FP10 MIOT action."""

    entity_description: DreameButtonDescription

    def __init__(self, coordinator: DreameCoordinator, description: DreameButtonDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.descriptor.did}_button_{description.key}"

    async def async_press(self) -> None:
        await self.coordinator.async_send_action(
            self.entity_description.siid,
            self.entity_description.aiid,
        )
