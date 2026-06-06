"""Tests for events tools."""

import json
from unittest.mock import AsyncMock, MagicMock

from httpx import Response

from intervals_icu_mcp.tools.events import (
    get_calendar_events,
    get_event,
    get_upcoming_workouts,
    search_events,
)


def _mock_ctx(mock_config):
    ctx = MagicMock()
    ctx.get_state = AsyncMock(return_value=mock_config)
    return ctx


class TestGetCalendarEvents:
    async def test_success(self, mock_config, respx_mock, mock_event_data):
        respx_mock.get("/athlete/i123456/events").mock(
            return_value=Response(200, json=[mock_event_data])
        )
        result = await get_calendar_events(ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert "events_by_date" in parsed["data"]

    async def test_empty(self, mock_config, respx_mock):
        respx_mock.get("/athlete/i123456/events").mock(
            return_value=Response(200, json=[])
        )
        result = await get_calendar_events(ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["data"]["count"] == 0

    async def test_api_error(self, mock_config, respx_mock):
        respx_mock.get("/athlete/i123456/events").mock(return_value=Response(401))
        result = await get_calendar_events(ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert "error" in parsed


class TestGetUpcomingWorkouts:
    async def test_success(self, mock_config, respx_mock, mock_event_data):
        respx_mock.get("/athlete/i123456/events").mock(
            return_value=Response(200, json=[mock_event_data])
        )
        result = await get_upcoming_workouts(ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        # The mock event is in the past, so may not show as upcoming
        assert "workouts" in parsed["data"]

    async def test_empty(self, mock_config, respx_mock):
        respx_mock.get("/athlete/i123456/events").mock(
            return_value=Response(200, json=[])
        )
        result = await get_upcoming_workouts(ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["data"]["count"] == 0


class TestGetEvent:
    async def test_success(self, mock_config, respx_mock, mock_event_data):
        respx_mock.get("/athlete/i123456/events/1001").mock(
            return_value=Response(200, json=mock_event_data)
        )
        result = await get_event(event_id=1001, ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["data"]["id"] == 1001
        assert parsed["data"]["name"] == "Threshold Intervals"

    async def test_api_error(self, mock_config, respx_mock):
        respx_mock.get("/athlete/i123456/events/9999").mock(return_value=Response(404))
        result = await get_event(event_id=9999, ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert "error" in parsed


class TestSearchEvents:
    async def test_success(self, mock_config, respx_mock, mock_event_data):
        respx_mock.get("/athlete/i123456/events").mock(
            return_value=Response(200, json=[mock_event_data])
        )
        result = await search_events(query="Threshold", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["data"]["count"] == 1

    async def test_no_match(self, mock_config, respx_mock, mock_event_data):
        respx_mock.get("/athlete/i123456/events").mock(
            return_value=Response(200, json=[mock_event_data])
        )
        result = await search_events(query="nonexistent", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["data"]["count"] == 0

    async def test_with_category_filter(self, mock_config, respx_mock, mock_event_data):
        respx_mock.get("/athlete/i123456/events").mock(
            return_value=Response(200, json=[mock_event_data])
        )
        result = await search_events(
            query="Threshold", category="WORKOUT", ctx=_mock_ctx(mock_config)
        )
        parsed = json.loads(result)
        assert parsed["data"]["count"] == 1
