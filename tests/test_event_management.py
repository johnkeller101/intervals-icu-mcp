"""Tests for event_management tools."""

import json
from unittest.mock import AsyncMock, MagicMock

from httpx import Response

from intervals_icu_mcp.tools.event_management import (
    _normalize_category,
    _normalize_event_type,
    bulk_create_events,
    bulk_delete_events,
    create_event,
    delete_event,
    duplicate_event,
    mark_event_done,
    parse_start_date_local,
    update_event,
)


def _mock_ctx(mock_config):
    ctx = MagicMock()
    ctx.get_state = AsyncMock(return_value=mock_config)
    return ctx


class TestParseStartDateLocal:
    def test_date_only(self):
        result = parse_start_date_local("2025-12-08")
        assert result == "2025-12-08T00:00:00"

    def test_datetime_with_seconds(self):
        result = parse_start_date_local("2025-12-08T15:30:00")
        assert result == "2025-12-08T15:30:00"

    def test_datetime_without_seconds(self):
        result = parse_start_date_local("2025-12-08T15:30")
        assert result == "2025-12-08T15:30:00"

    def test_invalid_format(self):
        import pytest
        with pytest.raises(ValueError, match="Invalid date format"):
            parse_start_date_local("not-a-date")


class TestNormalizeCategory:
    def test_valid_category(self):
        assert _normalize_category("WORKOUT") == "WORKOUT"

    def test_alias_race(self):
        assert _normalize_category("RACE") == "RACE_A"

    def test_alias_goal(self):
        assert _normalize_category("GOAL") == "TARGET"

    def test_alias_rest(self):
        assert _normalize_category("REST") == "HOLIDAY"

    def test_case_insensitive(self):
        assert _normalize_category("workout") == "WORKOUT"

    def test_invalid_category(self):
        import pytest
        with pytest.raises(ValueError, match="Invalid category"):
            _normalize_category("INVALID_CAT")


class TestNormalizeEventType:
    def test_valid_type(self):
        assert _normalize_event_type("Ride") == "Ride"

    def test_case_insensitive(self):
        assert _normalize_event_type("ride") == "Ride"

    def test_invalid_type(self):
        import pytest
        with pytest.raises(ValueError, match="Unknown activity type"):
            _normalize_event_type("Skydiving")


class TestCreateEvent:
    async def test_success(self, mock_config, respx_mock):
        respx_mock.post("/athlete/i123456/events").mock(
            return_value=Response(200, json={
                "id": 2001,
                "start_date_local": "2025-12-08T00:00:00",
                "name": "Test Workout",
                "category": "WORKOUT",
                "type": "Ride",
                "moving_time": 3600,
            })
        )
        result = await create_event(
            start_date="2025-12-08",
            name="Test Workout",
            category="WORKOUT",
            event_type="Ride",
            duration_seconds=3600,
            ctx=_mock_ctx(mock_config),
        )
        parsed = json.loads(result)
        assert parsed["data"]["id"] == 2001
        assert parsed["data"]["name"] == "Test Workout"

    async def test_invalid_category(self, mock_config, respx_mock):
        result = await create_event(
            start_date="2025-12-08",
            name="Test",
            category="INVALID",
            ctx=_mock_ctx(mock_config),
        )
        parsed = json.loads(result)
        assert "error" in parsed

    async def test_invalid_date(self, mock_config, respx_mock):
        result = await create_event(
            start_date="bad-date",
            name="Test",
            category="WORKOUT",
            ctx=_mock_ctx(mock_config),
        )
        parsed = json.loads(result)
        assert "error" in parsed

    async def test_category_alias(self, mock_config, respx_mock):
        respx_mock.post("/athlete/i123456/events").mock(
            return_value=Response(200, json={
                "id": 2002,
                "start_date_local": "2025-12-08T00:00:00",
                "name": "Race Day",
                "category": "RACE_A",
            })
        )
        result = await create_event(
            start_date="2025-12-08",
            name="Race Day",
            category="RACE",
            ctx=_mock_ctx(mock_config),
        )
        parsed = json.loads(result)
        assert parsed["data"]["id"] == 2002

    async def test_api_error_400(self, mock_config, respx_mock):
        respx_mock.post("/athlete/i123456/events").mock(
            return_value=Response(400, text="Bad request")
        )
        result = await create_event(
            start_date="2025-12-08",
            name="Test",
            category="WORKOUT",
            ctx=_mock_ctx(mock_config),
        )
        parsed = json.loads(result)
        assert "error" in parsed


class TestUpdateEvent:
    async def test_success(self, mock_config, respx_mock):
        respx_mock.put("/athlete/i123456/events/1001").mock(
            return_value=Response(200, json={
                "id": 1001,
                "start_date_local": "2025-12-08",
                "name": "Updated Name",
                "category": "WORKOUT",
            })
        )
        result = await update_event(
            event_id=1001, name="Updated Name", ctx=_mock_ctx(mock_config)
        )
        parsed = json.loads(result)
        assert parsed["data"]["name"] == "Updated Name"

    async def test_no_fields(self, mock_config, respx_mock):
        result = await update_event(event_id=1001, ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert "error" in parsed

    async def test_invalid_date(self, mock_config, respx_mock):
        result = await update_event(
            event_id=1001, start_date="bad", ctx=_mock_ctx(mock_config)
        )
        parsed = json.loads(result)
        assert "error" in parsed


class TestDeleteEvent:
    async def test_success(self, mock_config, respx_mock):
        respx_mock.delete("/athlete/i123456/events/1001").mock(
            return_value=Response(200)
        )
        result = await delete_event(event_id=1001, ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["data"]["deleted"] is True

    async def test_api_error(self, mock_config, respx_mock):
        respx_mock.delete("/athlete/i123456/events/9999").mock(
            return_value=Response(404)
        )
        result = await delete_event(event_id=9999, ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert "error" in parsed


class TestBulkCreateEvents:
    async def test_success(self, mock_config, respx_mock):
        respx_mock.post("/athlete/i123456/events/bulk").mock(
            return_value=Response(200, json=[
                {"id": 3001, "start_date_local": "2025-12-08", "name": "W1", "category": "WORKOUT"},
                {"id": 3002, "start_date_local": "2025-12-09", "name": "W2", "category": "WORKOUT"},
            ])
        )
        events_json = json.dumps([
            {"start_date_local": "2025-12-08", "name": "W1", "category": "WORKOUT"},
            {"start_date_local": "2025-12-09", "name": "W2", "category": "WORKOUT"},
        ])
        result = await bulk_create_events(events=events_json, ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert len(parsed["data"]["events"]) == 2

    async def test_invalid_json(self, mock_config, respx_mock):
        result = await bulk_create_events(events="not json", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert "error" in parsed

    async def test_not_array(self, mock_config, respx_mock):
        result = await bulk_create_events(events='{"key": "value"}', ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert "error" in parsed

    async def test_missing_required_field(self, mock_config, respx_mock):
        events_json = json.dumps([{"name": "W1", "category": "WORKOUT"}])
        result = await bulk_create_events(events=events_json, ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert "error" in parsed


class TestBulkDeleteEvents:
    async def test_success(self, mock_config, respx_mock):
        respx_mock.delete("/athlete/i123456/events/bulk").mock(
            return_value=Response(200, json={"deleted": 2})
        )
        result = await bulk_delete_events(event_ids="[1001, 1002]", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert parsed["data"]["deleted_count"] == 2

    async def test_invalid_json(self, mock_config, respx_mock):
        result = await bulk_delete_events(event_ids="not json", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert "error" in parsed

    async def test_empty_list(self, mock_config, respx_mock):
        result = await bulk_delete_events(event_ids="[]", ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert "error" in parsed


class TestMarkEventDone:
    async def test_success(self, mock_config, respx_mock):
        respx_mock.post("/athlete/i123456/events/1001/mark-done").mock(
            return_value=Response(200, json={"status": "done"})
        )
        result = await mark_event_done(event_id=1001, ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert "data" in parsed

    async def test_api_error(self, mock_config, respx_mock):
        respx_mock.post("/athlete/i123456/events/9999/mark-done").mock(
            return_value=Response(404)
        )
        result = await mark_event_done(event_id=9999, ctx=_mock_ctx(mock_config))
        parsed = json.loads(result)
        assert "error" in parsed


class TestDuplicateEvent:
    async def test_success(self, mock_config, respx_mock):
        respx_mock.post("/athlete/i123456/events/1001/duplicate").mock(
            return_value=Response(200, json={
                "id": 4001,
                "start_date_local": "2025-12-15",
                "name": "Threshold Intervals",
                "category": "WORKOUT",
            })
        )
        result = await duplicate_event(
            event_id=1001, new_date="2025-12-15", ctx=_mock_ctx(mock_config)
        )
        parsed = json.loads(result)
        assert parsed["data"]["id"] == 4001
        assert parsed["data"]["original_event_id"] == 1001

    async def test_invalid_date(self, mock_config, respx_mock):
        result = await duplicate_event(
            event_id=1001, new_date="bad-date", ctx=_mock_ctx(mock_config)
        )
        parsed = json.loads(result)
        assert "error" in parsed
