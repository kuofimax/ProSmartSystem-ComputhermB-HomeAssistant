import logging
from homeassistant.components.number import NumberEntity
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)
DOMAIN = "computherm_b"

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up ProSmart Boost numbers from a config entry."""
    email = entry.data["email"]
    password = entry.data["password"]

    session = async_get_clientsession(hass)
    entities = []

    try:
        # LOGIN
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

        headers = {"Authorization": f"Bearer {token}"}

        # GET DEVICES
        async with session.get(
            "https://api.prosmartsystem.com/api/devices",
            headers=headers,
            timeout=10
        ) as dev_resp:
            dev_resp.raise_for_status()
            devices = await dev_resp.json()

        for dev in devices:
            device_id = dev["id"]
            device_name = dev.get("name") or dev.get("serial_number")
            entities.append(ProSmartBoostNumber(hass, token, device_id, device_name))

        async_add_entities(entities)
        _LOGGER.info("ProSmart boost numbers added: %s", [e._attr_name for e in entities])

    except Exception as e:
        _LOGGER.exception("Error setting up ProSmart boost numbers: %s", e)


class ProSmartBoostNumber(NumberEntity):
    """Boost control as a NumberEntity (minutes)."""

    def __init__(self, hass, token, device_id, device_name, boost_minutes=30):
        self.hass = hass
        self._token = token
        self._device_id = device_id
        self._device_name = device_name
        self._boost_minutes = boost_minutes

        self._attr_name = f"{device_name} Boost"
        self._attr_unique_id = f"{device_id}_boost"
        self._attr_native_min_value = 0
        self._attr_native_max_value = 180
        self._attr_native_step = 1
        self._attr_native_unit_of_measurement = "min"

    @property
    def device_info(self):
        """Assign the Boost number to the same device as the Temperature sensor."""
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": self._device_name,
            "manufacturer": "ProSmart System",
            "model": "BBoil Classic",
        }

    async def async_set_native_value(self, value: float):
        """Send boost POST command to ProSmart API."""
        self._boost_minutes = int(value)
        boost_time = self._boost_minutes * 60  # seconds

        session = async_get_clientsession(self.hass)
        headers = {"Authorization": f"Bearer {self._token}"}

        try:
            async with session.post(
                f"https://api.prosmartsystem.com/api/devices/{self._device_id}/cmd",
                headers=headers,
                json={"relay": 1, "boost_time": boost_time},
                timeout=10
            ) as resp:
                resp.raise_for_status()
                _LOGGER.info(
                    "Boost command sent: device=%s relay=1 for %s minutes",
                    self._device_id, self._boost_minutes
                )
        except Exception as e:
            _LOGGER.error("Error sending boost command: %s", e)
