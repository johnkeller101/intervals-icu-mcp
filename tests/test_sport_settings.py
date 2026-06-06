"""Tests for sport_settings tools."""

import json
import os
from unittest.mock import patch

import pytest
import respx as respx_lib
from httpx import Response

from intervals_icu_mcp.tools.sport_settings import (
    apply_sport_settings,
    create_sport_settings,
    delete_sport_settings,
    get_sport_settings,
    update_sport_settings,
)

# sport_settings.py uses load_config()/validate_credentials() directly.
# validate_credentials rejects athlete_id "i123456" as placeholder, so use a different ID.
_ENV = {
    "INTERVALS_ICU_API_KEY": "test_api_key_12345",
    "INTERVALS_ICU_ATHLETE_ID": "i999999",
}


@pytest.fixture
def ss_mock():
    with respx_lib.mock(base_url="https://intervals.icu/api/v1", assert_all_called=False) as mock:
        yield mock


class TestGetSportSettings:
    @patch.dict(os.environ, _ENV)
    async def test_success(self, ss_mock):
        ss_mock.get("/athlete/i999999/sport-settings").mock(
            return_value=Response(200, json=[
                {"id": 1, "type": "Ride", "ftp": 250, "fthr": 165},
                {"id": 2, "type": "Run", "pace_threshold": 4.5},
            ])
        )
        result = await get_sport_settings()
        parsed = json.loads(result)
        assert len(parsed["data"]["sport_settings"]) == 2
        assert parsed["data"]["sport_settings"][0]["ftp_watts"] == 250

    @patch.dict(os.environ, _ENV)
    async def test_empty(self, ss_mock):
        ss_mock.get("/athlete/i999999/sport-settings").mock(
            return_value=Response(200, json=[])
        )
        result = await get_sport_settings()
        parsed = json.loads(result)
        assert "No sport settings" in parsed["data"]["message"]

    @patch.dict(os.environ, _ENV)
    async def test_api_error(self, ss_mock):
        ss_mock.get("/athlete/i999999/sport-settings").mock(
            return_value=Response(401)
        )
        result = await get_sport_settings()
        parsed = json.loads(result)
        assert "error" in parsed


class TestUpdateSportSettings:
    @patch.dict(os.environ, _ENV)
    async def test_success(self, ss_mock):
        ss_mock.put("/athlete/i999999/sport-settings/1").mock(
            return_value=Response(200, json={
                "id": 1, "type": "Ride", "ftp": 260, "fthr": 168,
            })
        )
        result = await update_sport_settings(sport_id=1, ftp=260, fthr=168)
        parsed = json.loads(result)
        assert parsed["data"]["ftp_watts"] == 260

    @patch.dict(os.environ, _ENV)
    async def test_no_fields(self, ss_mock):
        result = await update_sport_settings(sport_id=1)
        parsed = json.loads(result)
        assert "error" in parsed


class TestApplySportSettings:
    @patch.dict(os.environ, _ENV)
    async def test_success(self, ss_mock):
        ss_mock.post("/athlete/i999999/sport-settings/1/apply").mock(
            return_value=Response(200, json={"updated": 15})
        )
        result = await apply_sport_settings(sport_id=1)
        parsed = json.loads(result)
        assert "data" in parsed

    @patch.dict(os.environ, _ENV)
    async def test_api_error(self, ss_mock):
        ss_mock.post("/athlete/i999999/sport-settings/1/apply").mock(
            return_value=Response(401)
        )
        result = await apply_sport_settings(sport_id=1)
        parsed = json.loads(result)
        assert "error" in parsed


class TestCreateSportSettings:
    @patch.dict(os.environ, _ENV)
    async def test_success(self, ss_mock):
        ss_mock.post("/athlete/i999999/sport-settings").mock(
            return_value=Response(200, json={
                "id": 3, "type": "Swim", "swim_threshold": 1.5,
            })
        )
        result = await create_sport_settings(sport_type="Swim", swim_threshold=1.5)
        parsed = json.loads(result)
        assert parsed["data"]["id"] == 3


class TestDeleteSportSettings:
    @patch.dict(os.environ, _ENV)
    async def test_success(self, ss_mock):
        ss_mock.delete("/athlete/i999999/sport-settings/1").mock(
            return_value=Response(200)
        )
        result = await delete_sport_settings(sport_id=1)
        parsed = json.loads(result)
        assert parsed["data"]["deleted"] is True

    @patch.dict(os.environ, _ENV)
    async def test_api_error(self, ss_mock):
        ss_mock.delete("/athlete/i999999/sport-settings/99").mock(
            return_value=Response(404)
        )
        result = await delete_sport_settings(sport_id=99)
        parsed = json.loads(result)
        assert "error" in parsed
