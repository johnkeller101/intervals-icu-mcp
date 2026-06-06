"""Tests for formatters module."""

from datetime import datetime

from intervals_icu_mcp.formatters import (
    calculate_avg,
    format_cadence,
    format_date,
    format_date_relative,
    format_distance,
    format_duration,
    format_elevation,
    format_heart_rate,
    format_intensity,
    format_pace,
    format_power,
    format_speed,
    format_training_load,
    format_tsb,
    format_weight,
    format_wellness_value,
    interpret_fitness_trends,
)


class TestFormatDuration:
    def test_hours_minutes_seconds(self):
        assert format_duration(3661) == "1h 1m 1s"

    def test_minutes_only(self):
        assert format_duration(120) == "2m"

    def test_seconds_only(self):
        assert format_duration(45) == "45s"

    def test_zero(self):
        assert format_duration(0) == "0s"

    def test_none(self):
        assert format_duration(None) == "0s"

    def test_negative(self):
        assert format_duration(-1) == "0s"


class TestFormatDistance:
    def test_metric(self):
        assert format_distance(50000.0) == "50.00 km"

    def test_imperial(self):
        result = format_distance(1609.344, unit="imperial")
        assert "1.00 mi" in result

    def test_none(self):
        assert format_distance(None) == "N/A"


class TestFormatElevation:
    def test_metric(self):
        assert format_elevation(500.0) == "500 m"

    def test_imperial(self):
        result = format_elevation(100.0, unit="imperial")
        assert "ft" in result

    def test_none(self):
        assert format_elevation(None) == "N/A"


class TestFormatSpeed:
    def test_metric(self):
        result = format_speed(10.0)
        assert "km/h" in result

    def test_imperial(self):
        result = format_speed(10.0, unit="imperial")
        assert "mph" in result

    def test_none(self):
        assert format_speed(None) == "N/A"


class TestFormatPace:
    def test_metric(self):
        result = format_pace(4.0)  # 4 m/s = 4:10/km
        assert "/km" in result

    def test_imperial(self):
        result = format_pace(4.0, unit="imperial")
        assert "/mi" in result

    def test_none(self):
        assert format_pace(None) == "N/A"

    def test_zero(self):
        assert format_pace(0) == "N/A"


class TestFormatDate:
    def test_datetime_object(self):
        dt = datetime(2025, 1, 15, 14, 30)
        assert format_date(dt) == "2025-01-15"

    def test_datetime_with_time(self):
        dt = datetime(2025, 1, 15, 14, 30)
        assert format_date(dt, include_time=True) == "2025-01-15 14:30"

    def test_string_input(self):
        result = format_date("2025-01-15T14:30:00")
        assert result == "2025-01-15"

    def test_none(self):
        assert format_date(None) == "N/A"

    def test_invalid_string(self):
        result = format_date("not a date")
        assert result == "not a date"


class TestFormatDateRelative:
    def test_none(self):
        assert format_date_relative(None) == "N/A"

    def test_today(self):
        result = format_date_relative(datetime.now())
        assert result == "Today"

    def test_invalid_string(self):
        result = format_date_relative("bad date")
        assert result == "bad date"


class TestFormatPower:
    def test_value(self):
        assert format_power(250) == "250 W"

    def test_none(self):
        assert format_power(None) == "N/A"


class TestFormatHeartRate:
    def test_value(self):
        assert format_heart_rate(145) == "145 bpm"

    def test_none(self):
        assert format_heart_rate(None) == "N/A"


class TestFormatCadence:
    def test_cycling(self):
        result = format_cadence(90.0, "Ride")
        assert "rpm" in result

    def test_running(self):
        result = format_cadence(180.0, "Run")
        assert "spm" in result

    def test_none(self):
        assert format_cadence(None) == "N/A"


class TestFormatTrainingLoad:
    def test_value(self):
        assert format_training_load(120) == "120"

    def test_none(self):
        assert format_training_load(None) == "N/A"


class TestFormatIntensity:
    def test_value(self):
        assert format_intensity(0.85) == "0.85"

    def test_none(self):
        assert format_intensity(None) == "N/A"


class TestFormatTsb:
    def test_fresh(self):
        result = format_tsb(25.0)
        assert "Fresh" in result

    def test_recovered(self):
        result = format_tsb(10.0)
        assert "Recovered" in result

    def test_optimal(self):
        result = format_tsb(0.0)
        assert "Optimal" in result

    def test_fatigued(self):
        result = format_tsb(-20.0)
        assert "Fatigued" in result

    def test_very_fatigued(self):
        result = format_tsb(-35.0)
        assert "Very Fatigued" in result

    def test_none(self):
        assert format_tsb(None) == "N/A"


class TestFormatWellnessValue:
    def test_high_value(self):
        result = format_wellness_value(9, 10)
        assert "9/10" in result

    def test_none(self):
        assert format_wellness_value(None) == "N/A"


class TestCalculateAvg:
    def test_values(self):
        assert calculate_avg([10, 20, 30]) == 20.0

    def test_empty(self):
        assert calculate_avg([]) == 0.0


class TestFormatWeight:
    def test_metric(self):
        assert format_weight(70.0) == "70.0 kg"

    def test_imperial(self):
        result = format_weight(70.0, unit="imperial")
        assert "lbs" in result

    def test_none(self):
        assert format_weight(None) == "N/A"


class TestInterpretFitnessTrends:
    def test_high_ramp(self):
        result = interpret_fitness_trends(50.0, 35.0, 9.0)
        assert "high" in result.lower() or "Risk" in result

    def test_moderate_ramp(self):
        result = interpret_fitness_trends(50.0, 35.0, 6.0)
        assert "moderate" in result.lower() or "Monitor" in result

    def test_declining(self):
        result = interpret_fitness_trends(50.0, 35.0, -6.0)
        assert "declining" in result.lower()

    def test_sustainable(self):
        result = interpret_fitness_trends(50.0, 35.0, 3.0)
        assert "Sustainable" in result

    def test_no_data(self):
        result = interpret_fitness_trends(None, None, None)
        assert "No fitness data" in result
