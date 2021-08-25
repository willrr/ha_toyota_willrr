"""Toyota integration"""
import asyncio
import asyncio.exceptions as asyncioexceptions
from datetime import timedelta
import logging

import async_timeout
import httpx
from mytoyota.client import MyT
from mytoyota.exceptions import ToyotaInternalServerError, ToyotaLoginError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, CONF_REGION
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_LOCALE,
    DATA_CLIENT,
    DATA_COORDINATOR,
    DOMAIN,
    MONTHLY,
    PLATFORMS,
    STARTUP_MESSAGE,
    STATISTICS,
    VIN,
    WEEKLY,
    YEARLY,
)

_LOGGER = logging.getLogger(__name__)

# Update sensors every 5 minutes
UPDATE_INTERVAL = timedelta(seconds=300)


async def with_timeout(task, timeout_seconds=15):
    """Run an async task with a timeout."""
    async with async_timeout.timeout(timeout_seconds):
        return await task


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Toyota Connected Services from a config entry."""
    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})
        _LOGGER.info(STARTUP_MESSAGE)

    email = entry.data[CONF_EMAIL]
    password = entry.data[CONF_PASSWORD]
    locale = entry.data[CONF_LOCALE]
    region = entry.data[CONF_REGION]

    client = MyT(
        username=email,
        password=password,
        locale=locale,
        region=region.lower(),
    )

    await client.login()

    async def async_update_data():
        """Fetch data from Toyota API."""

        try:

            vehicles = []

            cars = await with_timeout(client.get_vehicles())

            for car in cars:
                # Use parallel request to get car data and statistics.

                vehicle_data = await asyncio.gather(
                    *[
                        client.get_vehicle_status(car),
                        client.get_driving_statistics(car[VIN], interval="isoweek"),
                        client.get_driving_statistics(car[VIN]),
                        client.get_driving_statistics(car[VIN], interval="year"),
                    ]
                )

                # Vehicle status
                vehicle = vehicle_data[0]

                # Vehicle statistics
                vehicle[STATISTICS] = {
                    WEEKLY: vehicle_data[1],
                    MONTHLY: vehicle_data[2],
                    YEARLY: vehicle_data[3],
                }

                vehicles.append(vehicle)

            _LOGGER.debug(vehicles)
            return vehicles

        except ToyotaLoginError as ex:
            _LOGGER.error(ex)
        except ToyotaInternalServerError as ex:
            raise UpdateFailed(ex) from ex
        except httpx.ConnectTimeout as ex:
            raise UpdateFailed("Unable to connect to Toyota Connected Services") from ex
        except (
            asyncioexceptions.CancelledError,
            asyncioexceptions.TimeoutError,
            httpx.ReadTimeout,
        ) as ex:

            raise UpdateFailed(
                "Update canceled! Toyota's API was too slow to respond."
                " Will try again later..."
            ) from ex

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=async_update_data,
        update_interval=UPDATE_INTERVAL,
    )

    # Fetch initial data so we have data when entities subscribe
    await coordinator.async_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        DATA_CLIENT: client,
        DATA_COORDINATOR: coordinator,
    }

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    # Setup components
    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
