"""Tests for the Bond button device."""

from unittest.mock import patch

from bond_async import Action, DeviceType
import pytest

from homeassistant.components.bond.button import STEP_SIZE
from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .common import (
    patch_bond_action,
    patch_bond_device_commands,
    patch_bond_device_state,
    patch_bond_transmit_command,
    setup_platform,
)


def ceiling_fan(name: str):
    """Create a ceiling fan with given name."""
    return {
        "name": name,
        "type": DeviceType.CEILING_FAN,
        "actions": [Action.SET_SPEED, Action.SET_DIRECTION, Action.STOP],
    }


def light_brightness_increase_decrease_only(name: str):
    """Create a light that can only increase or decrease brightness."""
    return {
        "name": name,
        "type": DeviceType.LIGHT,
        "actions": [
            Action.TURN_LIGHT_ON,
            Action.TURN_LIGHT_OFF,
            Action.START_DIMMER,
            Action.START_INCREASING_BRIGHTNESS,
            Action.START_DECREASING_BRIGHTNESS,
            Action.STOP,
        ],
    }


def fireplace_increase_decrease_only(name: str):
    """Create a fireplace that can only increase or decrease flame."""
    return {
        "name": name,
        "type": DeviceType.LIGHT,
        "actions": [
            Action.INCREASE_FLAME,
            Action.DECREASE_FLAME,
        ],
    }


def light(name: str):
    """Create a light with a given name."""
    return {
        "name": name,
        "type": DeviceType.LIGHT,
        "actions": [Action.TURN_LIGHT_ON, Action.TURN_LIGHT_OFF, Action.SET_BRIGHTNESS],
    }


def motorized_shade(name: str):
    """Create a motorized shade with a given name."""
    return {
        "name": name,
        "type": DeviceType.MOTORIZED_SHADES,
        "actions": [Action.OPEN, Action.OPEN_NEXT, Action.CLOSE, Action.CLOSE_NEXT],
    }


def motorized_shade_with_preset(name: str):
    """Create a motorized shade with preset action."""
    return {
        "name": name,
        "type": DeviceType.MOTORIZED_SHADES,
        "actions": [Action.OPEN, Action.CLOSE, Action.HOLD, Action.PRESET, Action.STOP],
    }


async def test_entity_registry(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
) -> None:
    """Tests that the devices are registered in the entity registry."""
    await setup_platform(
        hass,
        BUTTON_DOMAIN,
        light_brightness_increase_decrease_only("name-1"),
        bond_version={"bondid": "test-hub-id"},
        bond_device_id="test-device-id",
    )

    entity = entity_registry.entities["button.name_1_stop_actions"]
    assert entity.unique_id == "test-hub-id_test-device-id_stop"
    entity = entity_registry.entities["button.name_1_start_increasing_brightness"]
    assert entity.unique_id == "test-hub-id_test-device-id_startincreasingbrightness"
    entity = entity_registry.entities["button.name_1_start_decreasing_brightness"]
    assert entity.unique_id == "test-hub-id_test-device-id_startdecreasingbrightness"
    entity = entity_registry.entities["button.name_1_start_dimmer"]
    assert entity.unique_id == "test-hub-id_test-device-id_startdimmer"


async def test_mutually_exclusive_actions(hass: HomeAssistant) -> None:
    """Tests we do not create the button when there is a mutually exclusive action."""
    await setup_platform(
        hass,
        BUTTON_DOMAIN,
        light("name-1"),
        bond_device_id="test-device-id",
    )

    assert not hass.states.async_all("button")


async def test_stop_not_created_no_other_buttons(hass: HomeAssistant) -> None:
    """Tests we do not create the stop button when there are no other buttons."""
    await setup_platform(
        hass,
        BUTTON_DOMAIN,
        ceiling_fan("name-1"),
        bond_device_id="test-device-id",
    )

    assert not hass.states.async_all("button")


async def test_press_button_with_argument(hass: HomeAssistant) -> None:
    """Tests we can press a button with an argument."""
    await setup_platform(
        hass,
        BUTTON_DOMAIN,
        fireplace_increase_decrease_only("name-1"),
        bond_device_id="test-device-id",
    )

    assert hass.states.get("button.name_1_increase_flame")
    assert hass.states.get("button.name_1_decrease_flame")

    with patch_bond_action() as mock_action, patch_bond_device_state():
        await hass.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: "button.name_1_increase_flame"},
            blocking=True,
        )
        await hass.async_block_till_done()

    mock_action.assert_called_once_with(
        "test-device-id", Action(Action.INCREASE_FLAME, STEP_SIZE)
    )

    with patch_bond_action() as mock_action, patch_bond_device_state():
        await hass.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: "button.name_1_decrease_flame"},
            blocking=True,
        )
        await hass.async_block_till_done()

    mock_action.assert_called_once_with(
        "test-device-id", Action(Action.DECREASE_FLAME, STEP_SIZE)
    )


async def test_press_button(hass: HomeAssistant) -> None:
    """Tests we can press a button."""
    await setup_platform(
        hass,
        BUTTON_DOMAIN,
        light_brightness_increase_decrease_only("name-1"),
        bond_device_id="test-device-id",
    )

    assert hass.states.get("button.name_1_start_increasing_brightness")
    assert hass.states.get("button.name_1_start_decreasing_brightness")

    with patch_bond_action() as mock_action, patch_bond_device_state():
        await hass.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: "button.name_1_start_increasing_brightness"},
            blocking=True,
        )
        await hass.async_block_till_done()

    mock_action.assert_called_once_with(
        "test-device-id", Action(Action.START_INCREASING_BRIGHTNESS)
    )

    with patch_bond_action() as mock_action, patch_bond_device_state():
        await hass.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: "button.name_1_start_decreasing_brightness"},
            blocking=True,
        )
        await hass.async_block_till_done()

    mock_action.assert_called_once_with(
        "test-device-id", Action(Action.START_DECREASING_BRIGHTNESS)
    )


async def test_motorized_shade_actions(hass: HomeAssistant) -> None:
    """Tests motorized shade open next and close next actions."""
    await setup_platform(
        hass,
        BUTTON_DOMAIN,
        motorized_shade("name-1"),
        bond_device_id="test-device-id",
    )

    assert hass.states.get("button.name_1_open_next")
    assert hass.states.get("button.name_1_close_next")

    with patch_bond_action() as mock_action, patch_bond_device_state():
        await hass.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: "button.name_1_open_next"},
            blocking=True,
        )
        await hass.async_block_till_done()

    mock_action.assert_called_once_with("test-device-id", Action(Action.OPEN_NEXT))

    with patch_bond_action() as mock_action, patch_bond_device_state():
        await hass.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: "button.name_1_close_next"},
            blocking=True,
        )
        await hass.async_block_till_done()

    mock_action.assert_called_once_with("test-device-id", Action(Action.CLOSE_NEXT))


async def test_preset_button(hass: HomeAssistant) -> None:
    """Tests preset button is created and can be pressed."""
    await setup_platform(
        hass,
        BUTTON_DOMAIN,
        motorized_shade_with_preset("name-1"),
        bond_device_id="test-device-id",
    )

    assert hass.states.get("button.name_1_preset")

    with patch_bond_action() as mock_action, patch_bond_device_state():
        await hass.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: "button.name_1_preset"},
            blocking=True,
        )
        await hass.async_block_till_done()

    mock_action.assert_called_once_with("test-device-id", Action(Action.PRESET))


async def test_preset_does_not_trigger_stop_button(hass: HomeAssistant) -> None:
    """Tests that Preset alone does not cause a Stop Actions button to appear.

    Preset is added independently of the main button list, so it should
    not trigger the Stop button logic (which only activates when there
    are other button entities).
    """
    await setup_platform(
        hass,
        BUTTON_DOMAIN,
        motorized_shade_with_preset("name-1"),
        bond_device_id="test-device-id",
    )

    assert hass.states.get("button.name_1_preset")
    assert not hass.states.get("button.name_1_stop_actions")


def bridge_tower_fan(name: str):
    """Create a bridge fan whose remote only has toggle-style buttons."""
    return {
        "name": name,
        "type": DeviceType.CEILING_FAN,
        "actions": [
            Action.TURN_ON,
            Action.TURN_OFF,
            Action.TOGGLE_POWER,
            Action.SET_SPEED,
            Action.INCREASE_SPEED,
            Action.SET_DIRECTION,
            Action.TOGGLE_DIRECTION,
            Action.STOP,
        ],
        "commands": {"_": "some-hash"},
    }


TOWER_FAN_COMMANDS = {
    "cmd-toggle": {"name": "Toggle", "action": Action.TOGGLE_POWER},
    "cmd-speed-up": {
        "name": "Increase Speed",
        "action": Action.INCREASE_SPEED,
        "argument": 1,
    },
    "cmd-oscillate": {"name": "Oscillate", "action": "Oscillate"},
    "cmd-hidden": {"name": "Hidden", "action": Action.TURN_OFF, "hidden": True},
}


async def test_command_buttons_created(
    hass: HomeAssistant, entity_registry: er.EntityRegistry
) -> None:
    """Tests visible Bond app commands become buttons."""
    with patch_bond_device_commands(TOWER_FAN_COMMANDS):
        await setup_platform(
            hass,
            BUTTON_DOMAIN,
            bridge_tower_fan("Tower fan"),
            bond_version={"bondid": "test-hub-id"},
            bond_device_id="test-device-id",
        )

    assert {
        entity.entity_id: entity.unique_id
        for entity in entity_registry.entities.values()
    } == {
        "button.tower_fan_toggle": "test-hub-id_test-device-id_command_cmd-toggle",
        "button.tower_fan_increase_speed": (
            "test-hub-id_test-device-id_command_cmd-speed-up"
        ),
        "button.tower_fan_oscillate": "test-hub-id_test-device-id_command_cmd-oscillate",
    }


async def test_command_button_skips_existing_button(hass: HomeAssistant) -> None:
    """Tests a command already exposed as an action button is not duplicated."""
    with patch_bond_device_commands(
        {"cmd-dimmer": {"name": "Dim", "action": Action.START_DIMMER}}
    ):
        await setup_platform(
            hass,
            BUTTON_DOMAIN,
            {**light_brightness_increase_decrease_only("name-1"), "commands": {}},
            bond_device_id="test-device-id",
        )

    assert hass.states.get("button.name_1_start_dimmer")
    assert not hass.states.get("button.name_1_dim")


@pytest.mark.parametrize(
    ("entity_id", "expected_action"),
    [
        pytest.param(
            "button.tower_fan_toggle", Action(Action.TOGGLE_POWER), id="no_argument"
        ),
        pytest.param(
            "button.tower_fan_increase_speed",
            Action(Action.INCREASE_SPEED, 1),
            id="with_argument",
        ),
    ],
)
async def test_press_command_button_runs_action(
    hass: HomeAssistant, entity_id: str, expected_action: Action
) -> None:
    """Tests pressing a command with a supported action runs that action."""
    with patch_bond_device_commands(TOWER_FAN_COMMANDS):
        await setup_platform(
            hass,
            BUTTON_DOMAIN,
            bridge_tower_fan("Tower fan"),
            bond_device_id="test-device-id",
        )

    with (
        patch_bond_action() as mock_action,
        patch_bond_transmit_command() as mock_transmit,
        patch_bond_device_state(),
    ):
        await hass.services.async_call(
            BUTTON_DOMAIN, SERVICE_PRESS, {ATTR_ENTITY_ID: entity_id}, blocking=True
        )

    mock_action.assert_called_once_with("test-device-id", expected_action)
    mock_transmit.assert_not_called()


async def test_press_command_button_transmits_signal(hass: HomeAssistant) -> None:
    """Tests pressing a command without a supported action transmits its signal."""
    with patch_bond_device_commands(TOWER_FAN_COMMANDS):
        await setup_platform(
            hass,
            BUTTON_DOMAIN,
            bridge_tower_fan("Tower fan"),
            bond_device_id="test-device-id",
        )

    with (
        patch_bond_action() as mock_action,
        patch_bond_transmit_command() as mock_transmit,
        patch_bond_device_state(),
    ):
        await hass.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: "button.tower_fan_oscillate"},
            blocking=True,
        )

    mock_transmit.assert_called_once_with("test-device-id", "cmd-oscillate")
    mock_action.assert_not_called()


async def test_command_fetch_failure(hass: HomeAssistant) -> None:
    """Tests action buttons are still created when commands can't be fetched."""
    with patch_bond_device_commands({}, side_effect=TimeoutError()):
        await setup_platform(
            hass,
            BUTTON_DOMAIN,
            {**light_brightness_increase_decrease_only("name-1"), "commands": {}},
            bond_device_id="test-device-id",
        )

    assert hass.states.get("button.name_1_start_dimmer")


async def test_no_commands_endpoint(hass: HomeAssistant) -> None:
    """Tests devices without commands (Smart by Bond) don't query them."""
    with patch(
        "homeassistant.components.bond.Bond.device_commands"
    ) as mock_device_commands:
        await setup_platform(
            hass,
            BUTTON_DOMAIN,
            light_brightness_increase_decrease_only("name-1"),
            bond_device_id="test-device-id",
        )

    mock_device_commands.assert_not_called()
