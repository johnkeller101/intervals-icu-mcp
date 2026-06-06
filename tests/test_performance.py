"""Tests for performance tools."""

import json
from unittest.mock import AsyncMock, MagicMock

from httpx import Response

from intervals_icu_mcp.tools.performance import get_power_curves


def _mock_ctx(mock_config):
    ctx = MagicMock()
    ctx.get_state = AsyncMock(return_value=mock_config)
    return ctx


class TestGetPowerCurves:
    async def test_success(self, mock_config, respx_mock):
        respx_mock.get("/athlete/i123456/power-curves").mock(
            return_value=Response(200, json={
                "name": "Power Curve",
                "type": "power",
                "data": [
                    {"secs": 5, "watts": 800, "date": "2025-10-01"},
                    {"secs": 60, "watts": 400, "date": "2025-10-05"},
                    {"secs": 300, "watts": 300, "date": "2025-10-08"},
                    {"secs": 1200, "watts": 250, "date": "2025-10-12"},
                ],
            })
        )
        result = await get_power_curves(ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert "peak_efforts" in parsed["data"]
        assert parsed["data"]["period"] == "90_days"

    async def test_empty_data(self, mock_config, respx_mock):
        respx_mock.get("/athlete/i123456/power-curves").mock(
            return_value=Response(200, json={
                "name": "Power Curve",
                "type": "power",
                "data": [],
            })
        )
        result = await get_power_curves(ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["data"]["power_curve"] == []

    async def test_with_days_back(self, mock_config, respx_mock):
        respx_mock.get("/athlete/i123456/power-curves").mock(
            return_value=Response(200, json={
                "name": "Power Curve",
                "type": "power",
                "data": [{"secs": 5, "watts": 800}],
            })
        )
        result = await get_power_curves(days_back=30, ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["data"]["period"] == "30_days"

    async def test_with_time_period_year(self, mock_config, respx_mock):
        respx_mock.get("/athlete/i123456/power-curves").mock(
            return_value=Response(200, json={
                "name": "Power Curve",
                "type": "power",
                "data": [{"secs": 5, "watts": 800}],
            })
        )
        result = await get_power_curves(time_period="year", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["data"]["period"] == "year"

    async def test_with_time_period_all(self, mock_config, respx_mock):
        respx_mock.get("/athlete/i123456/power-curves").mock(
            return_value=Response(200, json={
                "name": "Power Curve",
                "type": "power",
                "data": [{"secs": 5, "watts": 800}],
            })
        )
        result = await get_power_curves(time_period="all", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["data"]["period"] == "all_time"

    async def test_invalid_time_period(self, mock_config, respx_mock):
        result = await get_power_curves(time_period="invalid", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert "error" in parsed

    async def test_api_error(self, mock_config, respx_mock):
        respx_mock.get("/athlete/i123456/power-curves").mock(return_value=Response(401))
        result = await get_power_curves(ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert "error" in parsed

    async def test_ftp_analysis(self, mock_config, respx_mock):
        """Test FTP analysis is included when 20-min data is available."""
        respx_mock.get("/athlete/i123456/power-curves").mock(
            return_value=Response(200, json={
                "name": "Power Curve",
                "type": "power",
                "data": [
                    {"secs": 5, "watts": 800},
                    {"secs": 1200, "watts": 280, "date": "2025-10-12"},
                ],
            })
        )
        result = await get_power_curves(ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert "ftp_analysis" in parsed["data"]
        assert parsed["data"]["ftp_analysis"]["estimated_ftp"] == int(280 * 0.95)
