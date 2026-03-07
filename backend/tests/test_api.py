"""Tests for the API layer - focused on ConfigUpdateRequest validation."""

import pytest
from pydantic import ValidationError

from backend.api.routes import ConfigUpdateRequest


class TestConfigUpdateRequest:
    """Test cases for ConfigUpdateRequest validation."""

    def test_valid_config_all_fields(self):
        """Test valid configuration with all fields provided."""
        # Arrange & Act
        config = ConfigUpdateRequest(tick_speed=5, spawn_rate=0.3, phase_duration=5)

        # Assert
        assert config.tick_speed == 5
        assert config.spawn_rate == 0.3
        assert config.phase_duration == 5

    def test_valid_config_partial_fields(self):
        """Test valid configuration with only some fields provided."""
        # Arrange & Act
        config = ConfigUpdateRequest(tick_speed=8)

        # Assert
        assert config.tick_speed == 8
        assert config.spawn_rate is None
        assert config.phase_duration is None

    def test_valid_config_empty(self):
        """Test valid configuration with no fields provided."""
        # Arrange & Act
        config = ConfigUpdateRequest()

        # Assert
        assert config.tick_speed is None
        assert config.spawn_rate is None
        assert config.phase_duration is None

    @pytest.mark.parametrize(
        "field_name,test_values",
        [
            ("tick_speed", [1, 5, 10]),
            ("spawn_rate", [0.0, 0.5, 1.0]),
            ("phase_duration", [1, 10, 20]),
        ],
    )
    def test_valid_boundary_values(self, field_name, test_values):
        """Test valid boundary and mid-range values for all configuration fields."""
        for value in test_values:
            # Arrange & Act
            config = ConfigUpdateRequest(**{field_name: value})

            # Assert
            assert getattr(config, field_name) == value

    @pytest.mark.parametrize(
        "field_name,invalid_values",
        [
            ("tick_speed", [0, -1, 11, 100]),
            ("spawn_rate", [-0.1, -1.0, 1.1, 2.0]),
            ("phase_duration", [0, -1, 21, 100]),
        ],
    )
    def test_invalid_values_out_of_bounds(self, field_name, invalid_values):
        """Test invalid values outside allowed ranges for all configuration fields."""
        for invalid_value in invalid_values:
            # Arrange & Act - This should raise ValidationError
            with pytest.raises(ValidationError) as exc_info:
                ConfigUpdateRequest(**{field_name: invalid_value})

            # Assert - Verify the validation error details
            errors = exc_info.value.errors()
            assert len(errors) == 1
            assert errors[0]["loc"] == (field_name,)

            # Assert - Verify error message contains boundary information
            error_msg = str(errors[0]["msg"])
            assert (
                "greater than or equal to" in error_msg
                or "less than or equal to" in error_msg
            )

    @pytest.mark.parametrize(
        "field_name,invalid_value",
        [
            ("tick_speed", "not_a_number"),
            ("tick_speed", 5.5),
            ("spawn_rate", "invalid"),
            ("spawn_rate", [1, 2, 3]),  # List is not a valid type
            ("phase_duration", "string"),
            ("phase_duration", 3.14),
        ],
    )
    def test_invalid_field_types(self, field_name, invalid_value):
        """Test invalid field types for configuration parameters."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            ConfigUpdateRequest(**{field_name: invalid_value})

        # Verify the error is about type validation
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == (field_name,)

    def test_multiple_invalid_fields_all_reported(self):
        """Test that validation errors for multiple fields are all reported together."""
        # Arrange & Act - Send request with all fields invalid
        with pytest.raises(ValidationError) as exc_info:
            ConfigUpdateRequest(
                tick_speed=15, spawn_rate=-0.5, phase_duration=25  # > 10  # < 0  # > 20
            )

        # Assert - All validation errors should be reported, not just the first one
        errors = exc_info.value.errors()
        assert len(errors) == 3, "All field validation errors should be reported"

        # Assert - Each field should have its own error
        error_fields = {error["loc"][0] for error in errors}
        assert error_fields == {"tick_speed", "spawn_rate", "phase_duration"}

    def test_config_serialization(self):
        """Test that valid config can be serialized to dict."""
        # Arrange
        config = ConfigUpdateRequest(tick_speed=7, spawn_rate=0.2, phase_duration=4)

        # Act
        config_dict = config.model_dump()

        # Assert
        expected = {"tick_speed": 7, "spawn_rate": 0.2, "phase_duration": 4}
        assert config_dict == expected

    def test_config_serialization_with_none_values(self):
        """Test serialization with None values."""
        # Arrange
        config = ConfigUpdateRequest(tick_speed=3)

        # Act
        config_dict = config.model_dump()

        # Assert
        expected = {"tick_speed": 3, "spawn_rate": None, "phase_duration": None}
        assert config_dict == expected


# TODO: Add these test classes when the functionality is implemented:
#
# class TestAPIRoutes:
#     """Test cases for REST API endpoints when implemented."""
#
# class TestWebSocketManager:
#     """Test cases for WebSocket management when implemented."""
#
# class TestConfigValidationIntegration:
#     """Integration tests when API endpoints are connected to validation."""
