"""Client."""
from datetime import datetime, timezone
import logging
import aiohttp
import numpy as np

_LOGGER = logging.getLogger(__name__)

INTENSITY = {
    "very low": 0,
    "low": 1,
    "moderate": 2,
    "high": 3,
    "very high": 4,
}

# Thresholds (gCO2/kWh) for very_low/low/moderate/high boundaries per year,
# reflecting the grid's decarbonisation trajectory.
INTENSITY_INDEXES = {
    2021: [50, 140, 220, 330],
    2022: [45, 130, 210, 310],
    2023: [40, 120, 200, 290],
    2024: [35, 110, 190, 270],
    2025: [30, 100, 180, 250],
    2026: [25, 90, 170, 230],
    2027: [20, 80, 160, 210],
    2028: [15, 70, 150, 190],
    2029: [10, 60, 140, 170],
    2030: [5, 50, 130, 150],
}

LOW_CARBON_SOURCES = ["biomass", "nuclear", "hydro", "solar", "wind"]
FOSSIL_FUEL_SOURCES = ["gas", "coal", "oil"]

_REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=10)


def _get_index(intensity, thresholds):
    """Return the intensity category string for a given gCO2/kWh value."""
    if intensity < thresholds[0]:
        return "very low"
    elif intensity < thresholds[1]:
        return "low"
    elif intensity < thresholds[2]:
        return "moderate"
    elif intensity < thresholds[3]:
        return "high"
    return "very high"


class Client:
    """Carbon Intensity API Client."""

    def __init__(self, postcode):
        self.postcode = postcode
        self.headers = {"Accept": "application/json"}
        _LOGGER.debug(str(self))

    def __str__(self):
        return "{ postcode: %s, headers: %s }" % (self.postcode, self.headers)

    async def async_get_data(self, from_time=None):
        """Fetch national and regional CO2 intensity data."""
        if from_time is None:
            from_time = datetime.now(timezone.utc)
        request_url = (
            "https://api.carbonintensity.org.uk/regional/intensity/%s/fw48h/postcode/%s"
            % (from_time.strftime("%Y-%m-%dT%H:%MZ"), self.postcode)
        )
        request_url_national = (
            "https://api.carbonintensity.org.uk/intensity/%s/fw24h/"
            % (from_time.strftime("%Y-%m-%dT%H:%MZ"))
        )
        _LOGGER.debug("Regional Request: %s", request_url)
        _LOGGER.debug("National Request: %s", request_url_national)
        async with aiohttp.ClientSession(timeout=_REQUEST_TIMEOUT) as session:
            async with session.get(request_url, headers=self.headers) as resp:
                resp.raise_for_status()
                json_response = await resp.json()
            async with session.get(request_url_national, headers=self.headers) as resp:
                resp.raise_for_status()
                json_response_national = await resp.json()
        return generate_response(json_response, json_response_national)


def generate_response(json_response, json_response_national):
    """Return processed intensity data including hourly forecast and optimal windows."""
    _LOGGER.debug(json_response)
    _LOGGER.debug(json_response_national)

    data = json_response["data"]["data"]
    postcode = json_response["data"]["postcode"]
    national_data = json_response_national["data"]

    # Cap to 96 periods (48 h) and require at least 48 (24 h).
    if len(data) > 96:
        data = data[:96]
    if len(data) < 48:
        return {"error": "malformed data"}
    # Keep even number of half-hour slots for clean hourly pairing.
    if len(data) % 2 == 1:
        data = data[:-1]

    two_day_forecast = len(data) >= 56

    # Year-aware intensity thresholds — fall back to 2030 values for years beyond the table.
    current_year = datetime.now(timezone.utc).year
    thresholds = INTENSITY_INDEXES.get(
        current_year, INTENSITY_INDEXES[max(INTENSITY_INDEXES)]
    )

    # Build a dict keyed by forecast intensity so we can find the minimum quickly.
    periods = {}
    for period in data:
        periods[period["intensity"]["forecast"]] = {
            "from": period["from"],
            "to": period["to"],
            "index": period["intensity"]["index"],
        }

    # Collect arrays for numpy processing.
    half_hour_intensities = []
    period_start = []
    period_end = []
    for period in data:
        period_start.append(
            datetime.strptime(period["from"], "%Y-%m-%dT%H:%MZ").replace(
                tzinfo=timezone.utc
            )
        )
        period_end.append(
            datetime.strptime(period["to"], "%Y-%m-%dT%H:%MZ").replace(
                tzinfo=timezone.utc
            )
        )
        half_hour_intensities.append(period["intensity"]["forecast"])

    # Average each pair of half-hour slots into hourly values.
    intensity_array = np.array(half_hour_intensities, dtype=float)
    hourly_intensities = np.convolve(intensity_array, np.ones(2) / 2, "valid")[::2]
    hours_start = period_start[::2]
    hours_end = period_end[1::2]

    # Best 2-hour window (4 consecutive hourly slots) in the next 24 h.
    average_intensity_24h = np.convolve(
        hourly_intensities[:24], np.ones(4) / 4, "valid"
    )
    best_24h = int(np.argmin(average_intensity_24h))

    if two_day_forecast:
        average_intensity_48h = np.convolve(
            hourly_intensities[24:], np.ones(4) / 4, "valid"
        )
        best_48h = int(np.argmin(average_intensity_48h))
    else:
        average_intensity_48h = None
        best_48h = 0

    # Build per-hour forecast list with an "optimal" flag.
    hourly_forecast = []
    for i, start_hour in enumerate(hours_start):
        in_24h_window = (
            start_hour >= hours_start[best_24h]
            and hours_end[i] <= hours_end[best_24h + 3]
        )
        in_48h_window = two_day_forecast and (
            start_hour >= hours_start[best_48h + 24]
            and hours_end[i] <= hours_end[best_48h + 3 + 24]
        )
        hourly_forecast.append(
            {
                "from": start_hour,
                "to": hours_end[i],
                "intensity": float(hourly_intensities[i]),
                "index": _get_index(hourly_intensities[i], thresholds),
                "optimal": in_24h_window or in_48h_window,
            }
        )

    # Generation mix percentages for the current period.
    low_carbon_pct = 0.0
    fossil_fuel_pct = 0.0
    for fuel_entry in data[0].get("generationmix", []):
        fuel = fuel_entry.get("fuel", "")
        perc = fuel_entry.get("perc", 0.0)
        if fuel in LOW_CARBON_SOURCES:
            low_carbon_pct += perc
        if fuel in FOSSIL_FUEL_SOURCES:
            fossil_fuel_pct += perc

    minimum_key = min(periods)

    return {
        "data": {
            "current_period_from": datetime.fromisoformat(
                data[0]["from"].replace("Z", "+00:00")
            ),
            "current_period_to": datetime.fromisoformat(
                data[0]["to"].replace("Z", "+00:00")
            ),
            "current_period_forecast": data[0]["intensity"]["forecast"],
            "current_period_index": data[0]["intensity"]["index"],
            "current_period_national_forecast": national_data[0]["intensity"][
                "forecast"
            ],
            "current_period_national_index": national_data[0]["intensity"]["index"],
            "current_low_carbon_percentage": round(low_carbon_pct, 1),
            "current_fossil_fuel_percentage": round(fossil_fuel_pct, 1),
            "lowest_period_from": datetime.fromisoformat(
                periods[minimum_key]["from"].replace("Z", "+00:00")
            ),
            "lowest_period_to": datetime.fromisoformat(
                periods[minimum_key]["to"].replace("Z", "+00:00")
            ),
            "lowest_period_forecast": minimum_key,
            "lowest_period_index": periods[minimum_key]["index"],
            "optimal_window_from": hours_start[best_24h],
            "optimal_window_to": hours_end[best_24h + 3],
            "optimal_window_forecast": float(average_intensity_24h[best_24h]),
            "optimal_window_index": _get_index(
                average_intensity_24h[best_24h], thresholds
            ),
            "optimal_window_48_from": hours_start[best_48h + 24]
            if two_day_forecast
            else None,
            "optimal_window_48_to": hours_end[best_48h + 3 + 24]
            if two_day_forecast
            else None,
            "optimal_window_48_forecast": float(average_intensity_48h[best_48h])
            if two_day_forecast
            else None,
            "optimal_window_48_index": _get_index(
                average_intensity_48h[best_48h], thresholds
            )
            if two_day_forecast
            else None,
            "unit": "gCO2/kWh",
            "forecast": hourly_forecast,
            "postcode": postcode,
        }
    }
