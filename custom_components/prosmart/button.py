import logging
from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)
DOMAIN = "computherm_b"


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up ProSmart mode buttons from a config entry."""
    email = entry.data["email"]
    password = entry.data["password"]

    session = async_get_clientsession(hass)
    entities = []

    try:
        # --- LOGIN ---
        async with session.post(
            "https://api.prosmartsystem.com/api/auth/login",
            json={"email": email, "password": password},
            timeout=10
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()
            token = data.get("access_token")
            if not token:
                _LOGGER.error("No access token returned")
                return

        # --- GET DEVICES ---
        headers = {"Authorization": f"Bearer {token}"}
        async with session.get(
            "https://api.prosmartsystem.com/api/devices",
            headers=headers,
            timeout=10
        ) as dev_resp:
            dev_resp.raise_for_status()
            devices = await dev_resp.json()

        # --- Create buttons for each device ---
        for dev in devices:
            device_id = dev["id"]
            device_name = dev.get("name") or dev.get("serial_number")

            entities.append(ProSmartModeButton(hass, token, device_id, "MANUAL", device_name))
            entities.append(ProSmartModeButton(hass, token, device_id, "SCHEDULE", device_name))

        async_add_entities(entities)
        _LOGGER.info("ProSmart mode buttons added: %s", [e.name for e in entities])

    except Exception as e:
        _LOGGER.exception("Error setting up ProSmart mode buttons: %s", e)


class ProSmartModeButton(ButtonEntity):
    """Button to set heating mode (MANUAL / SCHEDULE)."""

    def __init__(self, hass, token, device_id, mode, name):
        self.hass = hass
        self._token = token
        self._device_id = device_id
        self._mode = mode
        self._attr_name = f"{name} {mode}"
        self._attr_unique_id = f"{device_id}_{mode}_button"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": f"ProSmart {self._device_id}",
            "manufacturer": "ProSmart System",
            "model": "BBoil Classic",
        }

    async def async_press(self):
        """Send the mode change POST request."""
        session = async_get_clientsession(self.hass)
        try:
            async with session.post(
                f"https://api.prosmartsystem.com/api/devices/{self._device_id}/cmd",
                headers={"Authorization": f"Bearer {self._token}"},
                json={"mode": self._mode},
                timeout=10
            ) as resp:
                resp.raise_for_status()
                _LOGGER.info("Mode set to %s", self._mode)
        except Exception as e:
            _LOGGER.error("Error setting mode %s: %s", self._mode, e)
