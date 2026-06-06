"""Tests for curves tools (HR and pace curves)."""

import json
from unittest.mock import AsyncMock, MagicMock

from httpx import Response

from intervals_icu_mcp.tools.curves import get_hr_curves, get_pace_curves


def _mock_ctx(mock_config):
    ctx = MagicMock()
    ctx.get_state = AsyncMock(return_value=mock_config)
    return ctx


class TestGetHRCurves:
    async def test_success(self, mock_config, respx_mock):
        respx_mock.get("/athlete/i123456/hr-curves").mock(
            return_value=Response(200, json={
                "name": "HR Curve",
                "type": "hr",
                "data": [
                    {"secs": 5, "bpm": 195, "date": "2025-10-01"},
                    {"secs": 60, "bpm": 185, "date": "2025-10-05"},
                    {"secs": 300, "bpm": 175, "date": "2025-10-08"},
                    {"secs": 1200, "bpm": 165, "date": "2025-10-12"},
                ],
            })
        )
        result = await get_hr_curves(ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert "peak_efforts" in parsed["data"]
        assert parsed["data"]["period"] == "90_days"

    async def test_empty_data(self, mock_config, respx_mock):
        respx_mock.get("/athlete/i123456/hr-curves").mock(
            return_value=Response(200, json={
                "name": "HR Curve",
                "type": "hr",
                "data": [],
            })
        )
        result = await get_hr_curves(ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["data"]["hr_curve"] == []

    async def test_with_days_back(self, mock_config, respx_mock):
        respx_mock.get("/athlete/i123456/hr-curves").mock(
            return_value=Response(200, json={
                "name": "HR Curve",
                "type": "hr",
                "data": [{"secs": 5, "bpm": 195}],
            })
        )
        result = await get_hr_curves(days_back=30, ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["data"]["period"] == "30_days"

    async def test_with_time_period_week(self, mock_config, respx_mock):
        respx_mock.get("/athlete/i123456/hr-curves").mock(
            return_value=Response(200, json={
                "name": "HR Curve",
                "type": "hr",
                "data": [{"secs": 5, "bpm": 195}],
            })
        )
        result = await get_hr_curves(time_period="week", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["data"]["period"] == "week"

    async def test_invalid_time_period(self, mock_config, respx_mock):
        result = await get_hr_curves(time_period="invalid", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert "error" in parsed

    async def test_api_error(self, mock_config, respx_mock):
        respx_mock.get("/athlete/i123456/hr-curves").mock(return_value=Response(401))
        result = await get_hr_curves(ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert "error" in parsed

    async def test_all_time_period(self, mock_config, respx_mock):
        respx_mock.get("/athlete/i123456/hr-curves").mock(
            return_value=Response(200, json={
                "name": "HR Curve",
                "type": "hr",
                "data": [{"secs": 5, "bpm": 195}],
            })
        )
        result = await get_hr_curves(time_period="all", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["data"]["period"] == "all_time"


class TestGetPaceCurves:
    async def test_success(self, mock_config, respx_mock):
        respx_mock.get("/athlete/i123456/pace-curves").mock(
            return_value=Response(200, json={
                "name": "Pace Curve",
                "type": "pace",
                "data": [
                    {"secs": 60, "pace": 3.5, "date": "2025-10-01"},
                    {"secs": 300, "pace": 4.0, "date": "2025-10-05"},
                    {"secs": 1200, "pace": 4.5, "date": "2025-10-08"},
                ],
            })
        )
        result = await get_pace_curves(ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert "peak_efforts" in parsed["data"]

    async def test_empty_data(self, mock_config, respx_mock):
        respx_mock.get("/athlete/i123456/pace-curves").mock(
            return_value=Response(200, json={
                "name": "Pace Curve",
                "type": "pace",
                "data": [],
            })
        )
        result = await get_pace_curves(ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["data"]["pace_curve"] == []

    async def test_with_gap(self, mock_config, respx_mock):
        respx_mock.get("/athlete/i123456/pace-curves").mock(
            return_value=Response(200, json={
                "name": "Pace Curve",
                "type": "pace",
                "data": [{"secs": 60, "pace": 3.5}],
            })
        )
        result = await get_pace_curves(use_gap=True, ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert "peak_efforts" in parsed["data"]

    async def test_invalid_time_period(self, mock_config, respx_mock):
        result = await get_pace_curves(time_period="invalid", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert "error" in parsed

    async def test_api_error(self, mock_config, respx_mock):
        respx_mock.get("/athlete/i123456/pace-curves").mock(return_value=Response(401))
        result = await get_pace_curves(ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert "error" in parsed
