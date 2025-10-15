import logging
from datetime import timedelta

from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed, CoordinatorEntity
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfTemperature

_LOGGER = logging.getLogger(__name__)
DOMAIN = "computherm_b"
UPDATE_INTERVAL = timedelta(seconds=30)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up ProSmart sensors from a config entry."""
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

            coordinator = ProSmartCoordinator(hass, session, headers, device_id, device_name)
            await coordinator.async_config_entry_first_refresh()

            # --- Temperature & Setpoints ---
            entities.append(ProSmartTemperatureSensor(coordinator))
            entities.append(ProSmartManualSetPointSensor(coordinator))
            entities.append(ProSmartScheduleSetPointSensor(coordinator))
            entities.append(ProSmartBoostSetPointSensor(coordinator))

            # --- Function / Relay / Boost ---
            entities.append(ProSmartFunctionSensor(coordinator))
            entities.append(ProSmartRelayStateSensor(coordinator))
            entities.append(ProSmartRelayModeSensor(coordinator))
            entities.append(ProSmartBoostActiveSensor(coordinator))
            entities.append(ProSmartBoostRemainingSensor(coordinator))

            # --- Hysteresis ---
            entities.append(ProSmartHysteresisHighSensor(coordinator))
            entities.append(ProSmartHysteresisLowSensor(coordinator))

        async_add_entities(entities)
        _LOGGER.info("ProSmart sensors added: %s", [e._attr_name for e in entities])

    except Exception as e:
        _LOGGER.exception("Error setting up ProSmart sensors: %s", e)


class ProSmartCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch temperature, setpoints, and relay info periodically."""

    def __init__(self, hass, session, headers, device_id, device_name):
        self.session = session
        self.headers = headers
        self.device_id = device_id
        self.device_name = device_name
        self.data = {}
        super().__init__(
            hass,
            _LOGGER,
            name=f"ProSmart {device_name} coordinator",
            update_interval=UPDATE_INTERVAL,
        )

    async def _async_update_data(self):
        """Fetch data from ProSmart API."""
        try:
            async with self.session.get(
                f"https://api.prosmartsystem.com/api/devices/{self.device_id}/cmd/scan",
                headers=self.headers,
                timeout=10
            ) as resp:
                resp.raise_for_status()
                result = await resp.json()

                # --- Temperature ---
                readings = result.get("readings", [])
                temperature = next((r.get("reading") for r in readings if r.get("type") == "TEMPERATURE"), None)

                # --- Relay info ---
                relays = result.get("relays", [])
                relay = relays[0] if relays else {}

                # --- Collect all data ---
                self.data = {
                    "temperature": temperature,
                    "manual_set_point": relay.get("manual_set_point"),
                    "schedule_set_point": relay.get("schedule_set_point"),
                    "boost_set_point": relay.get("boost_set_point"),
                    "boost_active": relay.get("boost_active"),
                    "boost_remaining": (
                        round(relay["boost_remaining"] / 60) if relay.get("boost_remaining") is not None else None
                    ),
                    "relay_state": relay.get("relay_state"),
                    "relay_mode": relay.get("mode"),
                    "function": relay.get("function"),
                    "hysteresis_high": relay.get("hysteresis_high"),
                    "hysteresis_low": relay.get("hysteresis_low"),
                }

                return self.data

        except Exception as e:
            raise UpdateFailed(f"Error fetching device data: {e}") from e


# ---------- TEMPERATURE & SETPOINT SENSORS ----------

class ProSmartTemperatureSensor(CoordinatorEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:thermometer"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = f"{coordinator.device_name} Temperature"
        self._attr_unique_id = f"{coordinator.device_id}_temperature"

    @property
    def native_value(self):
        return self.coordinator.data.get("temperature")

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.coordinator.device_id)},
            "name": self.coordinator.device_name,
            "manufacturer": "Computherm / ProSmart",
            "model": "Wi-Fi Thermostat",
        }


class ProSmartManualSetPointSensor(CoordinatorEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:thermometer-check"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = f"{coordinator.device_name} Manual Set Point"
        self._attr_unique_id = f"{coordinator.device_id}_manual_set_point"

    @property
    def native_value(self):
        return self.coordinator.data.get("manual_set_point")

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.coordinator.device_id)},
            "name": self.coordinator.device_name,
            "manufacturer": "Computherm / ProSmart",
            "model": "Wi-Fi Thermostat",
        }


class ProSmartScheduleSetPointSensor(CoordinatorEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = f"{coordinator.device_name} Schedule Set Point"
        self._attr_unique_id = f"{coordinator.device_id}_schedule_set_point"

    @property
    def native_value(self):
        return self.coordinator.data.get("schedule_set_point")

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.coordinator.device_id)},
            "name": self.coordinator.device_name,
            "manufacturer": "Computherm / ProSmart",
            "model": "Wi-Fi Thermostat",
        }


class ProSmartBoostSetPointSensor(CoordinatorEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:rocket-launch"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = f"{coordinator.device_name} Boost Set Point"
        self._attr_unique_id = f"{coordinator.device_id}_boost_set_point"

    @property
    def native_value(self):
        return self.coordinator.data.get("boost_set_point")

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.coordinator.device_id)},
            "name": self.coordinator.device_name,
            "manufacturer": "Computherm / ProSmart",
            "model": "Wi-Fi Thermostat",
        }


# ---------- FUNCTION / STATE SENSORS ----------

class ProSmartFunctionSensor(CoordinatorEntity, SensorEntity):
    _attr_icon = "mdi:cog"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = f"{coordinator.device_name} Function"
        self._attr_unique_id = f"{coordinator.device_id}_function"

    @property
    def native_value(self):
        return self.coordinator.data.get("function")

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.coordinator.device_id)},
            "name": self.coordinator.device_name,
            "manufacturer": "Computherm / ProSmart",
            "model": "Wi-Fi Thermostat",
        }


class ProSmartRelayStateSensor(CoordinatorEntity, SensorEntity):
    _attr_icon = "mdi:power"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = f"{coordinator.device_name} Relay State"
        self._attr_unique_id = f"{coordinator.device_id}_relay_state"

    @property
    def native_value(self):
        return self.coordinator.data.get("relay_state")

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.coordinator.device_id)},
            "name": self.coordinator.device_name,
            "manufacturer": "Computherm / ProSmart",
            "model": "Wi-Fi Thermostat",
        }


class ProSmartRelayModeSensor(CoordinatorEntity, SensorEntity):
    """Shows the current relay mode (SCHEDULE, MANUAL, BOOST, etc.)."""
    _attr_icon = "mdi:swap-horizontal"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = f"{coordinator.device_name} Relay Mode"
        self._attr_unique_id = f"{coordinator.device_id}_relay_mode"

    @property
    def native_value(self):
        return self.coordinator.data.get("relay_mode")

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.coordinator.device_id)},
            "name": self.coordinator.device_name,
            "manufacturer": "Computherm / ProSmart",
            "model": "Wi-Fi Thermostat",
        }


class ProSmartBoostActiveSensor(CoordinatorEntity, SensorEntity):
    _attr_icon = "mdi:rocket"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = f"{coordinator.device_name} Boost Active"
        self._attr_unique_id = f"{coordinator.device_id}_boost_active"

    @property
    def native_value(self):
        value = self.coordinator.data.get("boost_active")
        return "ON" if value else "OFF"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.coordinator.device_id)},
            "name": self.coordinator.device_name,
            "manufacturer": "Computherm / ProSmart",
            "model": "Wi-Fi Thermostat",
        }


class ProSmartBoostRemainingSensor(CoordinatorEntity, SensorEntity):
    _attr_icon = "mdi:timer-outline"
    _attr_native_unit_of_measurement = "min"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = f"{coordinator.device_name} Boost Remaining"
        self._attr_unique_id = f"{coordinator.device_id}_boost_remaining"

    @property
    def native_value(self):
        return self.coordinator.data.get("boost_remaining")

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.coordinator.device_id)},
            "name": self.coordinator.device_name,
            "manufacturer": "Computherm / ProSmart",
            "model": "Wi-Fi Thermostat",
        }


# ---------- HYSTERESIS ----------

class ProSmartHysteresisHighSensor(CoordinatorEntity, SensorEntity):
    _attr_name = "Hysteresis High"
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:arrow-up"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device_id}_hysteresis_high"

    @property
    def native_value(self):
        return self.coordinator.data.get("hysteresis_high")

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.coordinator.device_id)},
            "name": self.coordinator.device_name,
            "manufacturer": "Computherm / ProSmart",
            "model": "Wi-Fi Thermostat",
        }


class ProSmartHysteresisLowSensor(CoordinatorEntity, SensorEntity):
    _attr_name = "Hysteresis Low"
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:arrow-down"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device_id}_hysteresis_low"

    @property
    def native_value(self):
        return self.coordinator.data.get("hysteresis_low")

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.coordinator.device_id)},
            "name": self.coordinator.device_name,
            "manufacturer": "Computherm / ProSmart",
            "model": "Wi-Fi Thermostat",
        }
