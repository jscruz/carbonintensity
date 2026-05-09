from carbonintensity.client import Client, generate_response
import pytest
from datetime import datetime, timezone, date
import os
import json

TESTRESPONSE_FILENAME = os.path.join(os.path.dirname(__file__), "response.json")
TESTRESPONSENATIONAL_FILENAME = os.path.join(
    os.path.dirname(__file__), "response_national.json"
)

VALID_INDEXES = ["very low", "low", "moderate", "high", "very high"]


def test_string_format():
    client = Client("BH1")
    assert client.postcode == "BH1"
    assert client.headers == {"Accept": "application/json"}


def test_generate_response():
    with open(TESTRESPONSE_FILENAME) as json_file, open(
        TESTRESPONSENATIONAL_FILENAME
    ) as json_national_file:
        json_response = json.load(json_file)
        json_national_response = json.load(json_national_file)
        response = generate_response(json_response, json_national_response)

    data = response["data"]
    assert data["current_period_from"].strftime("%Y-%m-%dT%H:%M") == "2020-05-19T20:00"
    assert data["current_period_to"].strftime("%Y-%m-%dT%H:%M") == "2020-05-19T20:30"
    assert data["current_period_forecast"] == 307
    assert data["current_period_index"] == "high"
    assert data["current_period_national_index"] == "low"
    assert data["current_period_national_forecast"] == 145
    assert data["lowest_period_from"].strftime("%Y-%m-%dT%H:%M") == "2020-05-20T14:00"
    assert data["lowest_period_to"].strftime("%Y-%m-%dT%H:%M") == "2020-05-20T14:30"
    assert data["lowest_period_forecast"] == 161
    assert data["lowest_period_index"] == "moderate"
    assert data["postcode"] == "BH1"

    # Generation mix
    assert isinstance(data["current_low_carbon_percentage"], float)
    assert isinstance(data["current_fossil_fuel_percentage"], float)
    assert 0.0 <= data["current_low_carbon_percentage"] <= 100.0
    assert 0.0 <= data["current_fossil_fuel_percentage"] <= 100.0
    # biomass(6.5) + nuclear(4.9) + hydro(0.6) + solar(1.2) + wind(1.4) = 14.6
    assert data["current_low_carbon_percentage"] == 14.6
    # gas(73.2) + coal(0) = 73.2
    assert data["current_fossil_fuel_percentage"] == 73.2

    # Optimal window (24 h only — mock has 48 periods so two_day_forecast is False)
    assert isinstance(data["optimal_window_from"], datetime)
    assert isinstance(data["optimal_window_to"], datetime)
    assert isinstance(data["optimal_window_forecast"], float)
    assert data["optimal_window_index"] in VALID_INDEXES
    assert data["optimal_window_48_from"] is None
    assert data["optimal_window_48_to"] is None
    assert data["optimal_window_48_forecast"] is None
    assert data["optimal_window_48_index"] is None

    # Hourly forecast list
    assert isinstance(data["forecast"], list)
    assert len(data["forecast"]) == 24  # 48 half-hour slots → 24 hourly
    first = data["forecast"][0]
    assert isinstance(first["from"], datetime)
    assert isinstance(first["to"], datetime)
    assert isinstance(first["intensity"], float)
    assert first["index"] in VALID_INDEXES
    assert isinstance(first["optimal"], bool)


@pytest.mark.asyncio
async def test_request_data():
    client = Client("BH1")
    response = await client.async_get_data()
    print(response)
    data = response["data"]

    assert isinstance(data["current_period_from"], date)
    assert isinstance(data["current_period_to"], date)
    assert isinstance(data["current_period_forecast"], int)
    assert data["current_period_national_index"] in VALID_INDEXES
    assert isinstance(data["current_period_national_forecast"], int)
    assert data["current_period_index"] in VALID_INDEXES
    assert isinstance(data["current_low_carbon_percentage"], float)
    assert isinstance(data["current_fossil_fuel_percentage"], float)
    assert isinstance(data["lowest_period_from"], date)
    assert isinstance(data["lowest_period_to"], date)
    assert isinstance(data["lowest_period_forecast"], int)
    assert data["lowest_period_index"] in VALID_INDEXES
    assert isinstance(data["optimal_window_from"], date)
    assert isinstance(data["optimal_window_to"], date)
    assert isinstance(data["optimal_window_forecast"], float)
    assert data["optimal_window_index"] in VALID_INDEXES
    assert isinstance(data["forecast"], list)
    assert len(data["forecast"]) > 0
    assert data["postcode"] == "BH1"
