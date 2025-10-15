import logging
from homeassistant.components.number import NumberEntity
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)
DOMAIN = "computherm_b"


async def async_setup_entry(hass, entry, async_add_entities):
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

            entities.append(ProSmartBoostDuration(hass, token, device_id, device_name))
            entities.append(ProSmartBoostTemperature(hass, token, device_id, device_name))
            entities.append(ProSmartManualTemperature(hass, token, device_id, device_name))

        async_add_entities(entities)
        _LOGGER.info("ProSmart numbers added: %s", [e._attr_name for e in entities])

    except Exception as e:
        _LOGGER.exception("Error setting up ProSmart numbers: %s", e)


class ProSmartNumberBase(NumberEntity):
    def __init__(self, hass, token, device_id, device_name):
        self.hass = hass
        self._token = token
        self._device_id = device_id
        self._device_name = device_name
        self._session = async_get_clientsession(hass)

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": self._device_name,
            "manufacturer": "ProSmart System",
            "model": "BBoil Classic",
        }

    async def _get_relay(self):
        """GET current relay state from device."""
        headers = {"Authorization": f"Bearer {self._token}"}
        try:
            async with self._session.get(
                f"https://api.prosmartsystem.com/api/devices/{self._device_id}",
                headers=headers,
                timeout=10
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
                # Use the first relay (index 0)
                return data["relays"][0]
        except Exception as e:
            _LOGGER.error("Error fetching relay data: %s", e)
            return None


class ProSmartBoostDuration(ProSmartNumberBase):
    def __init__(self, hass, token, device_id, device_name):
        super().__init__(hass, token, device_id, device_name)
        self._attr_name = f"{device_name} Boost Duration"
        self._attr_unique_id = f"{device_id}_boost_duration"
        self._attr_native_min_value = 0
        self._attr_native_max_value = 180
        self._attr_native_step = 1
        self._attr_native_unit_of_measurement = "min"

    @property
    def native_value(self):
        # Return last known value; will be refreshed by async_update
        return getattr(self, "_boost_minutes", 0)

    async def async_update(self):
        relay = await self._get_relay()
        if relay:
            self._boost_minutes = relay.get("boost_remaining", 0)


    async def async_set_native_value(self, value: float):
        self._boost_minutes = int(value)
        self.async_write_ha_state()

        headers = {"Authorization": f"Bearer {self._token}"}
        try:
            async with self._session.post(
                f"https://api.prosmartsystem.com/api/devices/{self._device_id}/cmd",
                headers=headers,
                json={"relay": 1, "boost_time": self._boost_minutes * 60},
                timeout=10
            ) as resp:
                resp.raise_for_status()
        except Exception as e:
            _LOGGER.error("Error sending boost command: %s", e)


class ProSmartBoostTemperature(ProSmartNumberBase):
    def __init__(self, hass, token, device_id, device_name):
        super().__init__(hass, token, device_id, device_name)
        self._attr_name = f"{device_name} Boost Temperature"
        self._attr_unique_id = f"{device_id}_boost_temperature"
        self._attr_native_min_value = 5
        self._attr_native_max_value = 35
        self._attr_native_step = 0.1
        self._attr_native_unit_of_measurement = "°C"
        self._temperature = 24.0

    @property
    def native_value(self):
        return getattr(self, "_temperature", 24.0)

    async def async_update(self):
        relay = await self._get_relay()
        if relay:
            self._temperature = relay.get("boost_set_point", 24.0)

    async def async_set_native_value(self, value: float):
        self._temperature = round(float(value), 1)
        self.async_write_ha_state()
        headers = {"Authorization": f"Bearer {self._token}"}
        try:
            async with self._session.post(
                f"https://api.prosmartsystem.com/api/devices/{self._device_id}/cmd",
                headers=headers,
                json={"relay": 1, "boost_set_point": self._temperature},
                timeout=10
            ) as resp:
                resp.raise_for_status()
        except Exception as e:
            _LOGGER.error("Error sending boost temperature command: %s", e)


class ProSmartManualTemperature(ProSmartNumberBase):
    def __init__(self, hass, token, device_id, device_name):
        super().__init__(hass, token, device_id, device_name)
        self._attr_name = f"{device_name} Manual Temperature"
        self._attr_unique_id = f"{device_id}_manual_temperature"
        self._attr_native_min_value = 5
        self._attr_native_max_value = 35
        self._attr_native_step = 0.1
        self._attr_native_unit_of_measurement = "°C"
        self._temperature = 22.0

    @property
    def native_value(self):
        return getattr(self, "_temperature", 22.0)

    async def async_update(self):
        relay = await self._get_relay()
        if relay:
            self._temperature = relay.get("manual_set_point", 22.0)

    async def async_set_native_value(self, value: float):
        self._temperature = round(float(value), 1)
        self.async_write_ha_state()
        headers = {"Authorization": f"Bearer {self._token}"}
        try:
            async with self._session.post(
                f"https://api.prosmartsystem.com/api/devices/{self._device_id}/cmd",
                headers=headers,
                json={"relay": 1, "manual_set_point": self._temperature},
                timeout=10
            ) as resp:
                resp.raise_for_status()
        except Exception as e:
            _LOGGER.error("Error sending manual temperature command: %s", e)
