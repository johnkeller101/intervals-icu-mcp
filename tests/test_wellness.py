"""Tests for wellness tools."""

import json
from unittest.mock import AsyncMock, MagicMock

from httpx import Response

from intervals_icu_mcp.tools.wellness import (
    get_wellness_data,
    get_wellness_for_date,
    update_wellness,
)


def _mock_ctx(mock_config):
    ctx = MagicMock()
    ctx.get_state = AsyncMock(return_value=mock_config)
    return ctx


class TestGetWellnessData:
    async def test_success(self, mock_config, respx_mock, mock_wellness_data):
        respx_mock.get("/athlete/i123456/wellness").mock(
            return_value=Response(200, json=[mock_wellness_data])
        )
        result = await get_wellness_data(ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["data"]["count"] == 1
        assert parsed["data"]["wellness_data"][0]["date"].startswith("2025-10-13")

    async def test_empty(self, mock_config, respx_mock):
        respx_mock.get("/athlete/i123456/wellness").mock(
            return_value=Response(200, json=[])
        )
        result = await get_wellness_data(ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["data"]["count"] == 0

    async def test_trends_with_multiple_records(self, mock_config, respx_mock, mock_wellness_data):
        record2 = {**mock_wellness_data, "id": "2025-10-12", "hrv": 60.0, "restingHR": 50}
        respx_mock.get("/athlete/i123456/wellness").mock(
            return_value=Response(200, json=[mock_wellness_data, record2])
        )
        result = await get_wellness_data(ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert "trends" in parsed["data"]

    async def test_api_error(self, mock_config, respx_mock):
        respx_mock.get("/athlete/i123456/wellness").mock(return_value=Response(401))
        result = await get_wellness_data(ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert "error" in parsed


class TestGetWellnessForDate:
    async def test_success(self, mock_config, respx_mock, mock_wellness_data):
        respx_mock.get("/athlete/i123456/wellness/2025-10-13").mock(
            return_value=Response(200, json=mock_wellness_data)
        )
        result = await get_wellness_for_date(date="2025-10-13", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["data"]["date"].startswith("2025-10-13")
        assert parsed["data"]["heart"]["hrv_rmssd"] == 65.5

    async def test_invalid_date(self, mock_config, respx_mock):
        result = await get_wellness_for_date(date="bad-date", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert "error" in parsed

    async def test_api_error(self, mock_config, respx_mock):
        respx_mock.get("/athlete/i123456/wellness/2025-01-01").mock(
            return_value=Response(404)
        )
        result = await get_wellness_for_date(date="2025-01-01", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert "error" in parsed


class TestUpdateWellness:
    async def test_success(self, mock_config, respx_mock, mock_wellness_data):
        respx_mock.put("/athlete/i123456/wellness").mock(
            return_value=Response(200, json=mock_wellness_data)
        )
        result = await update_wellness(
            date="2025-10-13", weight=70.0, hrv=65.5, ctx=_mock_ctx(mock_config)
        )
        parsed = json.loads(result)
        assert parsed["data"]["weight_kg"] == 70.0

    async def test_no_data(self, mock_config, respx_mock):
        result = await update_wellness(date="2025-10-13", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert "error" in parsed

    async def test_invalid_date(self, mock_config, respx_mock):
        result = await update_wellness(date="bad-date", weight=70.0, ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert "error" in parsed

    async def test_api_error(self, mock_config, respx_mock):
        respx_mock.put("/athlete/i123456/wellness").mock(return_value=Response(401))
        result = await update_wellness(
            date="2025-10-13", weight=70.0, ctx=_mock_ctx(mock_config)
        )
        parsed = json.loads(result)
        assert "error" in parsed
