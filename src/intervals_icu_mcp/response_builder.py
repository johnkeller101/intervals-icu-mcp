"""Response builder utilities for structured JSON output.

This module provides utilities for building consistent, structured JSON responses
across all MCP tools. All tools return JSON with a standard structure:

{
    "data": {...},           # Main data payload
    "analysis": {...},       # Optional insights and computed metrics
    "metadata": {...}        # Query metadata, timestamps, includes
}
"""

import json
import re
from datetime import date, datetime
from typing import Any, cast

# Keys whose string values should be enriched with day-of-week
_DATE_KEYS = frozenset({
    "date",
    "start_date",
    "end_date",
    "start_date_local",
    "end_date_local",
    "oldest",
    "newest",
    "snoozed_until",
    "dob",
    "fetched_at",
})

# Matches YYYY-MM-DD with optional time component
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")


def _add_day_of_week(value: str) -> str:
    """Append day-of-week to an ISO date/datetime string.

    '2025-01-15' -> '2025-01-15 (Wednesday)'
    '2025-01-15T14:30:00' -> '2025-01-15T14:30:00 (Wednesday)'
    """
    match = _ISO_DATE_RE.match(value)
    if not match:
        return value
    try:
        parsed = datetime.strptime(match.group(), "%Y-%m-%d")
        return f"{value} ({parsed.strftime('%A')})"
    except ValueError:
        return value


def _convert_datetimes(obj: Any, _key: str | None = None) -> Any:  # type: ignore[misc]
    """Recursively convert datetime/date objects and enrich date strings with day-of-week."""
    if isinstance(obj, datetime):
        iso = obj.isoformat()
        return f"{iso} ({obj.strftime('%A')})"
    elif isinstance(obj, date):
        iso = obj.isoformat()
        return f"{iso} ({obj.strftime('%A')})"
    elif isinstance(obj, dict):
        return {str(k): _convert_datetimes(v, _key=str(k)) for k, v in obj.items()}  # type: ignore[misc]
    elif isinstance(obj, list):
        return [_convert_datetimes(item, _key=_key) for item in obj]  # type: ignore[misc]
    elif isinstance(obj, str) and _key and _key in _DATE_KEYS and _ISO_DATE_RE.match(obj):
        return _add_day_of_week(obj)
    return obj


class ResponseBuilder:
    """Builder for standardized JSON responses."""

    @staticmethod
    def format_date_with_day(dt: datetime | str | None) -> dict[str, str] | None:
        """Format a date/datetime with explicit day-of-week information.

        Args:
            dt: datetime object or ISO string or None

        Returns:
            Dict with datetime, date, day_of_week, and formatted string, or None if input is None
        """
        if dt is None:
            return None

        # Parse the datetime if it's a string, otherwise use it directly
        if isinstance(dt, str):
            parsed_dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        else:
            parsed_dt = dt

        return {
            "datetime": dt if isinstance(dt, str) else dt.isoformat(),
            "date": parsed_dt.strftime("%Y-%m-%d"),
            "day_of_week": parsed_dt.strftime("%A"),  # e.g., "Monday"
            "formatted": parsed_dt.strftime(
                "%A, %B %d, %Y at %I:%M %p"
            ),  # e.g., "Monday, October 15, 2025 at 02:30 PM"
        }

    @staticmethod
    def build_response(
        data: dict[str, Any],
        analysis: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        query_type: str | None = None,
    ) -> str:
        """Build standardized JSON response.

        Args:
            data: Main data payload
            analysis: Optional analysis and insights
            metadata: Optional metadata (will be enriched with timestamp)
            query_type: Optional query type for metadata

        Returns:
            JSON string with structure:
            {
                "data": {...},
                "analysis": {...},
                "metadata": {
                    "fetched_at": "ISO timestamp",
                    "query_type": "...",
                    ...
                }
            }
        """
        # Convert datetime objects to ISO strings
        converted_data = cast(dict[str, Any], _convert_datetimes(data))
        converted_analysis: dict[str, Any] | None = None
        if analysis:
            converted_analysis = cast(dict[str, Any], _convert_datetimes(analysis))

        response: dict[str, Any] = {"data": converted_data}

        if converted_analysis:
            response["analysis"] = converted_analysis

        # Build metadata with timestamp
        meta = metadata or {}
        converted_meta = cast(dict[str, Any], _convert_datetimes(meta))
        now = datetime.now()
        converted_meta["fetched_at"] = f"{now.isoformat()} ({now.strftime('%A')})"
        if query_type:
            converted_meta["query_type"] = query_type

        response["metadata"] = converted_meta

        return json.dumps(response, separators=(",", ":"))

    @staticmethod
    def build_error_response(
        error_message: str,
        error_type: str = "error",
        suggestions: list[str] | None = None,
    ) -> str:
        """Build standardized error response.

        Args:
            error_message: Human-readable error message
            error_type: Type of error (e.g., "not_found", "rate_limit", "validation")
            suggestions: Optional list of suggestions to resolve the error

        Returns:
            JSON string with error structure
        """
        response: dict[str, dict[str, str | list[str]]] = {
            "error": {
                "message": error_message,
                "type": error_type,
                "timestamp": f"{datetime.now().isoformat()} ({datetime.now().strftime('%A')})",
            }
        }

        if suggestions:
            response["error"]["suggestions"] = suggestions

        return json.dumps(response, separators=(",", ":"))
