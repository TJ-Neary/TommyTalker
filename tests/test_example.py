"""
Example test file demonstrating testing patterns for TommyTalker.

Delete or rename this file once real tests are in place.
"""

import pytest
from pathlib import Path


class TestProjectSetup:
    """Verify the project is configured correctly."""

    def test_project_directory_exists(self, tmp_project_dir):
        """Temporary project dir is created by fixture."""
        assert tmp_project_dir.exists()
        assert (tmp_project_dir / "data").is_dir()
        assert (tmp_project_dir / "recordings").is_dir()

    def test_environment_configured(self, mock_env):
        """Mock environment variables are set."""
        import os
        assert os.getenv("TOMMY_TALKER_STATE_DIR") is not None
        assert os.getenv("LOG_LEVEL") == "DEBUG"


class TestConfigModule:
    """Test configuration module."""

    def test_mock_config_has_defaults(self, mock_config):
        """Mock config fixture provides usable defaults."""
        assert mock_config.default_mode == "cursor"
        assert "TommyTalker" in mock_config.vocabulary

    def test_mock_hardware_tier_3(self, mock_hardware):
        """Mock hardware fixture provides Tier 3 profile."""
        assert mock_hardware.tier == 3
        assert mock_hardware.ram_gb >= 32
        assert mock_hardware.diarization_enabled is True


class TestOperatingModes:
    """Test operating mode enumeration."""

    def test_operating_mode_values(self):
        """All four operating modes are defined."""
        from tommy_talker.engine.modes import OperatingMode

        assert OperatingMode.CURSOR.value == "cursor"
        assert OperatingMode.EDITOR.value == "editor"
        assert OperatingMode.MEETING.value == "meeting"
        assert OperatingMode.HUD.value == "hud"

    def test_mode_result_dataclass(self):
        """ModeResult dataclass is properly structured."""
        from tommy_talker.engine.modes import ModeResult

        result = ModeResult(success=True, text="Hello world")
        assert result.success is True
        assert result.text == "Hello world"
        assert result.error is None
