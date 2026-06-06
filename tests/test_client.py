"""Tests for client module."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
import respx
from httpx import Response

from intervals_icu_mcp.auth import ICUConfig
from intervals_icu_mcp.client import ICUAPIError, ICUClient


@pytest.fixture
def config():
    return ICUConfig(
        intervals_icu_api_key="test_key",
        intervals_icu_athlete_id="i123456",
    )


class TestICUAPIError:
    """Tests for ICUAPIError."""

    def test_basic_error(self):
        err = ICUAPIError("test error")
        assert err.message == "test error"
        assert err.status_code is None
        assert str(err) == "test error"

    def test_error_with_status(self):
        err = ICUAPIError("not found", status_code=404)
        assert err.status_code == 404

    def test_error_with_response_text(self):
        err = ICUAPIError("bad", status_code=400, response_text="details")
        assert err.response_text == "details"

    def test_error_with_payload(self):
        payload = {"name": "test"}
        err = ICUAPIError("bad", request_payload=payload)
        assert err.request_payload == payload


class TestICUClient:
    """Tests for ICUClient."""

    async def test_context_manager(self, config):
        """Test async context manager setup and teardown."""
        async with ICUClient(config) as client:
            assert client._client is not None
        # After exit, client should be closed

    async def test_request_without_context_manager(self, config):
        """Test that request raises without context manager."""
        client = ICUClient(config)
        with pytest.raises(RuntimeError, match="Client not initialized"):
            await client._request("GET", "/test")

    @respx.mock(base_url="https://intervals.icu/api/v1")
    async def test_get_athlete(self, config, respx_mock):
        """Test get_athlete API call."""
        respx_mock.get("/athlete/i123456").mock(
            return_value=Response(200, json={
                "id": "i123456",
                "name": "Test",
                "sport_settings": [],
            })
        )
        async with ICUClient(config) as client:
            athlete = await client.get_athlete()
            assert athlete.id == "i123456"
            assert athlete.name == "Test"

    @respx.mock(base_url="https://intervals.icu/api/v1")
    async def test_401_error(self, config, respx_mock):
        """Test 401 unauthorized error."""
        respx_mock.get("/athlete/i123456").mock(return_value=Response(401))
        async with ICUClient(config) as client:
            with pytest.raises(ICUAPIError, match="Unauthorized"):
                await client.get_athlete()

    @respx.mock(base_url="https://intervals.icu/api/v1")
    async def test_404_error(self, config, respx_mock):
        """Test 404 not found error."""
        respx_mock.get("/athlete/i123456").mock(return_value=Response(404))
        async with ICUClient(config) as client:
            with pytest.raises(ICUAPIError, match="not found"):
                await client.get_athlete()

    @respx.mock(base_url="https://intervals.icu/api/v1")
    async def test_429_error(self, config, respx_mock):
        """Test 429 rate limit error."""
        respx_mock.get("/athlete/i123456").mock(return_value=Response(429))
        async with ICUClient(config) as client:
            with pytest.raises(ICUAPIError, match="Rate limit"):
                await client.get_athlete()

    @respx.mock(base_url="https://intervals.icu/api/v1")
    async def test_400_error(self, config, respx_mock):
        """Test 400 bad request error."""
        respx_mock.get("/athlete/i123456").mock(
            return_value=Response(400, text="Bad request details")
        )
        async with ICUClient(config) as client:
            with pytest.raises(ICUAPIError) as exc_info:
                await client.get_athlete()
            assert exc_info.value.status_code == 400

    @respx.mock(base_url="https://intervals.icu/api/v1")
    async def test_get_activities(self, config, respx_mock):
        """Test get_activities API call."""
        respx_mock.get("/athlete/i123456/activities").mock(
            return_value=Response(200, json=[
                {"id": "a1", "start_date_local": "2025-10-13T08:00:00", "name": "Ride"},
            ])
        )
        async with ICUClient(config) as client:
            activities = await client.get_activities(oldest="2025-10-01")
            assert len(activities) == 1
            assert activities[0].id == "a1"

    @respx.mock(base_url="https://intervals.icu/api/v1")
    async def test_get_wellness(self, config, respx_mock):
        """Test get_wellness API call."""
        respx_mock.get("/athlete/i123456/wellness").mock(
            return_value=Response(200, json=[
                {"id": "2025-10-13", "weight": 70.0},
            ])
        )
        async with ICUClient(config) as client:
            records = await client.get_wellness(oldest="2025-10-01")
            assert len(records) == 1
            assert records[0].id == "2025-10-13"

    @respx.mock(base_url="https://intervals.icu/api/v1")
    async def test_get_events(self, config, respx_mock):
        """Test get_events API call."""
        respx_mock.get("/athlete/i123456/events").mock(
            return_value=Response(200, json=[
                {"id": 1001, "start_date_local": "2025-10-14", "name": "Test"},
            ])
        )
        async with ICUClient(config) as client:
            events = await client.get_events()
            assert len(events) == 1
            assert events[0].id == 1001

    @respx.mock(base_url="https://intervals.icu/api/v1")
    async def test_create_event(self, config, respx_mock):
        """Test create_event API call."""
        respx_mock.post("/athlete/i123456/events").mock(
            return_value=Response(200, json={
                "id": 2001,
                "start_date_local": "2025-10-15",
                "name": "New Event",
                "category": "WORKOUT",
            })
        )
        async with ICUClient(config) as client:
            event = await client.create_event({"name": "New Event"})
            assert event.id == 2001

    @respx.mock(base_url="https://intervals.icu/api/v1")
    async def test_delete_event(self, config, respx_mock):
        """Test delete_event API call."""
        respx_mock.delete("/athlete/i123456/events/1001").mock(
            return_value=Response(200)
        )
        async with ICUClient(config) as client:
            result = await client.delete_event(1001)
            assert result is True

    @respx.mock(base_url="https://intervals.icu/api/v1")
    async def test_get_gear(self, config, respx_mock):
        """Test get_gear API call."""
        respx_mock.get("/athlete/i123456/gear").mock(
            return_value=Response(200, json=[
                {"id": "g1", "name": "Road Bike", "reminders": []},
            ])
        )
        async with ICUClient(config) as client:
            gear = await client.get_gear()
            assert len(gear) == 1
            assert gear[0].id == "g1"

    @respx.mock(base_url="https://intervals.icu/api/v1")
    async def test_get_sport_settings(self, config, respx_mock):
        """Test get_sport_settings API call."""
        respx_mock.get("/athlete/i123456/sport-settings").mock(
            return_value=Response(200, json=[
                {"id": 1, "type": "Ride", "ftp": 250},
            ])
        )
        async with ICUClient(config) as client:
            settings = await client.get_sport_settings()
            assert len(settings) == 1
            assert settings[0].ftp == 250

    @respx.mock(base_url="https://intervals.icu/api/v1")
    async def test_get_power_curves(self, config, respx_mock):
        """Test get_power_curves API call."""
        respx_mock.get("/athlete/i123456/power-curves").mock(
            return_value=Response(200, json={
                "name": "Power", "type": "power", "data": [],
            })
        )
        async with ICUClient(config) as client:
            curve = await client.get_power_curves()
            assert curve.name == "Power"

    @respx.mock(base_url="https://intervals.icu/api/v1")
    async def test_get_workout_folders(self, config, respx_mock):
        """Test get_workout_folders API call."""
        respx_mock.get("/athlete/i123456/folders").mock(
            return_value=Response(200, json=[
                {"id": 1, "name": "My Workouts"},
            ])
        )
        async with ICUClient(config) as client:
            folders = await client.get_workout_folders()
            assert len(folders) == 1

    @respx.mock(base_url="https://intervals.icu/api/v1")
    async def test_get_activity_intervals(self, config, respx_mock):
        """Test get_activity_intervals API call."""
        respx_mock.get("/activity/a1/intervals").mock(
            return_value=Response(200, json=[
                {"id": 1, "type": "WORK", "duration": 300},
            ])
        )
        async with ICUClient(config) as client:
            intervals = await client.get_activity_intervals("a1")
            assert len(intervals) == 1

    @respx.mock(base_url="https://intervals.icu/api/v1")
    async def test_get_activity_streams(self, config, respx_mock):
        """Test get_activity_streams API call."""
        respx_mock.get("/activity/a1/streams").mock(
            return_value=Response(200, json={
                "watts": [100, 200, 300],
                "heartrate": [120, 130, 140],
            })
        )
        async with ICUClient(config) as client:
            streams = await client.get_activity_streams("a1")
            assert streams.watts == [100, 200, 300]

    @respx.mock(base_url="https://intervals.icu/api/v1")
    async def test_search_activities(self, config, respx_mock):
        """Test search_activities API call."""
        respx_mock.get("/athlete/i123456/activities/search").mock(
            return_value=Response(200, json=[
                {"id": "a1", "name": "Long Ride", "start_date_local": "2025-10-13T08:00:00"},
            ])
        )
        async with ICUClient(config) as client:
            results = await client.search_activities(query="Long")
            assert len(results) == 1

    @respx.mock(base_url="https://intervals.icu/api/v1")
    async def test_delete_activity(self, config, respx_mock):
        """Test delete_activity API call."""
        respx_mock.delete("/activity/a1").mock(return_value=Response(200))
        async with ICUClient(config) as client:
            result = await client.delete_activity("a1")
            assert result is True

    @respx.mock(base_url="https://intervals.icu/api/v1")
    async def test_mark_event_done(self, config, respx_mock):
        """Test mark_event_done API call."""
        respx_mock.post("/athlete/i123456/events/1001/mark-done").mock(
            return_value=Response(200, json={"status": "done"})
        )
        async with ICUClient(config) as client:
            result = await client.mark_event_done(1001)
            assert result["status"] == "done"

    @respx.mock(base_url="https://intervals.icu/api/v1")
    async def test_get_best_efforts(self, config, respx_mock):
        """Test get_best_efforts API call."""
        respx_mock.get("/activity/a1/best-efforts").mock(
            return_value=Response(200, json={"efforts": []})
        )
        async with ICUClient(config) as client:
            result = await client.get_best_efforts("a1", duration=300)
            assert result.efforts == []
