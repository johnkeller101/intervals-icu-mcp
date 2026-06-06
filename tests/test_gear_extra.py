"""Additional tests for gear tools to improve coverage."""

import json
import os
from unittest.mock import patch

import pytest
import respx as respx_lib
from httpx import Response

from intervals_icu_mcp.tools.gear import (
    create_gear,
    create_gear_reminder,
    get_gear_list,
    update_gear,
    update_gear_reminder,
)

_ENV = {
    "INTERVALS_ICU_API_KEY": "test_api_key_12345",
    "INTERVALS_ICU_ATHLETE_ID": "i999999",
}


@pytest.fixture
def gear_mock():
    with respx_lib.mock(base_url="https://intervals.icu/api/v1", assert_all_called=False) as mock:
        yield mock


class TestGetGearListWithTimeReminders:
    @patch.dict(os.environ, _ENV)
    async def test_time_alert_reminder(self, gear_mock):
        """Test gear with time-based reminders."""
        gear_mock.get("/athlete/i999999/gear").mock(
            return_value=Response(200, json=[{
                "id": "g1",
                "name": "Bike",
                "gear_type": "BIKE",
                "active": True,
                "primary": True,
                "distance": None,
                "moving_time": 360000,
                "activity_count": 100,
                "reminders": [
                    {"id": 1, "text": "Service", "time_alert": 360000,
                     "is_due": True, "due_time": 7200, "snoozed_until": "2025-12-01"},
                ],
            }])
        )
        result = await get_gear_list()
        parsed = json.loads(result)
        gear = parsed["data"]["gear"][0]
        assert gear["reminders"][0]["is_due"] is True
        assert "snoozed_until" in gear["reminders"][0]

    @patch.dict(os.environ, _ENV)
    async def test_unexpected_error(self, gear_mock):
        """Test unexpected exception."""
        gear_mock.get("/athlete/i999999/gear").mock(
            side_effect=RuntimeError("network error")
        )
        result = await get_gear_list()
        parsed = json.loads(result)
        assert "error" in parsed


class TestCreateGearWithBrandModel:
    @patch.dict(os.environ, _ENV)
    async def test_with_brand_and_model(self, gear_mock):
        gear_mock.post("/athlete/i999999/gear").mock(
            return_value=Response(200, json={
                "id": "g3",
                "name": "Trail Shoes",
                "gear_type": "SHOE",
                "active": True,
                "primary": True,
                "brand": "Hoka",
                "model": "Speedgoat",
                "reminders": [],
            })
        )
        result = await create_gear(
            name="Trail Shoes", gear_type="SHOE",
            brand="Hoka", model="Speedgoat", primary=True
        )
        parsed = json.loads(result)
        assert parsed["data"]["brand"] == "Hoka"
        assert parsed["data"]["model"] == "Speedgoat"

    @patch.dict(os.environ, _ENV)
    async def test_api_error(self, gear_mock):
        gear_mock.post("/athlete/i999999/gear").mock(return_value=Response(401))
        result = await create_gear(name="Test", gear_type="OTHER")
        parsed = json.loads(result)
        assert "error" in parsed

    @patch.dict(os.environ, _ENV)
    async def test_unexpected_error(self, gear_mock):
        gear_mock.post("/athlete/i999999/gear").mock(
            side_effect=RuntimeError("network error")
        )
        result = await create_gear(name="Test", gear_type="OTHER")
        parsed = json.loads(result)
        assert "error" in parsed


class TestUpdateGearWithAllFields:
    @patch.dict(os.environ, _ENV)
    async def test_all_fields(self, gear_mock):
        gear_mock.put("/athlete/i999999/gear/g1").mock(
            return_value=Response(200, json={
                "id": "g1",
                "name": "Updated",
                "gear_type": "BIKE",
                "active": False,
                "primary": True,
                "brand": "Giant",
                "model": "TCR",
                "reminders": [],
            })
        )
        result = await update_gear(
            gear_id="g1",
            name="Updated",
            gear_type="BIKE",
            brand="Giant",
            model="TCR",
            active=False,
            primary=True,
        )
        parsed = json.loads(result)
        assert parsed["data"]["brand"] == "Giant"

    @patch.dict(os.environ, _ENV)
    async def test_api_error(self, gear_mock):
        gear_mock.put("/athlete/i999999/gear/g1").mock(return_value=Response(401))
        result = await update_gear(gear_id="g1", name="New")
        parsed = json.loads(result)
        assert "error" in parsed


class TestCreateGearReminderWithTimeAlert:
    @patch.dict(os.environ, _ENV)
    async def test_time_alert(self, gear_mock):
        gear_mock.post("/athlete/i999999/gear/g1/reminders").mock(
            return_value=Response(200, json={
                "id": 20,
                "text": "Service bike",
                "time_alert": 360000,
            })
        )
        result = await create_gear_reminder(
            gear_id="g1", text="Service bike", time_alert=100
        )
        parsed = json.loads(result)
        assert parsed["data"]["text"] == "Service bike"

    @patch.dict(os.environ, _ENV)
    async def test_api_error(self, gear_mock):
        gear_mock.post("/athlete/i999999/gear/g1/reminders").mock(
            return_value=Response(401)
        )
        result = await create_gear_reminder(
            gear_id="g1", text="Test", distance_alert=500.0
        )
        parsed = json.loads(result)
        assert "error" in parsed


class TestUpdateGearReminderFull:
    @patch.dict(os.environ, _ENV)
    async def test_with_due_info(self, gear_mock):
        gear_mock.put("/athlete/i999999/gear/g1/reminders/10").mock(
            return_value=Response(200, json={
                "id": 10,
                "text": "Updated",
                "distance_alert": 5000000,
                "time_alert": 360000,
                "is_due": True,
                "due_distance": 1000000,
                "due_time": 36000,
            })
        )
        result = await update_gear_reminder(
            gear_id="g1", reminder_id=10,
            text="Updated", distance_alert=5000.0, time_alert=100
        )
        parsed = json.loads(result)
        assert parsed["data"]["is_due"] is True

    @patch.dict(os.environ, _ENV)
    async def test_api_error(self, gear_mock):
        gear_mock.put("/athlete/i999999/gear/g1/reminders/10").mock(
            return_value=Response(401)
        )
        result = await update_gear_reminder(
            gear_id="g1", reminder_id=10, text="test"
        )
        parsed = json.loads(result)
        assert "error" in parsed
