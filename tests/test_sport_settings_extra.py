"""Additional tests for sport_settings tools to improve coverage."""

import json
import os
from unittest.mock import patch

import pytest
import respx as respx_lib
from httpx import Response

from intervals_icu_mcp.tools.sport_settings import (
    create_sport_settings,
    get_sport_settings,
    update_sport_settings,
)

_ENV = {
    "INTERVALS_ICU_API_KEY": "test_api_key_12345",
    "INTERVALS_ICU_ATHLETE_ID": "i999999",
}


@pytest.fixture
def ss_mock():
    with respx_lib.mock(base_url="https://intervals.icu/api/v1", assert_all_called=False) as mock:
        yield mock


class TestGetSportSettingsWithThresholds:
    @patch.dict(os.environ, _ENV)
    async def test_swim_threshold(self, ss_mock):
        """Test swim threshold formatting."""
        ss_mock.get("/athlete/i999999/sport-settings").mock(
            return_value=Response(200, json=[
                {"id": 1, "type": "Swim", "swim_threshold": 1.5},
            ])
        )
        result = await get_sport_settings()
        parsed = json.loads(result)
        assert "swim_threshold" in parsed["data"]["sport_settings"][0]

    @patch.dict(os.environ, _ENV)
    async def test_pace_threshold(self, ss_mock):
        """Test pace threshold formatting."""
        ss_mock.get("/athlete/i999999/sport-settings").mock(
            return_value=Response(200, json=[
                {"id": 2, "type": "Run", "pace_threshold": 4.5},
            ])
        )
        result = await get_sport_settings()
        parsed = json.loads(result)
        assert "pace_threshold" in parsed["data"]["sport_settings"][0]


class TestUpdateSportSettingsWithThresholds:
    @patch.dict(os.environ, _ENV)
    async def test_update_pace_threshold(self, ss_mock):
        ss_mock.put("/athlete/i999999/sport-settings/2").mock(
            return_value=Response(200, json={
                "id": 2, "type": "Run", "pace_threshold": 4.5,
            })
        )
        result = await update_sport_settings(sport_id=2, pace_threshold=4.5)
        parsed = json.loads(result)
        assert "pace_threshold" in parsed["data"]

    @patch.dict(os.environ, _ENV)
    async def test_update_swim_threshold(self, ss_mock):
        ss_mock.put("/athlete/i999999/sport-settings/3").mock(
            return_value=Response(200, json={
                "id": 3, "type": "Swim", "swim_threshold": 1.5,
            })
        )
        result = await update_sport_settings(sport_id=3, swim_threshold=1.5)
        parsed = json.loads(result)
        assert "swim_threshold" in parsed["data"]

    @patch.dict(os.environ, _ENV)
    async def test_api_error(self, ss_mock):
        ss_mock.put("/athlete/i999999/sport-settings/1").mock(
            return_value=Response(401)
        )
        result = await update_sport_settings(sport_id=1, ftp=300)
        parsed = json.loads(result)
        assert "error" in parsed


class TestCreateSportSettingsAllThresholds:
    @patch.dict(os.environ, _ENV)
    async def test_with_all_thresholds(self, ss_mock):
        ss_mock.post("/athlete/i999999/sport-settings").mock(
            return_value=Response(200, json={
                "id": 4, "type": "Ride",
                "ftp": 250, "fthr": 165,
                "pace_threshold": 4.5, "swim_threshold": 1.5,
            })
        )
        result = await create_sport_settings(
            sport_type="Ride", ftp=250, fthr=165, pace_threshold=4.5, swim_threshold=1.5
        )
        parsed = json.loads(result)
        assert parsed["data"]["ftp_watts"] == 250
        assert "pace_threshold" in parsed["data"]
        assert "swim_threshold" in parsed["data"]

    @patch.dict(os.environ, _ENV)
    async def test_api_error(self, ss_mock):
        ss_mock.post("/athlete/i999999/sport-settings").mock(
            return_value=Response(401)
        )
        result = await create_sport_settings(sport_type="Ride")
        parsed = json.loads(result)
        assert "error" in parsed
