import logging
from homeassistant.components.number import NumberEntity
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)
DOMAIN = "computherm_b"


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up ProSmart Boost, Boost Temperature, and Manual Setpoint numbers from a config entry."""
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

        headers = {"Authorization": f"Bearer {token}"}

        # --- GET DEVICES ---
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

            relays = dev.get("relays", [])
            relay_data = relays[0] if relays else {}

            # --- Boost duration from server ---
            boost_remaining = relay_data.get("boost_remaining", 0)  # in minutes
            boost_setpoint = relay_data.get("boost_set_point", 24)
            manual_setpoint = relay_data.get("manual_set_point", 22)

            # Entities
            entities.append(ProSmartBoostNumber(hass, token, device_id, device_name, boost_remaining))
            entities.append(ProSmartBoostTemperatureNumber(hass, token, device_id, device_name, boost_setpoint))
            entities.append(ProSmartManualSetpointNumber(hass, token, device_id, device_name, manual_setpoint))

        async_add_entities(entities)
        _LOGGER.info("ProSmart numbers added: %s", [e._attr_name for e in entities])

    except Exception as e:
        _LOGGER.exception("Error setting up ProSmart numbers: %s", e)


class ProSmartBoostNumber(NumberEntity):
    """Boost duration control as a NumberEntity (minutes)."""

    def __init__(self, hass, token, device_id, device_name, boost_minutes=30):
        self.hass = hass
        self._token = token
        self._device_id = device_id
        self._device_name = device_name
        self._boost_minutes = boost_minutes

        self._attr_name = f"{device_name} Boost Duration"
        self._attr_unique_id = f"{device_id}_boost_duration"
        self._attr_native_min_value = 0
        self._attr_native_max_value = 180
        self._attr_native_step = 1
        self._attr_native_unit_of_measurement = "min"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": self._device_name,
            "manufacturer": "ProSmart System",
            "model": "BBoil Classic",
        }

    @property
    def native_value(self):
        return self._boost_minutes

    async def async_set_native_value(self, value: float):
        """Boost duration is read-only from server; no POST needed."""
        self._boost_minutes = int(value)
        self.async_write_ha_state()


class ProSmartBoostTemperatureNumber(NumberEntity):
    """Boost temperature control as a NumberEntity (°C)."""

    def __init__(self, hass, token, device_id, device_name, temperature=24.0):
        self.hass = hass
        self._token = token
        self._device_id = device_id
        self._device_name = device_name
        self._temperature = temperature

        self._attr_name = f"{device_name} Boost Temperature"
        self._attr_unique_id = f"{device_id}_boost_temperature"
        self._attr_native_min_value = 5
        self._attr_native_max_value = 35
        self._attr_native_step = 0.1
        self._attr_native_unit_of_measurement = "°C"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": self._device_name,
            "manufacturer": "ProSmart System",
            "model": "BBoil Classic",
        }

    @property
    def native_value(self):
        return self._temperature

    async def async_set_native_value(self, value: float):
        """Send boost temperature POST command and update state."""
        self._temperature = round(float(value), 1)
        self.async_write_ha_state()

        session = async_get_clientsession(self.hass)
        headers = {"Authorization": f"Bearer {self._token}"}

        try:
            async with session.post(
                f"https://api.prosmartsystem.com/api/devices/{self._device_id}/cmd",
                headers=headers,
                json={"relay": 1, "boost_set_point": self._temperature},
                timeout=10
            ) as resp:
                resp.raise_for_status()
                _LOGGER.info(
                    "Boost temperature sent: device=%s temperature=%.1f°C",
                    self._device_id, self._temperature
                )
        except Exception as e:
            _LOGGER.error("Error sending boost temperature command: %s", e)


class ProSmartManualSetpointNumber(NumberEntity):
    """Manual temperature control as a NumberEntity (°C)."""

    def __init__(self, hass, token, device_id, device_name, temperature=22.0):
        self.hass = hass
        self._token = token
        self._device_id = device_id
        self._device_name = device_name
        self._temperature = temperature

        self._attr_name = f"{device_name} Manual Temperature"
        self._attr_unique_id = f"{device_id}_manual_temperature"
        self._attr_native_min_value = 5
        self._attr_native_max_value = 35
        self._attr_native_step = 0.1
        self._attr_native_unit_of_measurement = "°C"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": self._device_name,
            "manufacturer": "ProSmart System",
            "model": "BBoil Classic",
        }

    @property
    def native_value(self):
        return self._temperature

    async def async_set_native_value(self, value: float):
        """Send manual temperature POST command and update state."""
        self._temperature = round(float(value), 1)
        self.async_write_ha_state()

        session = async_get_clientsession(self.hass)
        headers = {"Authorization": f"Bearer {self._token}"}

        try:
            async with session.post(
                f"https://api.prosmartsystem.com/api/devices/{self._device_id}/cmd",
                headers=headers,
                json={"relay": 1, "manual_set_point": self._temperature},
                timeout=10
            ) as resp:
                resp.raise_for_status()
                _LOGGER.info(
                    "Manual setpoint sent: device=%s temperature=%.1f°C",
                    self._device_id, self._temperature
                )
        except Exception as e:
            _LOGGER.error("Error sending manual setpoint command: %s", e)
