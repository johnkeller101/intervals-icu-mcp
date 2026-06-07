"""Additional tests for event_management to improve coverage."""

import json

from intervals_icu_mcp.client import ICUAPIError
from intervals_icu_mcp.tools.event_management import (
    _diagnose_event_error,
    _normalize_category,
    _normalize_event_type,
)


class TestDiagnoseEventError:
    def test_wrong_field_names(self):
        """Test diagnosis of wrong field names."""
        err = ICUAPIError(
            "Bad Request", status_code=400, response_text="error",
            request_payload={"start_date": "2025-01-01", "duration": 3600}
        )
        result = _diagnose_event_error(err)
        parsed = json.loads(result)
        assert "error" in parsed
        assert any("start_date_local" in s for s in parsed["error"]["suggestions"])

    def test_unknown_field(self):
        """Test diagnosis of unknown field."""
        err = ICUAPIError(
            "Bad Request", status_code=400, response_text="error",
            request_payload={"unknown_field": "value", "start_date_local": "2025-01-01",
                             "name": "test", "category": "WORKOUT"}
        )
        result = _diagnose_event_error(err)
        parsed = json.loads(result)
        assert any("Unknown field" in s for s in parsed["error"]["suggestions"])

    def test_invalid_category_alias(self):
        """Test diagnosis of invalid category with alias suggestion."""
        err = ICUAPIError(
            "Bad Request", status_code=400, response_text="error",
            request_payload={"category": "RACE", "start_date_local": "2025-01-01", "name": "test"}
        )
        result = _diagnose_event_error(err)
        parsed = json.loads(result)
        assert any("RACE_A" in s for s in parsed["error"]["suggestions"])

    def test_invalid_category_unknown(self):
        """Test diagnosis of completely invalid category."""
        err = ICUAPIError(
            "Bad Request", status_code=400, response_text="error",
            request_payload={"category": "BADCAT", "start_date_local": "2025-01-01", "name": "test"}
        )
        result = _diagnose_event_error(err)
        parsed = json.loads(result)
        assert any("not valid" in s for s in parsed["error"]["suggestions"])

    def test_invalid_date_format(self):
        """Test diagnosis of invalid date."""
        err = ICUAPIError(
            "Bad Request", status_code=400, response_text="error",
            request_payload={"start_date_local": "Jan 15 2025", "name": "test", "category": "WORKOUT"}
        )
        result = _diagnose_event_error(err)
        parsed = json.loads(result)
        assert any("invalid format" in s.lower() for s in parsed["error"]["suggestions"])

    def test_missing_start_date_with_start_date(self):
        """Test when start_date is used instead of start_date_local."""
        err = ICUAPIError(
            "Bad Request", status_code=400, response_text="error",
            request_payload={"start_date": "2025-01-01", "name": "test", "category": "WORKOUT"}
        )
        result = _diagnose_event_error(err)
        parsed = json.loads(result)
        # Should have suggestion about start_date_local
        suggestions = parsed["error"]["suggestions"]
        assert any("start_date_local" in s for s in suggestions)

    def test_missing_required_fields(self):
        """Test when required fields are missing."""
        err = ICUAPIError(
            "Bad Request", status_code=400, response_text="error",
            request_payload={"start_date_local": "2025-01-01"}
        )
        result = _diagnose_event_error(err)
        parsed = json.loads(result)
        suggestions = parsed["error"]["suggestions"]
        assert any("name" in s.lower() for s in suggestions)
        assert any("category" in s.lower() for s in suggestions)

    def test_invalid_type(self):
        """Test diagnosis of invalid activity type."""
        err = ICUAPIError(
            "Bad Request", status_code=400, response_text="error",
            request_payload={
                "start_date_local": "2025-01-01", "name": "test",
                "category": "WORKOUT", "type": "Bicycle"
            }
        )
        result = _diagnose_event_error(err)
        parsed = json.loads(result)
        assert any("type" in s.lower() for s in parsed["error"]["suggestions"])

    def test_invalid_moving_time_type(self):
        """Test diagnosis of wrong moving_time type."""
        err = ICUAPIError(
            "Bad Request", status_code=400, response_text="error",
            request_payload={
                "start_date_local": "2025-01-01", "name": "test",
                "category": "WORKOUT", "moving_time": "1 hour"
            }
        )
        result = _diagnose_event_error(err)
        parsed = json.loads(result)
        assert any("moving_time" in s for s in parsed["error"]["suggestions"])

    def test_invalid_distance_type(self):
        """Test diagnosis of wrong distance type."""
        err = ICUAPIError(
            "Bad Request", status_code=400, response_text="error",
            request_payload={
                "start_date_local": "2025-01-01", "name": "test",
                "category": "WORKOUT", "distance": "40km"
            }
        )
        result = _diagnose_event_error(err)
        parsed = json.loads(result)
        assert any("distance" in s for s in parsed["error"]["suggestions"])

    def test_invalid_workout_doc_not_dict(self):
        """Test diagnosis of wrong workout_doc type."""
        err = ICUAPIError(
            "Bad Request", status_code=400, response_text="error",
            request_payload={
                "start_date_local": "2025-01-01", "name": "test",
                "category": "WORKOUT", "workout_doc": "just a string"
            }
        )
        result = _diagnose_event_error(err)
        parsed = json.loads(result)
        assert any("workout_doc" in s for s in parsed["error"]["suggestions"])

    def test_workout_doc_missing_description(self):
        """Test workout_doc dict without required subfields."""
        err = ICUAPIError(
            "Bad Request", status_code=400, response_text="error",
            request_payload={
                "start_date_local": "2025-01-01", "name": "test",
                "category": "WORKOUT", "workout_doc": {"something": "else"}
            }
        )
        result = _diagnose_event_error(err)
        parsed = json.loads(result)
        assert any("workout_doc" in s for s in parsed["error"]["suggestions"])

    def test_no_specific_issues(self):
        """Test fallback when no specific issues detected."""
        err = ICUAPIError(
            "Bad Request", status_code=400, response_text="server error",
            request_payload={
                "start_date_local": "2025-01-01", "name": "test",
                "category": "WORKOUT", "type": "Ride"
            }
        )
        result = _diagnose_event_error(err)
        parsed = json.loads(result)
        assert "error" in parsed

    def test_missing_start_date_entirely(self):
        """Test when start_date_local is completely missing."""
        err = ICUAPIError(
            "Bad Request", status_code=400, response_text="error",
            request_payload={"name": "test", "category": "WORKOUT"}
        )
        result = _diagnose_event_error(err)
        parsed = json.loads(result)
        assert any("start_date_local" in s for s in parsed["error"]["suggestions"])

    def test_close_type_match(self):
        """Test diagnosis when type is close to a valid one."""
        err = ICUAPIError(
            "Bad Request", status_code=400, response_text="error",
            request_payload={
                "start_date_local": "2025-01-01", "name": "test",
                "category": "WORKOUT", "type": "virtual"
            }
        )
        result = _diagnose_event_error(err)
        parsed = json.loads(result)
        # Should find close matches like VirtualRide, VirtualRun
        assert any("type" in s.lower() or "Did you mean" in s for s in parsed["error"]["suggestions"])


class TestNormalizeEventTypeEdgeCases:
    def test_partial_match_single(self):
        """Test partial match that resolves to single type."""
        # "Snowboard" contains "Snowboard" exactly
        result = _normalize_event_type("Snowboard")
        assert result == "Snowboard"

    def test_ambiguous_partial_match(self):
        """Test ambiguous partial match raises ValueError."""
        import pytest
        with pytest.raises(ValueError, match="Ambiguous"):
            _normalize_event_type("Virtual")


class TestNormalizeCategoryEdgeCases:
    def test_injury_alias(self):
        assert _normalize_category("INJURY") == "INJURED"

    def test_ftp_alias(self):
        assert _normalize_category("FTP") == "SET_EFTP"
