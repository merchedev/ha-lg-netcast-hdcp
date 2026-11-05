"""Button entities for LG NetCast HDCP televisions."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import LgNetcastHdcpConfigEntry
from .const import DOMAIN, MANUFACTURER, MODEL
from .hdcp import HdcpAuthError, HdcpError


@dataclass(frozen=True, kw_only=True)
class LgNetcastButtonDescription(ButtonEntityDescription):
    """Describe a remote-key button."""

    command: str


BUTTONS: tuple[LgNetcastButtonDescription, ...] = (
    LgNetcastButtonDescription(
        key="home", name="Home", command="HOME", icon="mdi:home"
    ),
    LgNetcastButtonDescription(
        key="ok", name="OK", command="OK", icon="mdi:check-circle-outline"
    ),
    LgNetcastButtonDescription(
        key="input", name="Input", command="INPUT", icon="mdi:import"
    ),
    LgNetcastButtonDescription(
        key="left", name="Left", command="LEFT", icon="mdi:arrow-left"
    ),
    LgNetcastButtonDescription(
        key="right", name="Right", command="RIGHT", icon="mdi:arrow-right"
    ),
    LgNetcastButtonDescription(
        key="channel_up",
        name="Channel up",
        command="CHANNEL_UP",
        icon="mdi:plus",
    ),
    LgNetcastButtonDescription(
        key="channel_down",
        name="Channel down",
        command="CHANNEL_DOWN",
        icon="mdi:minus",
    ),
    LgNetcastButtonDescription(
        key="q_menu", name="Q.Menu", command="Q_MENU", icon="mdi:menu"
    ),
    LgNetcastButtonDescription(
        key="timer", name="Timer", command="TIMER", icon="mdi:timer-outline"
    ),
    LgNetcastButtonDescription(
        key="tv_radio", name="TV/Radio", command="TV_RADIO", icon="mdi:radio"
    ),
    LgNetcastButtonDescription(
        key="exit", name="Exit", command="EXIT", icon="mdi:exit-to-app"
    ),
    *(
        LgNetcastButtonDescription(
            key=f"number_{digit}",
            name=str(digit),
            command=f"NUMBER_{digit}",
            icon=f"mdi:numeric-{digit}",
        )
        for digit in range(10)
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LgNetcastHdcpConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the remote key buttons."""
    async_add_entities(
        LgNetcastHdcpButton(entry, description) for description in BUTTONS
    )


class LgNetcastHdcpButton(ButtonEntity):
    """A single remote key."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    entity_description: LgNetcastButtonDescription

    def __init__(
        self,
        entry: LgNetcastHdcpConfigEntry,
        description: LgNetcastButtonDescription,
    ) -> None:
        """Initialize the button."""
        self._entry = entry
        self._client = entry.runtime_data.client
        self.entity_description = description
        self._attr_unique_id = f"{entry.unique_id or entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id or entry.entry_id)},
            manufacturer=MANUFACTURER,
            model=MODEL,
            name=entry.title,
        )

    async def async_press(self) -> None:
        """Send the key to the TV."""
        try:
            await self._client.async_send_key(self.entity_description.command)
        except HdcpAuthError as err:
            self._entry.async_start_reauth(self.hass)
            raise HomeAssistantError(
                "The TV rejected the pairing key; reauthentication is required"
            ) from err
        except HdcpError as err:
            raise HomeAssistantError(f"Could not send the command: {err}") from err
