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


class TestWordReplacements:
    """Test word replacement feature."""

    def test_config_default_empty(self, mock_config):
        """Default config has no word replacements."""
        assert mock_config.word_replacements == {}

    def test_config_roundtrip(self, tmp_path, monkeypatch):
        """Word replacements persist through save/load cycle."""
        from tommy_talker.utils.config import UserConfig, save_config, load_config, BASE_DATA_DIR
        monkeypatch.setattr("tommy_talker.utils.config.BASE_DATA_DIR", tmp_path)

        config = UserConfig(word_replacements={"Korreg": "CoreRag", "super whisper": "Superwhisper"})
        save_config(config)
        loaded = load_config()
        assert loaded.word_replacements == {"Korreg": "CoreRag", "super whisper": "Superwhisper"}

    def test_replacement_applied(self):
        """Word replacements are applied to text."""
        import re
        replacements = {"Korreg": "CoreRag"}
        text = "Check out Korreg for details"
        for original, replacement in replacements.items():
            text = re.sub(r'\b' + re.escape(original) + r'\b', replacement, text, flags=re.IGNORECASE)
        assert text == "Check out CoreRag for details"

    def test_replacement_case_insensitive(self):
        """Replacements match regardless of case."""
        import re
        replacements = {"korreg": "CoreRag"}
        text = "Use KORREG or korreg"
        for original, replacement in replacements.items():
            text = re.sub(r'\b' + re.escape(original) + r'\b', replacement, text, flags=re.IGNORECASE)
        assert text == "Use CoreRag or CoreRag"

    def test_replacement_whole_word_only(self):
        """Replacements only match whole words, not substrings."""
        import re
        replacements = {"core": "Core"}
        text = "The corerag module is in hardcore mode"
        for original, replacement in replacements.items():
            text = re.sub(r'\b' + re.escape(original) + r'\b', replacement, text, flags=re.IGNORECASE)
        assert "corerag" in text  # Should NOT be replaced inside another word
        assert "hardcore" in text  # Should NOT be replaced inside another word

    def test_replacement_multi_word(self):
        """Multi-word originals are supported."""
        import re
        replacements = {"super whisper": "Superwhisper"}
        text = "I used super whisper yesterday"
        for original, replacement in replacements.items():
            text = re.sub(r'\b' + re.escape(original) + r'\b', replacement, text, flags=re.IGNORECASE)
        assert text == "I used Superwhisper yesterday"

    def test_multiple_replacements(self):
        """Multiple replacement rules are applied in sequence."""
        import re
        replacements = {"Korreg": "CoreRag", "HooHoo": "WhoWho"}
        text = "Try Korreg and HooHoo"
        for original, replacement in replacements.items():
            text = re.sub(r'\b' + re.escape(original) + r'\b', replacement, text, flags=re.IGNORECASE)
        assert text == "Try CoreRag and WhoWho"


class TestOperatingModes:
    """Test operating mode enumeration."""

    def test_operating_mode_values(self):
        """Push-to-talk cursor mode is defined."""
        from tommy_talker.engine.modes import OperatingMode

        assert OperatingMode.CURSOR.value == "cursor"

    def test_mode_result_dataclass(self):
        """ModeResult dataclass is properly structured."""
        from tommy_talker.engine.modes import ModeResult

        result = ModeResult(success=True, text="Hello world")
        assert result.success is True
        assert result.text == "Hello world"
        assert result.error is None
