"""Additional tests for activities tools to improve coverage."""

import json
from unittest.mock import AsyncMock, MagicMock

from httpx import Response

from intervals_icu_mcp.tools.activities import (
    download_fit_file,
    download_gpx_file,
    get_activity_details,
    get_recent_activities,
    search_activities_full,
    update_activity,
)


def _mock_ctx(mock_config):
    ctx = MagicMock()
    ctx.get_state = AsyncMock(return_value=mock_config)
    return ctx


class TestDownloadFitFile:
    async def test_success_base64(self, mock_config, respx_mock):
        respx_mock.get("/activity/12345/fit-file").mock(
            return_value=Response(200, content=b"fake fit content")
        )
        result = await download_fit_file(activity_id="12345", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["data"]["format"] == "FIT"
        assert parsed["data"]["content_base64"] is not None

    async def test_api_error(self, mock_config, respx_mock):
        respx_mock.get("/activity/99999/fit-file").mock(return_value=Response(404))
        result = await download_fit_file(activity_id="99999", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert "error" in parsed


class TestDownloadGpxFile:
    async def test_success_base64(self, mock_config, respx_mock):
        respx_mock.get("/activity/12345/gpx-file").mock(
            return_value=Response(200, content=b"fake gpx content")
        )
        result = await download_gpx_file(activity_id="12345", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["data"]["format"] == "GPX"
        assert parsed["data"]["content_base64"] is not None

    async def test_api_error(self, mock_config, respx_mock):
        respx_mock.get("/activity/99999/gpx-file").mock(return_value=Response(404))
        result = await download_gpx_file(activity_id="99999", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert "error" in parsed


class TestActivityDetailsFullMetrics:
    async def test_full_details(self, mock_config, respx_mock):
        """Test activity with all metric fields populated."""
        full_data = {
            "id": "12345",
            "start_date_local": "2025-10-13T08:00:00",
            "name": "Morning Ride",
            "type": "Ride",
            "description": "Great ride",
            "distance": 50000.0,
            "moving_time": 7200,
            "elapsed_time": 7500,
            "total_elevation_gain": 500.0,
            "average_speed": 6.94,
            "max_speed": 12.0,
            "average_watts": 200,
            "normalized_power": 210,
            "weighted_average_watts": 205,
            "max_watts": 800,
            "variability_index": 1.05,
            "efficiency_factor": 1.27,
            "average_heartrate": 145,
            "max_heartrate": 185,
            "average_cadence": 85.0,
            "max_cadence": 110.0,
            "icu_training_load": 120,
            "icu_intensity": 0.84,
            "tss": 115.5,
            "hrss": 110.2,
            "trimp": 95.3,
            "feel": 4,
            "perceived_exertion": 7,
            "calories": 1500,
            "device_name": "Garmin Edge",
            "trainer": True,
            "indoor": True,
            "commute": False,
        }
        respx_mock.get("/activity/12345").mock(
            return_value=Response(200, json=full_data)
        )
        result = await get_activity_details(activity_id="12345", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["data"]["description"] == "Great ride"
        assert "power" in parsed["data"]
        assert parsed["data"]["power"]["variability_index"] == 1.05
        assert "heart_rate" in parsed["data"]
        assert "cadence" in parsed["data"]
        assert "training" in parsed["data"]
        assert "subjective" in parsed["data"]
        assert "other" in parsed["data"]
        assert parsed["data"]["other"]["indoor"] is True


class TestRecentActivitiesEdgeCases:
    async def test_with_newest_param(self, mock_config, respx_mock, mock_activity_data):
        """Test with newest date parameter."""
        respx_mock.get("/athlete/i123456/activities").mock(
            return_value=Response(200, json=[mock_activity_data])
        )
        result = await get_recent_activities(
            newest="2025-12-01", ctx=_mock_ctx(mock_config)
        )
        parsed = json.loads(result)
        assert parsed["data"]["count"] == 1

    async def test_activity_with_no_type(self, mock_config, respx_mock):
        """Test filtering when activity type is None."""
        data = {
            "id": "a1", "start_date_local": "2025-10-13T08:00:00",
            "name": "Mystery", "type": None,
        }
        respx_mock.get("/athlete/i123456/activities").mock(
            return_value=Response(200, json=[data])
        )
        result = await get_recent_activities(
            activity_type="Ride", ctx=_mock_ctx(mock_config)
        )
        parsed = json.loads(result)
        # Should filter out the None-type activity
        assert parsed["data"]["count"] == 0

    async def test_unexpected_error(self, mock_config, respx_mock):
        """Test unexpected (non-API) error."""
        respx_mock.get("/athlete/i123456/activities").mock(
            side_effect=RuntimeError("connection lost")
        )
        result = await get_recent_activities(ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert "error" in parsed
        assert parsed["error"]["type"] == "internal_error"


class TestSearchActivitiesFullEdgeCases:
    async def test_no_results(self, mock_config, respx_mock):
        respx_mock.get("/athlete/i123456/activities/search-full").mock(
            return_value=Response(200, json=[])
        )
        result = await search_activities_full(query="nothing", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["data"]["count"] == 0

    async def test_unexpected_error(self, mock_config, respx_mock):
        respx_mock.get("/athlete/i123456/activities/search-full").mock(
            side_effect=RuntimeError("bad")
        )
        result = await search_activities_full(query="test", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert "error" in parsed


class TestUpdateActivityEdgeCases:
    async def test_api_error(self, mock_config, respx_mock):
        respx_mock.put("/activity/12345").mock(return_value=Response(401))
        result = await update_activity(
            activity_id="12345", name="test", ctx=_mock_ctx(mock_config)
        )
        parsed = json.loads(result)
        assert "error" in parsed

    async def test_with_all_fields(self, mock_config, respx_mock):
        updated = {
            "id": "12345",
            "start_date_local": "2025-10-13T08:00:00",
            "name": "Updated",
            "type": "Run",
            "description": "Changed",
            "trainer": True,
            "commute": True,
            "feel": 5,
            "perceived_exertion": 8,
        }
        respx_mock.put("/activity/12345").mock(
            return_value=Response(200, json=updated)
        )
        result = await update_activity(
            activity_id="12345",
            name="Updated",
            description="Changed",
            activity_type="Run",
            trainer=True,
            commute=True,
            feel=5,
            perceived_exertion=8,
            ctx=_mock_ctx(mock_config),
        )
        parsed = json.loads(result)
        assert parsed["data"]["description"] == "Changed"
        assert parsed["data"]["feel"] == 5
        assert parsed["data"]["rpe"] == 8
