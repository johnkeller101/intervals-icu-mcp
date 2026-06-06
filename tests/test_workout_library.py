"""Tests for workout_library tools."""

import json
from unittest.mock import AsyncMock, MagicMock

from httpx import Response

from intervals_icu_mcp.tools.workout_library import get_workout_library, get_workouts_in_folder


def _mock_ctx(mock_config):
    ctx = MagicMock()
    ctx.get_state = AsyncMock(return_value=mock_config)
    return ctx


class TestGetWorkoutLibrary:
    async def test_success(self, mock_config, respx_mock):
        respx_mock.get("/athlete/i123456/folders").mock(
            return_value=Response(200, json=[
                {
                    "id": 1,
                    "name": "My Workouts",
                    "num_workouts": 10,
                    "description": "Custom workouts",
                },
                {
                    "id": 2,
                    "name": "Training Plan",
                    "num_workouts": 20,
                    "duration_weeks": 12,
                    "hours_per_week_min": 8,
                    "hours_per_week_max": 12,
                },
            ])
        )
        result = await get_workout_library(ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert len(parsed["data"]["folders"]) == 2
        assert parsed["data"]["summary"]["training_plans"] == 1
        assert parsed["data"]["summary"]["regular_folders"] == 1

    async def test_empty(self, mock_config, respx_mock):
        respx_mock.get("/athlete/i123456/folders").mock(
            return_value=Response(200, json=[])
        )
        result = await get_workout_library(ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["data"]["count"] == 0

    async def test_api_error(self, mock_config, respx_mock):
        respx_mock.get("/athlete/i123456/folders").mock(return_value=Response(401))
        result = await get_workout_library(ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert "error" in parsed


class TestGetWorkoutsInFolder:
    async def test_success(self, mock_config, respx_mock):
        respx_mock.get("/athlete/i123456/folders/1/workouts").mock(
            return_value=Response(200, json=[
                {
                    "id": 101,
                    "name": "Threshold Intervals",
                    "type": "Ride",
                    "moving_time": 3600,
                    "icu_training_load": 80,
                    "icu_intensity": 0.85,
                    "indoor": True,
                },
                {
                    "id": 102,
                    "name": "Endurance Ride",
                    "type": "Ride",
                    "moving_time": 7200,
                    "icu_training_load": 60,
                    "indoor": False,
                },
            ])
        )
        result = await get_workouts_in_folder(folder_id=1, ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert len(parsed["data"]["workouts"]) == 2
        assert parsed["data"]["summary"]["total_workouts"] == 2
        assert parsed["data"]["summary"]["indoor_workouts"] == 1

    async def test_empty(self, mock_config, respx_mock):
        respx_mock.get("/athlete/i123456/folders/1/workouts").mock(
            return_value=Response(200, json=[])
        )
        result = await get_workouts_in_folder(folder_id=1, ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["data"]["count"] == 0

    async def test_api_error(self, mock_config, respx_mock):
        respx_mock.get("/athlete/i123456/folders/1/workouts").mock(
            return_value=Response(401)
        )
        result = await get_workouts_in_folder(folder_id=1, ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert "error" in parsed
