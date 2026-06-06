"""Tests for activities tools."""

import json
from unittest.mock import AsyncMock, MagicMock

from httpx import Response

from intervals_icu_mcp.tools.activities import (
    delete_activity,
    download_activity_file,
    get_activities_around,
    get_activity_details,
    get_recent_activities,
    search_activities,
    search_activities_full,
    update_activity,
)


def _mock_ctx(mock_config):
    ctx = MagicMock()
    ctx.get_state = AsyncMock(return_value=mock_config)
    return ctx


class TestGetRecentActivities:
    async def test_success(self, mock_config, respx_mock, mock_activity_data):
        respx_mock.get("/athlete/i123456/activities").mock(
            return_value=Response(200, json=[mock_activity_data])
        )
        result = await get_recent_activities(ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["data"]["count"] == 1
        assert parsed["data"]["activities"][0]["name"] == "Morning Ride"

    async def test_empty_results(self, mock_config, respx_mock):
        respx_mock.get("/athlete/i123456/activities").mock(
            return_value=Response(200, json=[])
        )
        result = await get_recent_activities(ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["data"]["count"] == 0

    async def test_type_filter(self, mock_config, respx_mock, mock_activity_data):
        run_data = {**mock_activity_data, "type": "Run"}
        respx_mock.get("/athlete/i123456/activities").mock(
            return_value=Response(200, json=[mock_activity_data, run_data])
        )
        result = await get_recent_activities(activity_type="Run", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["data"]["count"] == 1

    async def test_api_error(self, mock_config, respx_mock):
        respx_mock.get("/athlete/i123456/activities").mock(
            return_value=Response(401)
        )
        result = await get_recent_activities(ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert "error" in parsed

    async def test_with_oldest_param(self, mock_config, respx_mock, mock_activity_data):
        respx_mock.get("/athlete/i123456/activities").mock(
            return_value=Response(200, json=[mock_activity_data])
        )
        result = await get_recent_activities(oldest="2025-01-01", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["data"]["count"] == 1


class TestGetActivityDetails:
    async def test_success(self, mock_config, respx_mock, mock_activity_data):
        full_data = {**mock_activity_data, "description": "A great ride", "calories": 1500}
        respx_mock.get("/activity/12345").mock(
            return_value=Response(200, json=full_data)
        )
        result = await get_activity_details(activity_id="12345", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["data"]["name"] == "Morning Ride"
        assert parsed["data"]["other"]["calories"] == 1500

    async def test_api_error(self, mock_config, respx_mock):
        respx_mock.get("/activity/99999").mock(return_value=Response(404))
        result = await get_activity_details(activity_id="99999", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert "error" in parsed


class TestSearchActivities:
    async def test_success(self, mock_config, respx_mock):
        respx_mock.get("/athlete/i123456/activities/search").mock(
            return_value=Response(200, json=[
                {"id": "a1", "name": "Long Ride", "start_date_local": "2025-10-13T08:00:00"},
            ])
        )
        result = await search_activities(query="Long", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["data"]["count"] == 1

    async def test_empty_query(self, mock_config, respx_mock):
        result = await search_activities(query="  ", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert "error" in parsed

    async def test_no_results(self, mock_config, respx_mock):
        respx_mock.get("/athlete/i123456/activities/search").mock(
            return_value=Response(200, json=[])
        )
        result = await search_activities(query="nonexistent", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["data"]["count"] == 0


class TestSearchActivitiesFull:
    async def test_success(self, mock_config, respx_mock, mock_activity_data):
        respx_mock.get("/athlete/i123456/activities/search-full").mock(
            return_value=Response(200, json=[mock_activity_data])
        )
        result = await search_activities_full(query="Morning", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["data"]["count"] == 1

    async def test_empty_query(self, mock_config, respx_mock):
        result = await search_activities_full(query="", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert "error" in parsed


class TestUpdateActivity:
    async def test_success(self, mock_config, respx_mock, mock_activity_data):
        updated = {**mock_activity_data, "name": "Updated Ride"}
        respx_mock.put("/activity/12345").mock(
            return_value=Response(200, json=updated)
        )
        result = await update_activity(
            activity_id="12345", name="Updated Ride", ctx=_mock_ctx(mock_config)
        )
        parsed = json.loads(result)
        assert parsed["data"]["name"] == "Updated Ride"

    async def test_no_fields(self, mock_config, respx_mock):
        result = await update_activity(activity_id="12345", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert "error" in parsed


class TestDeleteActivity:
    async def test_success(self, mock_config, respx_mock):
        respx_mock.delete("/activity/12345").mock(return_value=Response(200))
        result = await delete_activity(activity_id="12345", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["data"]["deleted"] is True

    async def test_api_error(self, mock_config, respx_mock):
        respx_mock.delete("/activity/99999").mock(return_value=Response(404))
        result = await delete_activity(activity_id="99999", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert "error" in parsed


class TestDownloadActivityFile:
    async def test_success_base64(self, mock_config, respx_mock):
        respx_mock.get("/activity/12345/file").mock(
            return_value=Response(200, content=b"fake file content")
        )
        result = await download_activity_file(activity_id="12345", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["data"]["content_base64"] is not None

    async def test_api_error(self, mock_config, respx_mock):
        respx_mock.get("/activity/99999/file").mock(return_value=Response(404))
        result = await download_activity_file(activity_id="99999", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert "error" in parsed


class TestGetActivitiesAround:
    async def test_success(self, mock_config, respx_mock, mock_activity_data):
        activities = [
            {**mock_activity_data, "id": "a1", "start_date_local": "2025-10-12T08:00:00"},
            {**mock_activity_data, "id": "a2", "start_date_local": "2025-10-13T08:00:00"},
            {**mock_activity_data, "id": "a3", "start_date_local": "2025-10-14T08:00:00"},
        ]
        respx_mock.get("/athlete/i123456/activities-around").mock(
            return_value=Response(200, json=activities)
        )
        result = await get_activities_around(activity_id="a2", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["data"]["count"] == 3

    async def test_empty(self, mock_config, respx_mock):
        respx_mock.get("/athlete/i123456/activities-around").mock(
            return_value=Response(200, json=[])
        )
        result = await get_activities_around(activity_id="a2", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["data"]["count"] == 0
