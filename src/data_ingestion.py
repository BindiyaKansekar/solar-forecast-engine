"""
data_ingestion.py
=================
Weather and irradiance data ingestion for the Solar Forecast Engine.

Supports multiple data providers (Open-Meteo, custom REST APIs).
Provider selection and credentials are controlled via config.yaml.
"""

from __future__ import annotations

import logging
from typing import Any

import requests

from .models import ForecastHorizon, IrradianceReading

logger = logging.getLogger(__name__)

# Open-Meteo free API base URL (no auth required)
_OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# Request timeout in seconds
_REQUEST_TIMEOUT = 10


class WeatherDataIngester:
    """Fetch irradiance and temperature data from a configured weather provider.

    Args:
        config: Loaded configuration dict (``weather`` section used).
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self._cfg = config.get("weather", {})
        self._provider: str = self._cfg.get("provider", "open_meteo")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch_irradiance(
        self, lat: float, lon: float, horizon: ForecastHorizon
    ) -> list[IrradianceReading]:
        """Retrieve hourly Global Horizontal Irradiance (GHI) forecasts.

        Args:
            lat:     Latitude of the PV site in decimal degrees.
            lon:     Longitude of the PV site in decimal degrees.
            horizon: Forecast horizon controlling how many hours to fetch.

        Returns:
            List of :class:`IrradianceReading` in chronological order.

        Raises:
            RuntimeError: If the data provider returns an error response.
        """
        if self._provider == "open_meteo":
            return self._fetch_open_meteo_irradiance(lat, lon, horizon)
        return self._fetch_custom_irradiance(lat, lon, horizon)

    def fetch_temperature(
        self, lat: float, lon: float, horizon: ForecastHorizon
    ) -> list[float]:
        """Retrieve hourly 2 m air temperature forecasts in degrees Celsius.

        Args:
            lat:     Latitude of the PV site in decimal degrees.
            lon:     Longitude of the PV site in decimal degrees.
            horizon: Forecast horizon controlling how many hours to fetch.

        Returns:
            List of temperature values (°C) in chronological order.
        """
        if self._provider == "open_meteo":
            return self._fetch_open_meteo_temperature(lat, lon, horizon)
        return self._fetch_custom_temperature(lat, lon, horizon)

    # ------------------------------------------------------------------
    # Open-Meteo provider
    # ------------------------------------------------------------------

    def _fetch_open_meteo_irradiance(
        self, lat: float, lon: float, horizon: ForecastHorizon
    ) -> list[IrradianceReading]:
        """Fetch GHI from the Open-Meteo free weather API.

        Args:
            lat:     Site latitude.
            lon:     Site longitude.
            horizon: Forecast horizon.

        Returns:
            List of :class:`IrradianceReading` objects.
        """
        days = self._horizon_to_days(horizon)
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": "shortwave_radiation",
            "forecast_days": days,
            "timezone": "UTC",
        }
        try:
            response = requests.get(_OPEN_METEO_URL, params=params, timeout=_REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            ghi_values: list[float] = data["hourly"]["shortwave_radiation"]
            times: list[str] = data["hourly"]["time"]
            return [
                IrradianceReading(timestamp=t, ghi_wm2=max(0.0, g))
                for t, g in zip(times, ghi_values)
            ]
        except Exception:
            logger.exception("Open-Meteo irradiance fetch failed — lat=%s lon=%s", lat, lon)
            raise

    def _fetch_open_meteo_temperature(
        self, lat: float, lon: float, horizon: ForecastHorizon
    ) -> list[float]:
        """Fetch 2 m air temperature from the Open-Meteo free weather API.

        Args:
            lat:     Site latitude.
            lon:     Site longitude.
            horizon: Forecast horizon.

        Returns:
            List of temperature values in °C.
        """
        days = self._horizon_to_days(horizon)
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": "temperature_2m",
            "forecast_days": days,
            "timezone": "UTC",
        }
        try:
            response = requests.get(_OPEN_METEO_URL, params=params, timeout=_REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            return data["hourly"]["temperature_2m"]
        except Exception:
            logger.exception("Open-Meteo temperature fetch failed — lat=%s lon=%s", lat, lon)
            raise

    # ------------------------------------------------------------------
    # Custom provider (stub — implement for proprietary APIs)
    # ------------------------------------------------------------------

    def _fetch_custom_irradiance(
        self, lat: float, lon: float, horizon: ForecastHorizon
    ) -> list[IrradianceReading]:
        raise NotImplementedError("Custom irradiance provider not implemented")

    def _fetch_custom_temperature(
        self, lat: float, lon: float, horizon: ForecastHorizon
    ) -> list[float]:
        raise NotImplementedError("Custom temperature provider not implemented")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _horizon_to_days(horizon: ForecastHorizon) -> int:
        """Map a :class:`ForecastHorizon` to a number of forecast days.

        Args:
            horizon: Forecast horizon enum value.

        Returns:
            Number of calendar days to request from the weather API.
        """
        mapping = {
            ForecastHorizon.HOURLY_24H: 1,
            ForecastHorizon.DAILY_7D: 7,
            ForecastHorizon.DAILY_14D: 14,
        }
        return mapping.get(horizon, 1)
