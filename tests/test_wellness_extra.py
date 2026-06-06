"""Additional tests for wellness tools to improve coverage."""

import json
from unittest.mock import AsyncMock, MagicMock

from httpx import Response

from intervals_icu_mcp.tools.wellness import get_wellness_for_date, update_wellness


def _mock_ctx(mock_config):
    ctx = MagicMock()
    ctx.get_state = AsyncMock(return_value=mock_config)
    return ctx


class TestGetWellnessForDateFullMetrics:
    async def test_all_metrics(self, mock_config, respx_mock):
        """Test wellness with all possible metric fields."""
        full_data = {
            "id": "2025-10-13",
            "weight": 70.0,
            "restingHR": 48,
            "hrv": 65.5,
            "hrvSDNN": 75.2,
            "sleepSecs": 28800,
            "sleepQuality": 8,
            "sleepScore": 85.0,
            "avgSleepingHR": 50.0,
            "fatigue": 3,
            "soreness": 2,
            "stress": 2,
            "mood": 8,
            "motivation": 9,
            "injury": 0,
            "readiness": 85.0,
            "bodyFat": 12.5,
            "systolic": 120,
            "diastolic": 80,
            "spo2": 98.5,
            "respiration": 14.0,
            "steps": 8000,
            "kcalConsumed": 2500,
            "hydrationVolume": 3.0,
            "baevskySI": 45.0,
            "bloodGlucose": 5.2,
            "lactate": 1.1,
            "menstrualPhase": "luteal",
            "ctl": 50.0,
            "atl": 35.0,
            "tsb": 15.0,
            "rampRate": 3.0,
            "comments": "Feeling great today",
        }
        respx_mock.get("/athlete/i123456/wellness/2025-10-13").mock(
            return_value=Response(200, json=full_data)
        )
        result = await get_wellness_for_date(date="2025-10-13", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert "sleep" in parsed["data"]
        assert "heart" in parsed["data"]
        assert "subjective" in parsed["data"]
        assert "body" in parsed["data"]
        assert "vitals" in parsed["data"]
        assert "activity_nutrition" in parsed["data"]
        assert "training" in parsed["data"]
        assert "other" in parsed["data"]
        assert parsed["data"]["comments"] == "Feeling great today"


class TestUpdateWellnessFullFields:
    async def test_all_fields(self, mock_config, respx_mock):
        """Test updating all wellness fields."""
        return_data = {
            "id": "2025-10-13",
            "weight": 70.0,
            "restingHR": 48,
            "hrv": 65.5,
            "sleepSecs": 28800,
            "sleepQuality": 8,
            "fatigue": 3,
            "soreness": 2,
            "stress": 2,
            "mood": 8,
            "motivation": 9,
            "readiness": 85.0,
            "comments": "Updated",
        }
        respx_mock.put("/athlete/i123456/wellness").mock(
            return_value=Response(200, json=return_data)
        )
        result = await update_wellness(
            date="2025-10-13",
            weight=70.0,
            resting_hr=48,
            hrv=65.5,
            sleep_secs=28800,
            sleep_quality=8,
            fatigue=3,
            soreness=2,
            stress=2,
            mood=8,
            motivation=9,
            readiness=85.0,
            comments="Updated",
            ctx=_mock_ctx(mock_config),
        )
        parsed = json.loads(result)
        assert parsed["data"]["weight_kg"] == 70.0
        assert parsed["data"]["resting_hr"] == 48
        assert parsed["data"]["fatigue"] == 3
        assert parsed["data"]["comments"] == "Updated"

    async def test_unexpected_error(self, mock_config, respx_mock):
        """Test unexpected error."""
        respx_mock.put("/athlete/i123456/wellness").mock(
            side_effect=RuntimeError("connection lost")
        )
        result = await update_wellness(
            date="2025-10-13", weight=70.0, ctx=_mock_ctx(mock_config)
        )
        parsed = json.loads(result)
        assert "error" in parsed
