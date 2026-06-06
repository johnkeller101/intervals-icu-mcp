"""Tests for response_builder module."""

import json
from datetime import date, datetime

from intervals_icu_mcp.response_builder import ResponseBuilder, _add_day_of_week, _convert_datetimes


class TestAddDayOfWeek:
    """Tests for _add_day_of_week helper."""

    def test_date_only(self):
        """Test adding day of week to date-only string."""
        result = _add_day_of_week("2025-01-15")
        assert "Wednesday" in result
        assert result.startswith("2025-01-15")

    def test_datetime_string(self):
        """Test adding day of week to datetime string."""
        result = _add_day_of_week("2025-01-15T14:30:00")
        assert "Wednesday" in result

    def test_invalid_string(self):
        """Test with non-date string."""
        result = _add_day_of_week("not a date")
        assert result == "not a date"


class TestConvertDatetimes:
    """Tests for _convert_datetimes helper."""

    def test_datetime_object(self):
        """Test converting datetime object."""
        dt = datetime(2025, 1, 15, 14, 30)
        result = _convert_datetimes(dt)
        assert "2025-01-15" in result
        assert "Wednesday" in result

    def test_date_object(self):
        """Test converting date object."""
        d = date(2025, 1, 15)
        result = _convert_datetimes(d)
        assert "2025-01-15" in result
        assert "Wednesday" in result

    def test_dict_recursion(self):
        """Test recursive dict conversion."""
        data = {"start_date": "2025-01-15", "name": "Test"}
        result = _convert_datetimes(data)
        assert "Wednesday" in result["start_date"]
        assert result["name"] == "Test"

    def test_list_recursion(self):
        """Test recursive list conversion."""
        data = [datetime(2025, 1, 15)]
        result = _convert_datetimes(data)
        assert "Wednesday" in result[0]

    def test_non_date_key_string(self):
        """Test that non-date-key strings are not modified."""
        data = {"name": "2025-01-15"}
        result = _convert_datetimes(data)
        assert result["name"] == "2025-01-15"

    def test_passthrough_values(self):
        """Test that non-date values pass through."""
        assert _convert_datetimes(42) == 42
        assert _convert_datetimes(None) is None
        assert _convert_datetimes(True) is True


class TestResponseBuilder:
    """Tests for ResponseBuilder."""

    def test_build_response_basic(self):
        """Test basic response building."""
        result = ResponseBuilder.build_response(
            data={"key": "value"},
            query_type="test",
        )
        parsed = json.loads(result)
        assert parsed["data"]["key"] == "value"
        assert "metadata" in parsed
        assert parsed["metadata"]["query_type"] == "test"
        assert "fetched_at" in parsed["metadata"]

    def test_build_response_with_analysis(self):
        """Test response with analysis section."""
        result = ResponseBuilder.build_response(
            data={"key": "value"},
            analysis={"insight": "good"},
        )
        parsed = json.loads(result)
        assert parsed["analysis"]["insight"] == "good"

    def test_build_response_no_analysis(self):
        """Test response without analysis section."""
        result = ResponseBuilder.build_response(data={"key": "value"})
        parsed = json.loads(result)
        assert "analysis" not in parsed

    def test_build_response_with_metadata(self):
        """Test response with custom metadata."""
        result = ResponseBuilder.build_response(
            data={"key": "value"},
            metadata={"custom": "meta"},
        )
        parsed = json.loads(result)
        assert parsed["metadata"]["custom"] == "meta"
        assert "fetched_at" in parsed["metadata"]

    def test_build_error_response(self):
        """Test error response building."""
        result = ResponseBuilder.build_error_response(
            "Something went wrong",
            error_type="api_error",
        )
        parsed = json.loads(result)
        assert parsed["error"]["message"] == "Something went wrong"
        assert parsed["error"]["type"] == "api_error"
        assert "timestamp" in parsed["error"]

    def test_build_error_response_with_suggestions(self):
        """Test error response with suggestions."""
        result = ResponseBuilder.build_error_response(
            "Error occurred",
            suggestions=["Try this", "Or that"],
        )
        parsed = json.loads(result)
        assert parsed["error"]["suggestions"] == ["Try this", "Or that"]

    def test_format_date_with_day_datetime(self):
        """Test format_date_with_day with datetime."""
        result = ResponseBuilder.format_date_with_day(datetime(2025, 1, 15, 14, 30))
        assert result is not None
        assert result["date"] == "2025-01-15"
        assert result["day_of_week"] == "Wednesday"

    def test_format_date_with_day_string(self):
        """Test format_date_with_day with string."""
        result = ResponseBuilder.format_date_with_day("2025-01-15T14:30:00")
        assert result is not None
        assert result["date"] == "2025-01-15"
        assert result["day_of_week"] == "Wednesday"

    def test_format_date_with_day_none(self):
        """Test format_date_with_day with None."""
        assert ResponseBuilder.format_date_with_day(None) is None
