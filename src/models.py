"""
models.py
=========
Domain models for the Solar Forecast Engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ForecastHorizon(str, Enum):
    """Supported forecast time horizons."""
    HOURLY_24H = "hourly_24h"
    DAILY_7D = "daily_7d"
    DAILY_14D = "daily_14d"


@dataclass
class PVSite:
    """Configuration and metadata for a photovoltaic installation.

    Attributes:
        site_id:            Unique identifier for this PV site.
        name:               Human-readable site name.
        latitude:           Site latitude in decimal degrees.
        longitude:          Site longitude in decimal degrees.
        capacity_kwp:       Installed peak capacity in kilowatts-peak.
        panel_efficiency:   Panel efficiency (0–1 scale, e.g. 0.20 for 20%).
        tilt_deg:           Panel tilt angle from horizontal in degrees.
        azimuth_deg:        Panel azimuth angle (180 = south-facing).
        system_loss_factor: Combined DC/AC and wiring loss factor (0–1).
    """
    site_id: str
    name: str
    latitude: float
    longitude: float
    capacity_kwp: float
    panel_efficiency: float = 0.20
    tilt_deg: float = 30.0
    azimuth_deg: float = 180.0
    system_loss_factor: float = 0.80


@dataclass
class IrradianceReading:
    """A single hourly irradiance data point.

    Attributes:
        timestamp: ISO-8601 string or datetime of the hour.
        ghi_wm2:   Global Horizontal Irradiance in W/m².
        dni_wm2:   Direct Normal Irradiance in W/m² (optional).
        dhi_wm2:   Diffuse Horizontal Irradiance in W/m² (optional).
    """
    timestamp: str | datetime
    ghi_wm2: float
    dni_wm2: float = 0.0
    dhi_wm2: float = 0.0


@dataclass
class SolarForecast:
    """A complete solar generation forecast for a single PV site.

    Attributes:
        site_id:                 Identifier of the forecasted PV site.
        generated_at:            UTC datetime when this forecast was produced.
        horizon:                 Time horizon covered by this forecast.
        hourly_generation_kwh:   Estimated generation per hour in kWh.
        total_generation_kwh:    Sum of all hourly estimates.
        confidence_pct:          Optional model confidence percentage (0–100).
    """
    site_id: str
    generated_at: datetime
    horizon: ForecastHorizon
    hourly_generation_kwh: list[float] = field(default_factory=list)
    total_generation_kwh: float = 0.0
    confidence_pct: float | None = None
