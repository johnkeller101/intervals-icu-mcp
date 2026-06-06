"""Tests for gear tools."""

import json
import os
from unittest.mock import patch

import pytest
import respx as respx_lib
from httpx import Response

from intervals_icu_mcp.tools.gear import (
    create_gear,
    create_gear_reminder,
    delete_gear,
    get_gear_list,
    update_gear,
    update_gear_reminder,
)

# gear.py uses load_config()/validate_credentials() directly.
# validate_credentials rejects athlete_id "i123456" as placeholder, so use a different ID.
_ENV = {
    "INTERVALS_ICU_API_KEY": "test_api_key_12345",
    "INTERVALS_ICU_ATHLETE_ID": "i999999",
}


@pytest.fixture
def gear_mock():
    with respx_lib.mock(base_url="https://intervals.icu/api/v1", assert_all_called=False) as mock:
        yield mock


class TestGetGearList:
    @patch.dict(os.environ, _ENV)
    async def test_success(self, gear_mock):
        gear_mock.get("/athlete/i999999/gear").mock(
            return_value=Response(200, json=[{
                "id": "g1",
                "name": "Road Bike",
                "gear_type": "BIKE",
                "active": True,
                "brand": "Trek",
                "model": "Madone",
                "distance": 50000.0,
                "moving_time": 36000,
                "activity_count": 100,
                "reminders": [
                    {"id": 1, "text": "Replace chain", "distance_alert": 5000000,
                     "is_due": False, "due_distance": 3000000},
                ],
            }])
        )
        result = await get_gear_list()
        parsed = json.loads(result)
        assert len(parsed["data"]["gear"]) == 1
        assert parsed["data"]["gear"][0]["name"] == "Road Bike"

    @patch.dict(os.environ, _ENV)
    async def test_empty(self, gear_mock):
        gear_mock.get("/athlete/i999999/gear").mock(
            return_value=Response(200, json=[])
        )
        result = await get_gear_list()
        parsed = json.loads(result)
        assert "No gear" in parsed["data"]["message"]

    @patch.dict(os.environ, _ENV)
    async def test_api_error(self, gear_mock):
        gear_mock.get("/athlete/i999999/gear").mock(return_value=Response(401))
        result = await get_gear_list()
        parsed = json.loads(result)
        assert "error" in parsed


class TestCreateGear:
    @patch.dict(os.environ, _ENV)
    async def test_success(self, gear_mock):
        gear_mock.post("/athlete/i999999/gear").mock(
            return_value=Response(200, json={
                "id": "g2",
                "name": "Running Shoes",
                "gear_type": "SHOE",
                "active": True,
                "primary": False,
                "reminders": [],
            })
        )
        result = await create_gear(name="Running Shoes", gear_type="SHOE")
        parsed = json.loads(result)
        assert parsed["data"]["id"] == "g2"


class TestUpdateGear:
    @patch.dict(os.environ, _ENV)
    async def test_success(self, gear_mock):
        gear_mock.put("/athlete/i999999/gear/g1").mock(
            return_value=Response(200, json={
                "id": "g1",
                "name": "Updated Bike",
                "gear_type": "BIKE",
                "active": True,
                "distance": 60000.0,
                "moving_time": 40000,
                "activity_count": 120,
                "reminders": [],
            })
        )
        result = await update_gear(gear_id="g1", name="Updated Bike")
        parsed = json.loads(result)
        assert parsed["data"]["name"] == "Updated Bike"

    @patch.dict(os.environ, _ENV)
    async def test_no_fields(self, gear_mock):
        result = await update_gear(gear_id="g1")
        parsed = json.loads(result)
        assert "error" in parsed


class TestDeleteGear:
    @patch.dict(os.environ, _ENV)
    async def test_success(self, gear_mock):
        gear_mock.delete("/athlete/i999999/gear/g1").mock(
            return_value=Response(200)
        )
        result = await delete_gear(gear_id="g1")
        parsed = json.loads(result)
        assert parsed["data"]["deleted"] is True


class TestCreateGearReminder:
    @patch.dict(os.environ, _ENV)
    async def test_success(self, gear_mock):
        gear_mock.post("/athlete/i999999/gear/g1/reminders").mock(
            return_value=Response(200, json={
                "id": 10,
                "text": "Replace chain",
                "distance_alert": 5000000,
            })
        )
        result = await create_gear_reminder(
            gear_id="g1", text="Replace chain", distance_alert=5000.0
        )
        parsed = json.loads(result)
        assert parsed["data"]["text"] == "Replace chain"

    @patch.dict(os.environ, _ENV)
    async def test_no_thresholds(self, gear_mock):
        result = await create_gear_reminder(gear_id="g1", text="Test")
        parsed = json.loads(result)
        assert "error" in parsed


class TestUpdateGearReminder:
    @patch.dict(os.environ, _ENV)
    async def test_success(self, gear_mock):
        gear_mock.put("/athlete/i999999/gear/g1/reminders/10").mock(
            return_value=Response(200, json={
                "id": 10,
                "text": "Updated reminder",
                "distance_alert": 6000000,
            })
        )
        result = await update_gear_reminder(
            gear_id="g1", reminder_id=10, text="Updated reminder"
        )
        parsed = json.loads(result)
        assert parsed["data"]["text"] == "Updated reminder"

    @patch.dict(os.environ, _ENV)
    async def test_no_fields(self, gear_mock):
        result = await update_gear_reminder(gear_id="g1", reminder_id=10)
        parsed = json.loads(result)
        assert "error" in parsed
