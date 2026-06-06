"""Additional tests for athlete tools to improve coverage."""

import json
from unittest.mock import AsyncMock, MagicMock

from httpx import Response

from intervals_icu_mcp.tools.athlete import get_athlete_profile, get_fitness_summary


def _mock_ctx(mock_config):
    ctx = MagicMock()
    ctx.get_state = AsyncMock(return_value=mock_config)
    return ctx


class TestGetAthleteProfileEdgeCases:
    async def test_with_sport_settings_pace(self, mock_config, respx_mock):
        """Test profile with pace threshold in sport settings."""
        data = {
            "id": "i123456",
            "name": "Test Athlete",
            "email": "test@example.com",
            "weight": 70.0,
            "sex": "M",
            "dob": "1990-01-15",
            "ctl": 50.0,
            "atl": 35.0,
            "tsb": -5.0,
            "ramp_rate": 3.0,
            "sport_settings": [
                {"id": 1, "type": "Ride", "ftp": 250, "fthr": 165},
                {"id": 2, "type": "Run", "pace_threshold": 4.5, "fthr": 170},
                {"id": 3, "type": "Swim", "swim_threshold": 1.8},
            ],
        }
        respx_mock.get("/athlete/i123456").mock(
            return_value=Response(200, json=data)
        )
        result = await get_athlete_profile(ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert len(parsed["data"]["sports"]) == 3
        assert parsed["analysis"]["form_status"] == "optimal"
        assert parsed["analysis"]["ramp_rate_status"] == "good"

    async def test_very_fresh_tsb(self, mock_config, respx_mock):
        """Test with very high TSB (very fresh)."""
        data = {
            "id": "i123456",
            "name": "Fresh Athlete",
            "ctl": 50.0,
            "atl": 20.0,
            "tsb": 30.0,
            "ramp_rate": -2.0,
            "sport_settings": [],
        }
        respx_mock.get("/athlete/i123456").mock(
            return_value=Response(200, json=data)
        )
        result = await get_athlete_profile(ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["analysis"]["form_status"] == "very_fresh"
        assert parsed["analysis"]["ramp_rate_status"] == "declining"

    async def test_recovered_tsb(self, mock_config, respx_mock):
        """Test with recovered TSB."""
        data = {
            "id": "i123456",
            "name": "Recovered",
            "ctl": 50.0,
            "atl": 40.0,
            "tsb": 10.0,
            "ramp_rate": 6.0,
            "sport_settings": [],
        }
        respx_mock.get("/athlete/i123456").mock(
            return_value=Response(200, json=data)
        )
        result = await get_athlete_profile(ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["analysis"]["form_status"] == "recovered"
        assert parsed["analysis"]["ramp_rate_status"] == "caution"

    async def test_very_fatigued(self, mock_config, respx_mock):
        """Test very fatigued status."""
        data = {
            "id": "i123456",
            "name": "Tired",
            "ctl": 80.0,
            "atl": 120.0,
            "tsb": -40.0,
            "ramp_rate": -6.0,
            "sport_settings": [],
        }
        respx_mock.get("/athlete/i123456").mock(
            return_value=Response(200, json=data)
        )
        result = await get_athlete_profile(ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["analysis"]["form_status"] == "very_fatigued"
        assert parsed["analysis"]["ramp_rate_status"] == "declining_significantly"

    async def test_fatigued(self, mock_config, respx_mock):
        """Test fatigued status."""
        data = {
            "id": "i123456",
            "name": "Tired",
            "ctl": 60.0,
            "atl": 80.0,
            "tsb": -20.0,
            "ramp_rate": 9.0,
            "sport_settings": [],
        }
        respx_mock.get("/athlete/i123456").mock(
            return_value=Response(200, json=data)
        )
        result = await get_athlete_profile(ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["analysis"]["form_status"] == "fatigued"
        assert parsed["analysis"]["ramp_rate_status"] == "high_risk"

    async def test_api_error(self, mock_config, respx_mock):
        """Test API error handling."""
        respx_mock.get("/athlete/i123456").mock(return_value=Response(401))
        result = await get_athlete_profile(ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert "error" in parsed
        assert "suggestions" in parsed["error"]

    async def test_unexpected_error(self, mock_config, respx_mock):
        """Test unexpected error handling."""
        respx_mock.get("/athlete/i123456").mock(side_effect=RuntimeError("connection"))
        result = await get_athlete_profile(ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert "error" in parsed
        assert parsed["error"]["type"] == "internal_error"


class TestGetFitnessSummaryEdgeCases:
    async def test_no_fitness_data(self, mock_config, respx_mock):
        """Test when no fitness data available."""
        data = {
            "id": "i123456",
            "name": "New Athlete",
            "sport_settings": [],
        }
        respx_mock.get("/athlete/i123456").mock(
            return_value=Response(200, json=data)
        )
        result = await get_fitness_summary(ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert "error" in parsed

    async def test_very_fatigued_recommendations(self, mock_config, respx_mock):
        """Test recommendations when very fatigued."""
        data = {
            "id": "i123456",
            "name": "Test",
            "ctl": 80.0,
            "atl": 120.0,
            "tsb": -40.0,
            "ramp_rate": -6.0,
            "sport_settings": [],
        }
        respx_mock.get("/athlete/i123456").mock(
            return_value=Response(200, json=data)
        )
        result = await get_fitness_summary(ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["analysis"]["form_status"] == "very_fatigued"
        assert "recommendations" in parsed["analysis"]

    async def test_fatigued_with_high_ramp(self, mock_config, respx_mock):
        """Test fatigued with high ramp rate."""
        data = {
            "id": "i123456",
            "name": "Test",
            "ctl": 60.0,
            "atl": 80.0,
            "tsb": -20.0,
            "ramp_rate": 6.0,
            "sport_settings": [],
        }
        respx_mock.get("/athlete/i123456").mock(
            return_value=Response(200, json=data)
        )
        result = await get_fitness_summary(ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["analysis"]["form_status"] == "fatigued"

    async def test_recovered_declining(self, mock_config, respx_mock):
        """Test recovered with declining ramp rate."""
        data = {
            "id": "i123456",
            "name": "Test",
            "ctl": 50.0,
            "atl": 40.0,
            "tsb": 10.0,
            "ramp_rate": -2.0,
            "sport_settings": [],
        }
        respx_mock.get("/athlete/i123456").mock(
            return_value=Response(200, json=data)
        )
        result = await get_fitness_summary(ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["analysis"]["form_status"] == "recovered"
        assert "recommendations" in parsed["analysis"]

    async def test_fresh_positive_ramp(self, mock_config, respx_mock):
        """Test fresh with positive ramp rate."""
        data = {
            "id": "i123456",
            "name": "Test",
            "ctl": 50.0,
            "atl": 40.0,
            "tsb": 10.0,
            "ramp_rate": 3.0,
            "sport_settings": [],
        }
        respx_mock.get("/athlete/i123456").mock(
            return_value=Response(200, json=data)
        )
        result = await get_fitness_summary(ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["analysis"]["ramp_rate_status"] == "good"

    async def test_optimal_zone(self, mock_config, respx_mock):
        """Test optimal training zone."""
        data = {
            "id": "i123456",
            "name": "Test",
            "ctl": 60.0,
            "atl": 65.0,
            "tsb": -5.0,
            "ramp_rate": 3.0,
            "sport_settings": [],
        }
        respx_mock.get("/athlete/i123456").mock(
            return_value=Response(200, json=data)
        )
        result = await get_fitness_summary(ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["analysis"]["form_status"] == "optimal"

    async def test_api_error(self, mock_config, respx_mock):
        """Test API error."""
        respx_mock.get("/athlete/i123456").mock(return_value=Response(401))
        result = await get_fitness_summary(ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert "error" in parsed

    async def test_declining_significantly_ramp(self, mock_config, respx_mock):
        """Test declining significantly ramp rate."""
        data = {
            "id": "i123456",
            "name": "Test",
            "ctl": 50.0,
            "atl": 20.0,
            "tsb": 30.0,
            "ramp_rate": -8.0,
            "sport_settings": [],
        }
        respx_mock.get("/athlete/i123456").mock(
            return_value=Response(200, json=data)
        )
        result = await get_fitness_summary(ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["analysis"]["ramp_rate_status"] == "declining_significantly"
