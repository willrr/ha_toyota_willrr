"""Sensor platform for Toyota integration."""

# pylint: disable=W0212, W0511

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any, Literal, Optional, Union

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfLength
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from pytoyoda.models.vehicle import Vehicle

from . import StatisticsData, VehicleData
from .const import DOMAIN
from .entity import ToyotaBaseEntity
from .utils import (
    format_statistics_attributes,
    format_vin_sensor_attributes,
    round_number,
)

_LOGGER = logging.getLogger(__name__)


class ToyotaSensorEntityDescription(SensorEntityDescription, frozen_or_thawed=True):
    """Describes a Toyota sensor entity."""

    value_fn: Callable[[Vehicle], StateType]
    attributes_fn: Callable[[Vehicle], Optional[dict[str, Any]]]


VIN_ENTITY_DESCRIPTION = ToyotaSensorEntityDescription(
    key="vin",
    translation_key="vin",
    icon="mdi:car-info",
    entity_category=EntityCategory.DIAGNOSTIC,
    device_class=SensorDeviceClass.ENUM,
    state_class=None,
    value_fn=lambda vehicle: vehicle.vin,
    attributes_fn=lambda vehicle: format_vin_sensor_attributes(vehicle._vehicle_info),
)
ODOMETER_ENTITY_DESCRIPTION = ToyotaSensorEntityDescription(
    key="odometer",
    translation_key="odometer",
    icon="mdi:counter",
    device_class=SensorDeviceClass.DISTANCE,
    state_class=SensorStateClass.TOTAL_INCREASING,
    value_fn=lambda vehicle: None
    if vehicle.dashboard is None
    else round_number(vehicle.dashboard.odometer),
    suggested_display_precision=0,
    attributes_fn=lambda vehicle: None,  # noqa : ARG005
)
FUEL_LEVEL_ENTITY_DESCRIPTION = ToyotaSensorEntityDescription(
    key="fuel_level",
    translation_key="fuel_level",
    icon="mdi:gas-station",
    device_class=None,
    state_class=SensorStateClass.MEASUREMENT,
    value_fn=lambda vehicle: None
    if vehicle.dashboard is None
    else round_number(vehicle.dashboard.fuel_level),
    suggested_display_precision=0,
    attributes_fn=lambda vehicle: None,  # noqa : ARG005
)
FUEL_RANGE_ENTITY_DESCRIPTION = ToyotaSensorEntityDescription(
    key="fuel_range",
    translation_key="fuel_range",
    icon="mdi:map-marker-distance",
    device_class=SensorDeviceClass.DISTANCE,
    state_class=SensorStateClass.MEASUREMENT,
    value_fn=lambda vehicle: None
    if vehicle.dashboard is None
    else round_number(vehicle.dashboard.fuel_range),
    suggested_display_precision=0,
    attributes_fn=lambda vehicle: None,  # noqa : ARG005
)
BATTERY_LEVEL_ENTITY_DESCRIPTION = ToyotaSensorEntityDescription(
    key="battery_level",
    translation_key="battery_level",
    icon="mdi:car-electric",
    device_class=SensorDeviceClass.BATTERY,
    state_class=SensorStateClass.MEASUREMENT,
    value_fn=lambda vehicle: None
    if vehicle.dashboard is None
    else round_number(vehicle.dashboard.battery_level),
    suggested_display_precision=0,
    attributes_fn=lambda vehicle: None,  # noqa : ARG005
)
BATTERY_RANGE_ENTITY_DESCRIPTION = ToyotaSensorEntityDescription(
    key="battery_range",
    translation_key="battery_range",
    icon="mdi:map-marker-distance",
    device_class=SensorDeviceClass.DISTANCE,
    state_class=SensorStateClass.MEASUREMENT,
    value_fn=lambda vehicle: None
    if vehicle.dashboard is None
    else round_number(vehicle.dashboard.battery_range),
    suggested_display_precision=0,
    attributes_fn=lambda vehicle: None,  # noqa : ARG005
)
BATTERY_RANGE_AC_ENTITY_DESCRIPTION = ToyotaSensorEntityDescription(
    key="battery_range_ac",
    translation_key="battery_range_ac",
    icon="mdi:map-marker-distance",
    device_class=SensorDeviceClass.DISTANCE,
    state_class=SensorStateClass.MEASUREMENT,
    value_fn=lambda vehicle: None
    if vehicle.dashboard is None
    else round_number(vehicle.dashboard.battery_range_with_ac),
    suggested_display_precision=0,
    attributes_fn=lambda vehicle: None,  # noqa : ARG005
)
TOTAL_RANGE_ENTITY_DESCRIPTION = ToyotaSensorEntityDescription(
    key="total_range",
    translation_key="total_range",
    icon="mdi:map-marker-distance",
    device_class=SensorDeviceClass.DISTANCE,
    state_class=SensorStateClass.MEASUREMENT,
    value_fn=lambda vehicle: None
    if vehicle.dashboard is None
    else round_number(vehicle.dashboard.range),
    suggested_display_precision=0,
    attributes_fn=lambda vehicle: None,  # noqa : ARG005
)


class ToyotaStatisticsSensorEntityDescription(
    SensorEntityDescription, frozen_or_thawed=True
):
    """Describes a Toyota statistics sensor entity."""

    period: Literal["day", "week", "month", "year"]


STATISTICS_ENTITY_DESCRIPTIONS_DAILY = ToyotaStatisticsSensorEntityDescription(
    key="current_day_statistics",
    translation_key="current_day_statistics",
    icon="mdi:history",
    device_class=SensorDeviceClass.DISTANCE,
    state_class=SensorStateClass.MEASUREMENT,
    suggested_display_precision=0,
    period="day",
)

STATISTICS_ENTITY_DESCRIPTIONS_WEEKLY = ToyotaStatisticsSensorEntityDescription(
    key="current_week_statistics",
    translation_key="current_week_statistics",
    icon="mdi:history",
    device_class=SensorDeviceClass.DISTANCE,
    state_class=SensorStateClass.MEASUREMENT,
    suggested_display_precision=0,
    period="week",
)

STATISTICS_ENTITY_DESCRIPTIONS_MONTHLY = ToyotaStatisticsSensorEntityDescription(
    key="current_month_statistics",
    translation_key="current_month_statistics",
    icon="mdi:history",
    device_class=SensorDeviceClass.DISTANCE,
    state_class=SensorStateClass.MEASUREMENT,
    suggested_display_precision=0,
    period="month",
)

STATISTICS_ENTITY_DESCRIPTIONS_YEARLY = ToyotaStatisticsSensorEntityDescription(
    key="current_year_statistics",
    translation_key="current_year_statistics",
    icon="mdi:history",
    device_class=SensorDeviceClass.DISTANCE,
    state_class=SensorStateClass.MEASUREMENT,
    suggested_display_precision=0,
    period="year",
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_devices: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator: DataUpdateCoordinator[list[VehicleData]] = hass.data[DOMAIN][
        entry.entry_id
    ]

    sensors: list[Union[ToyotaSensor, ToyotaStatisticsSensor]] = []
    for index, _ in enumerate(coordinator.data):
        vehicle = coordinator.data[index]["data"]
        metric_values = coordinator.data[index]["metric_values"]

        capabilities_descriptions = [
            (
                True,
                VIN_ENTITY_DESCRIPTION,
                ToyotaSensor,
                None,
                None,
            ),
            (
                getattr(
                    getattr(vehicle._vehicle_info, "extended_capabilities", False),
                    "telemetry_capable",
                    False,
                ),
                ODOMETER_ENTITY_DESCRIPTION,
                ToyotaSensor,
                UnitOfLength.KILOMETERS
                if metric_values is True
                else UnitOfLength.MILES,
                UnitOfLength.KILOMETERS
                if metric_values is True
                else UnitOfLength.MILES,
            ),
            (
                getattr(
                    getattr(vehicle._vehicle_info, "extended_capabilities", False),
                    "fuel_level_available",
                    False,
                ),
                FUEL_LEVEL_ENTITY_DESCRIPTION,
                ToyotaSensor,
                PERCENTAGE,
                None,
            ),
            (
                getattr(
                    getattr(vehicle._vehicle_info, "extended_capabilities", False),
                    "fuel_range_available",
                    False,
                ),
                FUEL_RANGE_ENTITY_DESCRIPTION,
                ToyotaSensor,
                UnitOfLength.KILOMETERS
                if metric_values is True
                else UnitOfLength.MILES,
                UnitOfLength.KILOMETERS
                if metric_values is True
                else UnitOfLength.MILES,
            ),
            (
                getattr(
                    getattr(vehicle._vehicle_info, "extended_capabilities", False),
                    "econnect_vehicle_status_capable",
                    False,
                ),
                BATTERY_LEVEL_ENTITY_DESCRIPTION,
                ToyotaSensor,
                PERCENTAGE,
                None,
            ),
            (
                getattr(
                    getattr(vehicle._vehicle_info, "extended_capabilities", False),
                    "econnect_vehicle_status_capable",
                    False,
                ),
                BATTERY_RANGE_ENTITY_DESCRIPTION,
                ToyotaSensor,
                UnitOfLength.KILOMETERS
                if metric_values is True
                else UnitOfLength.MILES,
                UnitOfLength.KILOMETERS
                if metric_values is True
                else UnitOfLength.MILES,
            ),
            (
                getattr(
                    getattr(vehicle._vehicle_info, "extended_capabilities", False),
                    "econnect_vehicle_status_capable",
                    False,
                ),
                BATTERY_RANGE_AC_ENTITY_DESCRIPTION,
                ToyotaSensor,
                UnitOfLength.KILOMETERS
                if metric_values is True
                else UnitOfLength.MILES,
                UnitOfLength.KILOMETERS
                if metric_values is True
                else UnitOfLength.MILES,
            ),
            (
                getattr(
                    getattr(vehicle._vehicle_info, "extended_capabilities", False),
                    "econnect_vehicle_status_capable",
                    False,
                )
                and getattr(
                    getattr(vehicle._vehicle_info, "extended_capabilities", False),
                    "fuel_range_available",
                    False,
                ),
                TOTAL_RANGE_ENTITY_DESCRIPTION,
                ToyotaSensor,
                UnitOfLength.KILOMETERS
                if metric_values is True
                else UnitOfLength.MILES,
                UnitOfLength.KILOMETERS
                if metric_values is True
                else UnitOfLength.MILES,
            ),
            (
                True,  # TODO Unsure of the required capability
                STATISTICS_ENTITY_DESCRIPTIONS_DAILY,
                ToyotaStatisticsSensor,
                UnitOfLength.KILOMETERS
                if metric_values is True
                else UnitOfLength.MILES,
                UnitOfLength.KILOMETERS
                if metric_values is True
                else UnitOfLength.MILES,
            ),
            (
                True,  # TODO Unsure of the required capability
                STATISTICS_ENTITY_DESCRIPTIONS_WEEKLY,
                ToyotaStatisticsSensor,
                UnitOfLength.KILOMETERS
                if metric_values is True
                else UnitOfLength.MILES,
                UnitOfLength.KILOMETERS
                if metric_values is True
                else UnitOfLength.MILES,
            ),
            (
                True,  # TODO Unsure of the required capability
                STATISTICS_ENTITY_DESCRIPTIONS_MONTHLY,
                ToyotaStatisticsSensor,
                UnitOfLength.KILOMETERS
                if metric_values is True
                else UnitOfLength.MILES,
                UnitOfLength.KILOMETERS
                if metric_values is True
                else UnitOfLength.MILES,
            ),
            (
                True,  # TODO Unsure of the required capability
                STATISTICS_ENTITY_DESCRIPTIONS_YEARLY,
                ToyotaStatisticsSensor,
                UnitOfLength.KILOMETERS
                if metric_values is True
                else UnitOfLength.MILES,
                UnitOfLength.KILOMETERS
                if metric_values is True
                else UnitOfLength.MILES,
            ),
        ]

        sensors.extend(
            sensor_type(
                coordinator=coordinator,
                entry_id=entry.entry_id,
                vehicle_index=index,
                description=description,
                native_unit=native_unit,
                suggested_unit=suggested_unit,
            )
            for capability, description, sensor_type, native_unit, suggested_unit in capabilities_descriptions  # noqa: E501
            if capability
        )

    async_add_devices(sensors)


class ToyotaSensor(ToyotaBaseEntity, SensorEntity):
    """Representation of a Toyota sensor."""

    vehicle: Vehicle

    def __init__(  # noqa: PLR0913
        self,
        coordinator: DataUpdateCoordinator[list[VehicleData]],
        entry_id: str,
        vehicle_index: int,
        description: ToyotaSensorEntityDescription,
        native_unit: Union[UnitOfLength, str],
        suggested_unit: Union[UnitOfLength, str],
    ) -> None:
        """Initialise the ToyotaSensor class."""
        super().__init__(coordinator, entry_id, vehicle_index, description)
        self.description = description
        self._attr_native_unit_of_measurement = native_unit
        self._attr_suggested_unit_of_measurement = suggested_unit

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        return self.description.value_fn(self.vehicle)

    @property
    def extra_state_attributes(self) -> Optional[dict[str, Any]]:
        """Return the attributes of the sensor."""
        return self.description.attributes_fn(self.vehicle)


class ToyotaStatisticsSensor(ToyotaBaseEntity, SensorEntity):
    """Representation of a Toyota statistics sensor."""

    statistics: StatisticsData

    def __init__(  # noqa: PLR0913
        self,
        coordinator: DataUpdateCoordinator[list[VehicleData]],
        entry_id: str,
        vehicle_index: int,
        description: ToyotaStatisticsSensorEntityDescription,
        native_unit: Union[UnitOfLength, str],
        suggested_unit: Union[UnitOfLength, str],
    ) -> None:
        """Initialise the ToyotaStatisticsSensor class."""
        super().__init__(coordinator, entry_id, vehicle_index, description)
        self.period: Literal["day", "week", "month", "year"] = description.period
        self._attr_native_unit_of_measurement = native_unit
        self._attr_suggested_unit_of_measurement = suggested_unit

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        data = self.statistics[self.period]
        return round(data.distance, 1) if data and data.distance else None

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        data = self.statistics[self.period]
        return (
            format_statistics_attributes(data, self.vehicle._vehicle_info)
            if data
            else None
        )
