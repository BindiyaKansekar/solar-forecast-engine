"""
forecast_engine.py
==================
Core forecasting engine for the Solar Forecast Engine.

Combines irradiance model outputs with weather data to produce
short-term (hourly) and medium-term (daily) solar generation forecasts
for configured PV sites.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any

from .data_ingestion import WeatherDataIngester
from .models import ForecastHorizon, IrradianceReading, PVSite, SolarForecast

logger = logging.getLogger(__name__)

# Approximate panel efficiency degradation per degree Celsius above 25°C (STC)
_TEMP_COEFFICIENT = -0.004  # −0.4% per °C


class SolarForecastEngine:
    """Generate solar energy generation forecasts for a set of PV sites.

    Args:
        config:   Loaded configuration dict (from config.yaml).
        ingester: Weather/irradiance data ingestion client.
    """

    def __init__(self, config: dict[str, Any], ingester: WeatherDataIngester) -> None:
        self.config = config
        self.ingester = ingester
        self.sites: list[PVSite] = [PVSite(**s) for s in config.get("sites", [])]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_forecast(self, horizon: ForecastHorizon = ForecastHorizon.HOURLY_24H) -> list[SolarForecast]:
        """Run a forecast for all configured PV sites.

        Args:
            horizon: Time horizon for the forecast run.

        Returns:
            List of :class:`SolarForecast` objects, one per site.
        """
        forecasts: list[SolarForecast] = []
        for site in self.sites:
            try:
                forecast = self._forecast_site(site, horizon)
                forecasts.append(forecast)
                logger.info(
                    "Forecast complete — site=%s horizon=%s total_kwh=%.1f",
                    site.site_id, horizon.value, forecast.total_generation_kwh,
                )
            except Exception:
                logger.exception("Failed to forecast site %s", site.site_id)
        return forecasts

    # ------------------------------------------------------------------
    # Per-site forecasting
    # ------------------------------------------------------------------

    def _forecast_site(self, site: PVSite, horizon: ForecastHorizon) -> SolarForecast:
        """Produce a generation forecast for a single PV site.

        Args:
            site:    PV site configuration and metadata.
            horizon: Forecast time horizon.

        Returns:
            A :class:`SolarForecast` with hourly generation estimates.
        """
        irradiance_series = self.ingester.fetch_irradiance(
            lat=site.latitude,
            lon=site.longitude,
            horizon=horizon,
        )
        temperature_series = self.ingester.fetch_temperature(
            lat=site.latitude,
            lon=site.longitude,
            horizon=horizon,
        )

        hourly_kwh: list[float] = []
        for irr, temp in zip(irradiance_series, temperature_series):
            kwh = self._estimate_generation(site, irr, temp)
            hourly_kwh.append(kwh)

        return SolarForecast(
            site_id=site.site_id,
            generated_at=datetime.now(timezone.utc),
            horizon=horizon,
            hourly_generation_kwh=hourly_kwh,
            total_generation_kwh=sum(hourly_kwh),
        )

    def _estimate_generation(
        self, site: PVSite, irradiance: IrradianceReading, temperature_c: float
    ) -> float:
        """Estimate hourly generation (kWh) using a simplified PV model.

        Generation = GHI × Panel_area × Efficiency × Temperature_factor × System_losses

        Args:
            site:         PV site parameters (capacity, tilt, efficiency).
            irradiance:   Irradiance reading for the hour (W/m²).
            temperature_c: Ambient temperature in degrees Celsius.

        Returns:
            Estimated generation in kilowatt-hours for that hour.
        """
        # Temperature derating — panels lose efficiency above STC (25°C)
        temp_factor = 1.0 + _TEMP_COEFFICIENT * max(0.0, temperature_c - 25.0)

        # Simple energy estimate: P(kW) = GHI(W/m²) × area(m²) × η × temp_factor / 1000
        area_m2 = (site.capacity_kwp * 1000) / (irradiance.ghi_wm2 + 1e-6) if irradiance.ghi_wm2 > 0 else 0.0
        generation_kwh = (
            irradiance.ghi_wm2 * area_m2 * site.panel_efficiency * temp_factor * site.system_loss_factor / 1000.0
        )
        return max(0.0, generation_kwh)
