"""Event/calendar management tools for Intervals.icu MCP server."""

from datetime import datetime
from typing import Annotated, Any

from fastmcp import Context

from ..auth import ICUConfig
from ..client import ICUAPIError, ICUClient
from ..response_builder import ResponseBuilder


def parse_start_date_local(date_str: str) -> str:
    """Parse a date or datetime string and return ISO format for Intervals.icu API.

    Accepts:
        - YYYY-MM-DD (date only, defaults to midnight)
        - YYYY-MM-DDTHH:MM:SS (full datetime)
        - YYYY-MM-DDTHH:MM (datetime without seconds)

    Returns:
        ISO format string like "2025-12-08T15:00:00"
    """
    if "T" in date_str:
        for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M"]:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%Y-%m-%dT%H:%M:%S")
            except ValueError:
                continue

    try:
        dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
        return dt.strftime("%Y-%m-%dT%H:%M:%S")
    except ValueError:
        pass

    raise ValueError(f"Invalid date format: {date_str}. Use YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS")


VALID_CATEGORIES = [
    "WORKOUT", "RACE_A", "RACE_B", "RACE_C", "NOTE", "PLAN",
    "HOLIDAY", "SICK", "INJURED", "SET_EFTP", "FITNESS_DAYS",
    "SEASON_START", "TARGET", "SET_FITNESS",
]

# Auto-correct common category mistakes to valid API values
_CATEGORY_ALIASES = {
    "RACE": "RACE_A",
    "GOAL": "TARGET",
    "REST": "HOLIDAY",
    "INJURY": "INJURED",
    "FTP": "SET_EFTP",
}

# Valid sport/activity types accepted by the API
_VALID_TYPES = [
    "Ride", "Run", "Swim", "WeightTraining", "Hike", "Walk",
    "AlpineSki", "BackcountrySki", "Canoeing", "Crossfit",
    "EBikeRide", "Elliptical", "Golf", "GravelRide",
    "Handcycle", "IceSkate", "InlineSkate", "Kayaking",
    "Kitesurf", "MountainBikeRide", "NordicSki", "RockClimbing",
    "RollerSki", "Rowing", "Snowboard", "Snowshoe",
    "StairStepper", "StandUpPaddling", "Surfing",
    "TrailRun", "VirtualRide", "VirtualRun", "Wheelchair",
    "Windsurf", "Workout", "Yoga", "Other",
]

# Known API field names for events (to detect typos/wrong names)
_VALID_EVENT_FIELDS = {
    "start_date_local", "end_date_local", "name", "category", "type",
    "description", "moving_time", "distance", "icu_training_load",
    "indoor", "color", "external_id", "tags", "workout_doc",
    "athlete_cannot_edit", "hide_from_athlete", "target",
    "carbs_per_hour", "sub_type", "not_on_fitness_chart",
}

# Common field name mistakes → correct field name
_FIELD_ALIASES = {
    "start_date": "start_date_local",
    "date": "start_date_local",
    "duration": "moving_time",
    "duration_seconds": "moving_time",
    "time": "moving_time",
    "load": "icu_training_load",
    "training_load": "icu_training_load",
    "tss": "icu_training_load",
    "sport_type": "type",
    "activity_type": "type",
    "event_type": "type",
    "workout_type": "type",
    "distance_meters": "distance",
    "title": "name",
}


def _normalize_category(category: str) -> str:
    """Normalize an event category, auto-correcting common mistakes.

    Returns the corrected category if it's a known alias, or the
    uppercased original if already valid. Raises ValueError if unknown.
    """
    upper = category.upper()
    # Auto-correct known aliases
    if upper in _CATEGORY_ALIASES:
        return _CATEGORY_ALIASES[upper]
    # Already valid
    if upper in VALID_CATEGORIES:
        return upper
    # Unknown category
    raise ValueError(
        f"Invalid category '{category}'. "
        f"Must be one of: {', '.join(VALID_CATEGORIES)}. "
        f"Common aliases: RACE→RACE_A, GOAL→TARGET, REST→HOLIDAY, "
        f"INJURY→INJURED, FTP→SET_EFTP."
    )


def _normalize_event_type(event_type: str) -> str:
    """Normalize an activity/sport type, auto-correcting case mismatches.

    Returns the correctly-cased type if found. Raises ValueError if unknown.
    """
    # Build a case-insensitive lookup
    type_lookup = {t.lower(): t for t in _VALID_TYPES}
    lower = event_type.lower()
    if lower in type_lookup:
        return type_lookup[lower]
    # Try partial match
    matches = [t for t in _VALID_TYPES if lower in t.lower() or t.lower() in lower]
    if len(matches) == 1:
        return matches[0]
    if matches:
        raise ValueError(
            f"Ambiguous activity type '{event_type}'. "
            f"Did you mean one of: {', '.join(matches)}?"
        )
    raise ValueError(
        f"Unknown activity type '{event_type}'. "
        f"Valid types: Ride, Run, Swim, VirtualRide, GravelRide, "
        f"TrailRun, WeightTraining, Hike, Walk, Yoga, Other. "
        f"Use exact casing (e.g., 'Ride' not 'ride')."
    )


def _diagnose_event_error(error: ICUAPIError) -> str:
    """Analyze a 400 API error and return actionable suggestions for the agent.

    Inspects the request payload to identify common mistakes and returns
    specific guidance on how to fix them.
    """
    suggestions: list[str] = []
    payload = error.request_payload or {}

    if not isinstance(payload, dict):
        return ResponseBuilder.build_error_response(
            "The event payload must be a JSON object (dict), not a "
            f"{type(payload).__name__}. Build a dict with keys like "
            "'start_date_local', 'name', 'category', 'type', etc.",
            error_type="validation_error",
            suggestions=[
                "Payload must be a JSON object with string keys.",
                "Required keys: start_date_local, name, category.",
                "Example: {\"start_date_local\": \"2026-03-01\", "
                "\"name\": \"Easy Ride\", \"category\": \"WORKOUT\", "
                "\"type\": \"Ride\"}",
            ],
        )

    # Check for wrong field names
    for key in list(payload.keys()):
        if key in _FIELD_ALIASES:
            correct = _FIELD_ALIASES[key]
            suggestions.append(
                f"Field '{key}' is not a valid API field. "
                f"Use '{correct}' instead."
            )
        elif key not in _VALID_EVENT_FIELDS:
            suggestions.append(
                f"Unknown field '{key}'. Valid fields: "
                f"{', '.join(sorted(_VALID_EVENT_FIELDS))}."
            )

    # Check category
    cat = payload.get("category", "")
    if cat and isinstance(cat, str):
        upper_cat = cat.upper()
        if upper_cat not in VALID_CATEGORIES:
            if upper_cat in _CATEGORY_ALIASES:
                suggestions.append(
                    f"Category '{cat}' is invalid. "
                    f"Use '{_CATEGORY_ALIASES[upper_cat]}' instead."
                )
            else:
                suggestions.append(
                    f"Category '{cat}' is not valid. "
                    f"Must be one of: {', '.join(VALID_CATEGORIES)}. "
                    f"Common mappings: RACE→RACE_A, GOAL→TARGET, "
                    f"REST→HOLIDAY, INJURY→INJURED, FTP→SET_EFTP."
                )

    # Check date format
    date_val = payload.get("start_date_local", "")
    if date_val and isinstance(date_val, str):
        valid_date = False
        for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d"]:
            try:
                datetime.strptime(date_val, fmt)
                valid_date = True
                break
            except ValueError:
                continue
        if not valid_date:
            suggestions.append(
                f"Date '{date_val}' has invalid format. "
                f"Use YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS. "
                f"Example: '2026-03-01' or '2026-03-01T14:00:00'."
            )
    elif "start_date" in payload and "start_date_local" not in payload:
        suggestions.append(
            "Missing 'start_date_local'. The API requires 'start_date_local', "
            "not 'start_date'. Rename the field."
        )
    elif "start_date_local" not in payload:
        suggestions.append(
            "Missing required field 'start_date_local'. "
            "Every event needs a date in YYYY-MM-DD format."
        )

    # Check type (sport type)
    type_val = payload.get("type", "")
    if type_val and isinstance(type_val, str):
        if type_val not in _VALID_TYPES:
            # Find close matches
            lower_type = type_val.lower()
            close = [t for t in _VALID_TYPES if lower_type in t.lower() or t.lower() in lower_type]
            if close:
                suggestions.append(
                    f"Activity type '{type_val}' may not be valid. "
                    f"Did you mean: {', '.join(close)}?"
                )
            else:
                suggestions.append(
                    f"Activity type '{type_val}' is not recognized. "
                    f"Common types: Ride, Run, Swim, VirtualRide, "
                    f"GravelRide, TrailRun, WeightTraining, Hike."
                )

    # Check moving_time is a number
    mt = payload.get("moving_time")
    if mt is not None and not isinstance(mt, (int, float)):
        suggestions.append(
            f"'moving_time' must be an integer (seconds), got {type(mt).__name__}. "
            f"Examples: 3600=1h, 5400=1.5h, 7200=2h."
        )

    # Check distance is a number
    dist = payload.get("distance")
    if dist is not None and not isinstance(dist, (int, float)):
        suggestions.append(
            f"'distance' must be a number (meters), got {type(dist).__name__}. "
            f"Examples: 40000=40km, 100000=100km."
        )

    # Check workout_doc structure
    wd = payload.get("workout_doc")
    if wd is not None:
        if not isinstance(wd, dict):
            suggestions.append(
                "'workout_doc' must be a JSON object. "
                "Example: {\"description\": \"Warmup\\n- 10m ramp 45-55%\", \"steps\": []}"
            )
        elif "description" not in wd and "steps" not in wd:
            suggestions.append(
                "'workout_doc' should contain 'description' (text format) and/or 'steps' (array). "
                "For text-based workouts, use: "
                "{\"description\": \"workout text here\", \"steps\": []}"
            )

    # Check for missing required fields
    if "name" not in payload:
        suggestions.append("Missing required field 'name'. Every event needs a name.")
    if "category" not in payload:
        suggestions.append(
            "Missing required field 'category'. "
            "Use WORKOUT for training, NOTE for notes, RACE_A for races, etc."
        )

    # If no specific issues found, provide general guidance
    if not suggestions:
        suggestions = [
            "The Intervals.icu API rejected this request. Check that all field "
            "names and values match the expected format.",
            f"Required fields: start_date_local (YYYY-MM-DD), name (string), "
            f"category ({', '.join(VALID_CATEGORIES[:5])}...).",
            "Optional fields: type (Ride/Run/Swim), moving_time (seconds), "
            "distance (meters), description (string), workout_doc (object).",
            f"API response: {error.response_text or error.message}",
        ]

    error_msg = (
        f"Intervals.icu API rejected the event creation request. "
        f"Found {len(suggestions)} issue(s) to fix."
    )

    return ResponseBuilder.build_error_response(
        error_msg,
        error_type="api_validation_error",
        suggestions=suggestions,
    )


async def create_event(
    start_date: Annotated[
        str,
        "Start date/time. Accepts YYYY-MM-DD (defaults to midnight), "
        "YYYY-MM-DDTHH:MM:SS, or YYYY-MM-DDTHH:MM",
    ],
    name: Annotated[str, "Event name"],
    category: Annotated[
        str,
        "Event category: WORKOUT, NOTE, RACE_A, RACE_B, RACE_C, TARGET, "
        "PLAN, HOLIDAY, SICK, INJURED, SET_EFTP, FITNESS_DAYS, SEASON_START, SET_FITNESS",
    ],
    description: Annotated[str | None, "Event description (optional)"] = None,
    event_type: Annotated[str | None, "Activity type (e.g., Ride, Run, Swim)"] = None,
    duration_seconds: Annotated[int | None, "Planned duration in seconds"] = None,
    distance_meters: Annotated[float | None, "Planned distance in meters"] = None,
    training_load: Annotated[int | None, "Planned training load"] = None,
    ctx: Context | None = None,
) -> str:
    """Create a new calendar event (planned workout, note, race, or goal).

    Adds an event to your Intervals.icu calendar. Events can be workouts with
    planned metrics, notes for tracking information, races, or training goals.

    Args:
        start_date: Date/time string. Accepts YYYY-MM-DD (defaults to midnight),
            YYYY-MM-DDTHH:MM:SS (specific time), or YYYY-MM-DDTHH:MM
        name: Name of the event
        category: Type of event - WORKOUT, NOTE, RACE_A, RACE_B, RACE_C, TARGET, etc.
        description: Optional detailed description
        event_type: Activity type (e.g., "Ride", "Run", "Swim") for workouts
        duration_seconds: Planned duration for workouts
        distance_meters: Planned distance for workouts
        training_load: Planned training load for workouts

    Returns:
        JSON string with created event data
    """
    assert ctx is not None
    config: ICUConfig = ctx.get_state("config")

    # Validate and normalize category (auto-corrects RACE→RACE_A, GOAL→TARGET, etc.)
    try:
        normalized_category = _normalize_category(category)
    except ValueError as e:
        return ResponseBuilder.build_error_response(
            str(e),
            error_type="validation_error",
        )

    # Validate and normalize event type (auto-corrects casing)
    normalized_type = None
    if event_type:
        try:
            normalized_type = _normalize_event_type(event_type)
        except ValueError as e:
            return ResponseBuilder.build_error_response(
                str(e),
                error_type="validation_error",
            )

    # Validate and parse date format
    try:
        start_date_local = parse_start_date_local(start_date)
    except ValueError as e:
        return ResponseBuilder.build_error_response(
            str(e),
            error_type="validation_error",
        )

    try:
        # Build event data
        event_data: dict[str, Any] = {
            "start_date_local": start_date_local,
            "name": name,
            "category": normalized_category,
        }

        if description:
            event_data["description"] = description
        if normalized_type:
            event_data["type"] = normalized_type
        if duration_seconds:
            event_data["moving_time"] = duration_seconds
        if distance_meters:
            event_data["distance"] = distance_meters
        if training_load:
            event_data["icu_training_load"] = training_load

        async with ICUClient(config) as client:
            event = await client.create_event(event_data)

            event_result: dict[str, Any] = {
                "id": event.id,
                "start_date": event.start_date_local,
                "name": event.name,
                "category": event.category,
            }

            if event.description:
                event_result["description"] = event.description
            if event.type:
                event_result["type"] = event.type
            if event.moving_time:
                event_result["duration_seconds"] = event.moving_time
            if event.distance:
                event_result["distance_meters"] = event.distance
            if event.icu_training_load:
                event_result["training_load"] = event.icu_training_load

            return ResponseBuilder.build_response(
                data=event_result,
                query_type="create_event",
                metadata={"message": f"Successfully created {category.lower()}: {name}"},
            )

    except ICUAPIError as e:
        if e.status_code == 400:
            return _diagnose_event_error(e)
        return ResponseBuilder.build_error_response(e.message, error_type="api_error")
    except Exception as e:
        return ResponseBuilder.build_error_response(
            f"Unexpected error: {str(e)}", error_type="internal_error"
        )


async def update_event(
    event_id: Annotated[int, "Event ID to update"],
    name: Annotated[str | None, "Updated event name"] = None,
    description: Annotated[str | None, "Updated description"] = None,
    start_date: Annotated[
        str | None,
        "Updated start date/time. Accepts YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS, or YYYY-MM-DDTHH:MM",
    ] = None,
    event_type: Annotated[str | None, "Updated activity type"] = None,
    duration_seconds: Annotated[int | None, "Updated duration in seconds"] = None,
    distance_meters: Annotated[float | None, "Updated distance in meters"] = None,
    training_load: Annotated[int | None, "Updated training load"] = None,
    ctx: Context | None = None,
) -> str:
    """Update an existing calendar event.

    Modifies one or more fields of an existing event. Only provide the fields
    you want to change - other fields will remain unchanged.

    Args:
        event_id: ID of the event to update
        name: New name for the event
        description: New description
        start_date: New start date/time. Accepts YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS, or YYYY-MM-DDTHH:MM
        event_type: New activity type
        duration_seconds: New planned duration
        distance_meters: New planned distance
        training_load: New planned training load

    Returns:
        JSON string with updated event data
    """
    assert ctx is not None
    config: ICUConfig = ctx.get_state("config")

    # Validate and parse date format if provided
    start_date_local = None
    if start_date:
        try:
            start_date_local = parse_start_date_local(start_date)
        except ValueError as e:
            return ResponseBuilder.build_error_response(
                str(e),
                error_type="validation_error",
            )

    try:
        # Build update data (only include provided fields)
        event_data: dict[str, Any] = {}

        if name is not None:
            event_data["name"] = name
        if description is not None:
            event_data["description"] = description
        if start_date_local is not None:
            event_data["start_date_local"] = start_date_local
        if event_type is not None:
            event_data["type"] = event_type
        if duration_seconds is not None:
            event_data["moving_time"] = duration_seconds
        if distance_meters is not None:
            event_data["distance"] = distance_meters
        if training_load is not None:
            event_data["icu_training_load"] = training_load

        if not event_data:
            return ResponseBuilder.build_error_response(
                "No fields provided to update. Please specify at least one field to change.",
                error_type="validation_error",
            )

        async with ICUClient(config) as client:
            event = await client.update_event(event_id, event_data)

            event_result: dict[str, Any] = {
                "id": event.id,
                "start_date": event.start_date_local,
                "name": event.name,
                "category": event.category,
            }

            if event.description:
                event_result["description"] = event.description
            if event.type:
                event_result["type"] = event.type
            if event.moving_time:
                event_result["duration_seconds"] = event.moving_time
            if event.distance:
                event_result["distance_meters"] = event.distance
            if event.icu_training_load:
                event_result["training_load"] = event.icu_training_load

            return ResponseBuilder.build_response(
                data=event_result,
                query_type="update_event",
                metadata={"message": f"Successfully updated event {event_id}"},
            )

    except ICUAPIError as e:
        if e.status_code == 400:
            return _diagnose_event_error(e)
        return ResponseBuilder.build_error_response(e.message, error_type="api_error")
    except Exception as e:
        return ResponseBuilder.build_error_response(
            f"Unexpected error: {str(e)}", error_type="internal_error"
        )


async def delete_event(
    event_id: Annotated[int, "Event ID to delete"],
    ctx: Context | None = None,
) -> str:
    """Delete a calendar event.

    Permanently removes an event from your calendar. This action cannot be undone.

    Args:
        event_id: ID of the event to delete

    Returns:
        JSON string with deletion confirmation
    """
    assert ctx is not None
    config: ICUConfig = ctx.get_state("config")

    try:
        async with ICUClient(config) as client:
            success = await client.delete_event(event_id)

            if success:
                return ResponseBuilder.build_response(
                    data={"event_id": event_id, "deleted": True},
                    query_type="delete_event",
                    metadata={"message": f"Successfully deleted event {event_id}"},
                )
            else:
                return ResponseBuilder.build_error_response(
                    f"Failed to delete event {event_id}",
                    error_type="api_error",
                )

    except ICUAPIError as e:
        if e.status_code == 400:
            return _diagnose_event_error(e)
        return ResponseBuilder.build_error_response(e.message, error_type="api_error")
    except Exception as e:
        return ResponseBuilder.build_error_response(
            f"Unexpected error: {str(e)}", error_type="internal_error"
        )


async def bulk_create_events(
    events: Annotated[
        str,
        "JSON string containing array of events. Each event should have: start_date_local, name, category, and optional fields like description, type, moving_time, distance, icu_training_load",
    ],
    ctx: Context | None = None,
) -> str:
    """Create multiple calendar events in a single operation.

    This is more efficient than creating events one at a time. Provide a JSON array
    of event objects, each with the same structure as create_event.

    Args:
        events: JSON array of event objects to create

    Returns:
        JSON string with created events
    """
    assert ctx is not None
    config: ICUConfig = ctx.get_state("config")

    try:
        import json

        # Parse the JSON string
        try:
            parsed_data = json.loads(events)
        except json.JSONDecodeError as e:
            return ResponseBuilder.build_error_response(
                f"Invalid JSON format: {str(e)}", error_type="validation_error"
            )

        if not isinstance(parsed_data, list):
            return ResponseBuilder.build_error_response(
                "Events must be a JSON array", error_type="validation_error"
            )

        # Type cast after validation
        events_data: list[dict[str, Any]] = parsed_data  # type: ignore[assignment]

        # Validate each event
        for i, event_data in enumerate(events_data):
            if "start_date_local" not in event_data:
                return ResponseBuilder.build_error_response(
                    f"Event {i}: Missing required field 'start_date_local'",
                    error_type="validation_error",
                )
            if "name" not in event_data:
                return ResponseBuilder.build_error_response(
                    f"Event {i}: Missing required field 'name'", error_type="validation_error"
                )
            if "category" not in event_data:
                return ResponseBuilder.build_error_response(
                    f"Event {i}: Missing required field 'category'",
                    error_type="validation_error",
                )
            try:
                event_data["category"] = _normalize_category(event_data["category"])
            except ValueError as e:
                return ResponseBuilder.build_error_response(
                    f"Event {i}: {e}",
                    error_type="validation_error",
                )

            # Auto-correct common field name mistakes
            for wrong_name, correct_name in _FIELD_ALIASES.items():
                if wrong_name in event_data and correct_name not in event_data:
                    event_data[correct_name] = event_data.pop(wrong_name)

            # Validate and normalize event type
            if "type" in event_data:
                try:
                    event_data["type"] = _normalize_event_type(event_data["type"])
                except ValueError as e:
                    return ResponseBuilder.build_error_response(
                        f"Event {i}: {e}",
                        error_type="validation_error",
                    )

            # Validate date format
            try:
                datetime.strptime(event_data["start_date_local"], "%Y-%m-%d")
            except ValueError:
                return ResponseBuilder.build_error_response(
                    f"Event {i}: Invalid date format '{event_data['start_date_local']}'. "
                    f"Use YYYY-MM-DD format (e.g., '2026-03-01').",
                    error_type="validation_error",
                )

        async with ICUClient(config) as client:
            created_events = await client.bulk_create_events(events_data)

            events_result: list[dict[str, Any]] = []
            for event in created_events:
                event_info: dict[str, Any] = {
                    "id": event.id,
                    "start_date": event.start_date_local,
                    "name": event.name,
                    "category": event.category,
                }

                if event.description:
                    event_info["description"] = event.description
                if event.type:
                    event_info["type"] = event.type
                if event.moving_time:
                    event_info["duration_seconds"] = event.moving_time
                if event.distance:
                    event_info["distance_meters"] = event.distance
                if event.icu_training_load:
                    event_info["training_load"] = event.icu_training_load

                events_result.append(event_info)

            return ResponseBuilder.build_response(
                data={"events": events_result},
                query_type="bulk_create_events",
                metadata={
                    "message": f"Successfully created {len(created_events)} events",
                    "count": len(created_events),
                },
            )

    except ICUAPIError as e:
        if e.status_code == 400:
            return _diagnose_event_error(e)
        return ResponseBuilder.build_error_response(e.message, error_type="api_error")
    except Exception as e:
        return ResponseBuilder.build_error_response(
            f"Unexpected error: {str(e)}", error_type="internal_error"
        )


async def bulk_delete_events(
    event_ids: Annotated[str, "JSON array of event IDs to delete (e.g., '[123, 456, 789]')"],
    ctx: Context | None = None,
) -> str:
    """Delete multiple calendar events in a single operation.

    This is more efficient than deleting events one at a time. Provide a JSON array
    of event IDs to delete.

    Args:
        event_ids: JSON array of event IDs (integers)

    Returns:
        JSON string with deletion confirmation
    """
    assert ctx is not None
    config: ICUConfig = ctx.get_state("config")

    try:
        import json

        # Parse the JSON string
        try:
            parsed_data = json.loads(event_ids)
        except json.JSONDecodeError as e:
            return ResponseBuilder.build_error_response(
                f"Invalid JSON format: {str(e)}", error_type="validation_error"
            )

        if not isinstance(parsed_data, list):
            return ResponseBuilder.build_error_response(
                "Event IDs must be a JSON array", error_type="validation_error"
            )

        if not parsed_data:
            return ResponseBuilder.build_error_response(
                "Must provide at least one event ID to delete", error_type="validation_error"
            )

        # Type cast after validation
        ids_list: list[int] = parsed_data  # type: ignore[assignment]

        async with ICUClient(config) as client:
            result = await client.bulk_delete_events(ids_list)

            return ResponseBuilder.build_response(
                data={"deleted_count": len(ids_list), "event_ids": ids_list, "result": result},
                query_type="bulk_delete_events",
                metadata={"message": f"Successfully deleted {len(ids_list)} events"},
            )

    except ICUAPIError as e:
        if e.status_code == 400:
            return _diagnose_event_error(e)
        return ResponseBuilder.build_error_response(e.message, error_type="api_error")
    except Exception as e:
        return ResponseBuilder.build_error_response(
            f"Unexpected error: {str(e)}", error_type="internal_error"
        )


async def mark_event_done(
    event_id: Annotated[int, "Event ID to mark as done"],
    ctx: Context | None = None,
) -> str:
    """Mark a planned workout/event as done by creating a matching manual activity.

    This converts an incomplete event (showing red/0%) to completed (green/100%).
    The event must exist and be in the past or present.

    Args:
        event_id: The Intervals.icu event ID to mark as done

    Returns:
        JSON string with confirmation and created activity data
    """
    assert ctx is not None
    config: ICUConfig = ctx.get_state("config")

    try:
        async with ICUClient(config) as client:
            result = await client.mark_event_done(event_id)

            return ResponseBuilder.build_response(
                data=result,
                query_type="mark_event_done",
                metadata={"message": f"Successfully marked event {event_id} as done"},
            )

    except ICUAPIError as e:
        if e.status_code == 400:
            return _diagnose_event_error(e)
        return ResponseBuilder.build_error_response(e.message, error_type="api_error")
    except Exception as e:
        return ResponseBuilder.build_error_response(
            f"Unexpected error: {str(e)}", error_type="internal_error"
        )


async def duplicate_event(
    event_id: Annotated[int, "Event ID to duplicate"],
    new_date: Annotated[str, "New date for the duplicated event (YYYY-MM-DD format)"],
    ctx: Context | None = None,
) -> str:
    """Duplicate an existing event to a new date.

    Creates a copy of an event with all its properties (name, type, duration, etc.)
    but with a new date. Useful for repeating workouts or events.

    Args:
        event_id: ID of the event to duplicate
        new_date: New date in YYYY-MM-DD format

    Returns:
        JSON string with the duplicated event
    """
    assert ctx is not None
    config: ICUConfig = ctx.get_state("config")

    # Validate date format
    try:
        datetime.strptime(new_date, "%Y-%m-%d")
    except ValueError:
        return ResponseBuilder.build_error_response(
            "Invalid date format. Please use YYYY-MM-DD format.",
            error_type="validation_error",
        )

    try:
        async with ICUClient(config) as client:
            duplicated_event = await client.duplicate_event(event_id, new_date)

            event_result: dict[str, Any] = {
                "id": duplicated_event.id,
                "start_date": duplicated_event.start_date_local,
                "name": duplicated_event.name,
                "category": duplicated_event.category,
                "original_event_id": event_id,
            }

            if duplicated_event.description:
                event_result["description"] = duplicated_event.description
            if duplicated_event.type:
                event_result["type"] = duplicated_event.type
            if duplicated_event.moving_time:
                event_result["duration_seconds"] = duplicated_event.moving_time
            if duplicated_event.distance:
                event_result["distance_meters"] = duplicated_event.distance
            if duplicated_event.icu_training_load:
                event_result["training_load"] = duplicated_event.icu_training_load

            return ResponseBuilder.build_response(
                data=event_result,
                query_type="duplicate_event",
                metadata={
                    "message": f"Successfully duplicated event {event_id} to {new_date}",
                    "original_event_id": event_id,
                },
            )

    except ICUAPIError as e:
        if e.status_code == 400:
            return _diagnose_event_error(e)
        return ResponseBuilder.build_error_response(e.message, error_type="api_error")
    except Exception as e:
        return ResponseBuilder.build_error_response(
            f"Unexpected error: {str(e)}", error_type="internal_error"
        )
