"""Tests for activity_analysis tools."""

import json
from unittest.mock import AsyncMock, MagicMock

from httpx import Response

from intervals_icu_mcp.tools.activity_analysis import (
    get_activity_intervals,
    get_activity_streams,
    get_best_efforts,
    get_gap_histogram,
    get_hr_histogram,
    get_pace_histogram,
    get_power_histogram,
    search_intervals,
)


def _mock_ctx(mock_config):
    ctx = MagicMock()
    ctx.get_state = AsyncMock(return_value=mock_config)
    return ctx


class TestGetActivityStreams:
    async def test_success(self, mock_config, respx_mock):
        respx_mock.get("/activity/a1/streams").mock(
            return_value=Response(200, json={
                "watts": [100, 200, 300],
                "heartrate": [120, 130, 140],
                "time": [0, 1, 2],
            })
        )
        result = await get_activity_streams(activity_id="a1", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert "watts" in parsed["data"]["available_streams"]
        assert "heartrate" in parsed["data"]["available_streams"]

    async def test_no_streams(self, mock_config, respx_mock):
        respx_mock.get("/activity/a1/streams").mock(
            return_value=Response(200, json={})
        )
        result = await get_activity_streams(activity_id="a1", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["data"]["available_streams"] == []

    async def test_api_error(self, mock_config, respx_mock):
        respx_mock.get("/activity/a1/streams").mock(return_value=Response(404))
        result = await get_activity_streams(activity_id="a1", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert "error" in parsed


class TestGetActivityIntervals:
    async def test_success(self, mock_config, respx_mock):
        respx_mock.get("/activity/a1/intervals").mock(
            return_value=Response(200, json=[
                {"id": 1, "type": "WORK", "duration": 300, "average_watts": 250},
                {"id": 2, "type": "REST", "duration": 120, "average_watts": 100},
            ])
        )
        result = await get_activity_intervals(activity_id="a1", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["data"]["summary"]["work_intervals"] == 1
        assert parsed["data"]["summary"]["rest_intervals"] == 1

    async def test_empty(self, mock_config, respx_mock):
        respx_mock.get("/activity/a1/intervals").mock(
            return_value=Response(200, json=[])
        )
        result = await get_activity_intervals(activity_id="a1", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["data"]["count"] == 0

    async def test_api_error(self, mock_config, respx_mock):
        respx_mock.get("/activity/a1/intervals").mock(return_value=Response(401))
        result = await get_activity_intervals(activity_id="a1", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert "error" in parsed


class TestGetBestEfforts:
    async def test_success(self, mock_config, respx_mock):
        respx_mock.get("/activity/a1/best-efforts").mock(
            return_value=Response(200, json={
                "efforts": [
                    {"average": 300.0, "duration": 300, "start_index": 100, "end_index": 400},
                ]
            })
        )
        result = await get_best_efforts(
            activity_id="a1", duration=300, ctx=_mock_ctx(mock_config)
        )
        parsed = json.loads(result)
        assert parsed["data"]["count"] == 1
        assert parsed["data"]["best_efforts"][0]["average"] == 300.0

    async def test_no_duration_or_distance(self, mock_config, respx_mock):
        result = await get_best_efforts(activity_id="a1", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert "error" in parsed
        assert "duration" in parsed["error"]["message"].lower() or "distance" in parsed["error"]["message"].lower()

    async def test_empty_results(self, mock_config, respx_mock):
        respx_mock.get("/activity/a1/best-efforts").mock(
            return_value=Response(200, json={"efforts": []})
        )
        result = await get_best_efforts(
            activity_id="a1", duration=300, ctx=_mock_ctx(mock_config)
        )
        parsed = json.loads(result)
        assert parsed["data"]["count"] == 0

    async def test_with_distance(self, mock_config, respx_mock):
        respx_mock.get("/activity/a1/best-efforts").mock(
            return_value=Response(200, json={
                "efforts": [{"average": 5.0, "distance": 1000.0}]
            })
        )
        result = await get_best_efforts(
            activity_id="a1", stream="speed", distance=1000.0, ctx=_mock_ctx(mock_config)
        )
        parsed = json.loads(result)
        assert parsed["data"]["count"] == 1


class TestSearchIntervals:
    async def test_success(self, mock_config, respx_mock):
        respx_mock.get("/athlete/i123456/activities/interval-search").mock(
            return_value=Response(200, json=[
                {"type": "WORK", "duration": 300, "average_watts": 280},
            ])
        )
        result = await search_intervals(
            interval_type="WORK", ctx=_mock_ctx(mock_config)
        )
        parsed = json.loads(result)
        assert parsed["data"]["count"] == 1

    async def test_empty_results(self, mock_config, respx_mock):
        respx_mock.get("/athlete/i123456/activities/interval-search").mock(
            return_value=Response(200, json=[])
        )
        result = await search_intervals(ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["data"]["count"] == 0


class TestGetPowerHistogram:
    async def test_success(self, mock_config, respx_mock):
        respx_mock.get("/activity/a1/power-histogram").mock(
            return_value=Response(200, json={
                "bins": [
                    {"min": 0, "max": 100, "count": 50, "secs": 300},
                    {"min": 100, "max": 200, "count": 30, "secs": 180},
                ],
                "total_count": 80,
                "total_secs": 480,
            })
        )
        result = await get_power_histogram(activity_id="a1", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert len(parsed["data"]["bins"]) == 2

    async def test_empty(self, mock_config, respx_mock):
        respx_mock.get("/activity/a1/power-histogram").mock(
            return_value=Response(200, json={"bins": []})
        )
        result = await get_power_histogram(activity_id="a1", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["data"]["histogram"] == []


class TestGetHrHistogram:
    async def test_success(self, mock_config, respx_mock):
        respx_mock.get("/activity/a1/hr-histogram").mock(
            return_value=Response(200, json={
                "bins": [{"min": 120, "max": 140, "count": 100, "secs": 600}],
                "total_count": 100,
            })
        )
        result = await get_hr_histogram(activity_id="a1", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert len(parsed["data"]["bins"]) == 1

    async def test_empty(self, mock_config, respx_mock):
        respx_mock.get("/activity/a1/hr-histogram").mock(
            return_value=Response(200, json={"bins": []})
        )
        result = await get_hr_histogram(activity_id="a1", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["data"]["histogram"] == []


class TestGetPaceHistogram:
    async def test_success(self, mock_config, respx_mock):
        respx_mock.get("/activity/a1/pace-histogram").mock(
            return_value=Response(200, json={
                "bins": [{"min": 4.0, "max": 5.0, "count": 50, "secs": 300}],
                "total_count": 50,
            })
        )
        result = await get_pace_histogram(activity_id="a1", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert len(parsed["data"]["bins"]) == 1

    async def test_empty(self, mock_config, respx_mock):
        respx_mock.get("/activity/a1/pace-histogram").mock(
            return_value=Response(200, json={"bins": []})
        )
        result = await get_pace_histogram(activity_id="a1", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["data"]["histogram"] == []


class TestGetGapHistogram:
    async def test_success(self, mock_config, respx_mock):
        respx_mock.get("/activity/a1/gap-histogram").mock(
            return_value=Response(200, json={
                "bins": [{"min": 4.0, "max": 5.0, "count": 50, "secs": 300}],
                "total_count": 50,
            })
        )
        result = await get_gap_histogram(activity_id="a1", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert len(parsed["data"]["bins"]) == 1

    async def test_empty(self, mock_config, respx_mock):
        respx_mock.get("/activity/a1/gap-histogram").mock(
            return_value=Response(200, json={"bins": []})
        )
        result = await get_gap_histogram(activity_id="a1", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["data"]["histogram"] == []
