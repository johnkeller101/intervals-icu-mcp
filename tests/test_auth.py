"""Tests for auth module."""

from intervals_icu_mcp.auth import ICUConfig, validate_credentials


class TestICUConfig:
    """Tests for ICUConfig."""

    def test_config_creation(self):
        """Test creating config with values."""
        config = ICUConfig(
            intervals_icu_api_key="test_key",
            intervals_icu_athlete_id="i999",
        )
        assert config.intervals_icu_api_key == "test_key"
        assert config.intervals_icu_athlete_id == "i999"

    def test_config_defaults(self):
        """Test config default values."""
        config = ICUConfig()
        assert config.intervals_icu_api_key == ""
        assert config.intervals_icu_athlete_id == ""


class TestValidateCredentials:
    """Tests for validate_credentials."""

    def test_valid_credentials(self):
        """Test with valid credentials."""
        config = ICUConfig(
            intervals_icu_api_key="real_key_abc123",
            intervals_icu_athlete_id="i999999",
        )
        assert validate_credentials(config) is True

    def test_empty_api_key(self):
        """Test with empty API key."""
        config = ICUConfig(
            intervals_icu_api_key="",
            intervals_icu_athlete_id="i999999",
        )
        assert validate_credentials(config) is False

    def test_placeholder_api_key(self):
        """Test with placeholder API key."""
        config = ICUConfig(
            intervals_icu_api_key="your_api_key_here",
            intervals_icu_athlete_id="i999999",
        )
        assert validate_credentials(config) is False

    def test_placeholder_athlete_id(self):
        """Test with placeholder athlete ID."""
        config = ICUConfig(
            intervals_icu_api_key="real_key",
            intervals_icu_athlete_id="i123456",
        )
        assert validate_credentials(config) is False

    def test_empty_athlete_id(self):
        """Test with empty athlete ID."""
        config = ICUConfig(
            intervals_icu_api_key="real_key",
            intervals_icu_athlete_id="",
        )
        assert validate_credentials(config) is False
