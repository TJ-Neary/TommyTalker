"""
Tests for app context detection and profile system.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from tommy_talker.utils.app_context import (
    TextInputFormat,
    AppProfile,
    AppContext,
    detect_frontmost_app,
    load_app_profiles,
    lookup_profile,
    get_app_context,
    _get_bundled_profiles_path,
)


class TestTextInputFormat:
    """Test TextInputFormat enum."""

    def test_all_format_types_exist(self):
        """All expected text input format types are defined."""
        expected = [
            "plaintext", "code", "chat_message", "email", "markdown",
            "terminal_command", "search_query", "document_text",
            "rich_text", "url", "spreadsheet_formula",
        ]
        actual = [f.value for f in TextInputFormat]
        for fmt in expected:
            assert fmt in actual, f"Missing format: {fmt}"

    def test_format_from_string(self):
        """Can create format from string value."""
        assert TextInputFormat("code") == TextInputFormat.CODE
        assert TextInputFormat("chat_message") == TextInputFormat.CHAT_MESSAGE


class TestLoadAppProfiles:
    """Test bundled app profile loading."""

    def test_bundled_json_loads(self):
        """Bundled app_profiles.json loads successfully."""
        # Clear cache first
        import tommy_talker.utils.app_context as mod
        mod._profiles_cache = None

        profiles = load_app_profiles()
        assert len(profiles) > 50, f"Expected 50+ profiles, got {len(profiles)}"

    def test_bundled_json_schema_valid(self):
        """Each profile has required fields."""
        import tommy_talker.utils.app_context as mod
        mod._profiles_cache = None

        profiles = load_app_profiles()
        for key, profile in profiles.items():
            assert isinstance(profile, AppProfile)
            assert profile.name, f"Profile {key} missing name"
            assert isinstance(profile.text_input_format, TextInputFormat)

    def test_known_apps_present(self):
        """Key apps are in the database."""
        import tommy_talker.utils.app_context as mod
        mod._profiles_cache = None

        profiles = load_app_profiles()
        assert "slack" in profiles
        assert "visual studio code" in profiles
        assert "terminal" in profiles
        assert "safari" in profiles
        assert "obsidian" in profiles

    def test_known_app_formats(self):
        """Known apps have correct format types."""
        import tommy_talker.utils.app_context as mod
        mod._profiles_cache = None

        profiles = load_app_profiles()
        assert profiles["slack"].text_input_format == TextInputFormat.CHAT_MESSAGE
        assert profiles["terminal"].text_input_format == TextInputFormat.TERMINAL_COMMAND
        assert profiles["visual studio code"].text_input_format == TextInputFormat.CODE
        assert profiles["safari"].text_input_format == TextInputFormat.SEARCH_QUERY
        assert profiles["mail"].text_input_format == TextInputFormat.EMAIL
        assert profiles["obsidian"].text_input_format == TextInputFormat.MARKDOWN

    def test_cache_works(self):
        """Profiles are cached after first load."""
        import tommy_talker.utils.app_context as mod
        mod._profiles_cache = None

        p1 = load_app_profiles()
        p2 = load_app_profiles()
        assert p1 is p2, "Second call should return cached instance"

    def test_missing_bundled_file_graceful(self, tmp_path):
        """Gracefully handles missing bundled file."""
        import tommy_talker.utils.app_context as mod
        mod._profiles_cache = None

        with patch.object(mod, '_get_bundled_profiles_path', return_value=tmp_path / "missing.json"):
            with patch.object(mod, '_get_custom_profiles_path', return_value=tmp_path / "missing2.json"):
                profiles = load_app_profiles()
                assert profiles == {}
        mod._profiles_cache = None

    def test_custom_overrides(self, tmp_path):
        """Custom profiles override bundled ones."""
        import tommy_talker.utils.app_context as mod
        mod._profiles_cache = None

        custom = {"apps": {
            "myapp": {
                "name": "MyApp",
                "bundle_id": "com.test.myapp",
                "category": "Custom",
                "text_input_format": "code"
            }
        }}
        custom_path = tmp_path / "custom.json"
        custom_path.write_text(json.dumps(custom))

        with patch.object(mod, '_get_custom_profiles_path', return_value=custom_path):
            profiles = load_app_profiles()
            assert "myapp" in profiles
            assert profiles["myapp"].text_input_format == TextInputFormat.CODE
        mod._profiles_cache = None


class TestLookupProfile:
    """Test profile lookup logic."""

    @pytest.fixture
    def sample_profiles(self):
        return {
            "slack": AppProfile("Slack", "com.tinyspeck.slackmacgap", "Communication", TextInputFormat.CHAT_MESSAGE),
            "visual studio code": AppProfile("Visual Studio Code", "com.microsoft.VSCode", "Developer Tools", TextInputFormat.CODE),
            "safari": AppProfile("Safari", "com.apple.Safari", "Web Browser", TextInputFormat.SEARCH_QUERY),
        }

    def test_exact_name_match(self, sample_profiles):
        """Exact name match (case-insensitive)."""
        result = lookup_profile("Slack", "", sample_profiles)
        assert result is not None
        assert result.name == "Slack"

    def test_case_insensitive(self, sample_profiles):
        """Lookup is case-insensitive."""
        result = lookup_profile("SLACK", "", sample_profiles)
        assert result is not None
        assert result.name == "Slack"

    def test_bundle_id_fallback(self, sample_profiles):
        """Falls back to bundle_id match."""
        result = lookup_profile("Unknown App", "com.microsoft.VSCode", sample_profiles)
        assert result is not None
        assert result.name == "Visual Studio Code"

    def test_prefix_match(self, sample_profiles):
        """Prefix matching works for partial names."""
        result = lookup_profile("Visual Studio Code - Insiders", "", sample_profiles)
        assert result is not None
        assert result.text_input_format == TextInputFormat.CODE

    def test_unknown_returns_none(self, sample_profiles):
        """Unknown app returns None."""
        result = lookup_profile("Totally Unknown App", "com.unknown.app", sample_profiles)
        assert result is None


class TestDetectFrontmostApp:
    """Test frontmost app detection."""

    def test_returns_tuple(self):
        """detect_frontmost_app returns (name, bundle_id) tuple."""
        result = detect_frontmost_app()
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_graceful_without_appkit(self):
        """Returns fallback when AppKit not available."""
        import tommy_talker.utils.app_context as mod
        original = mod.HAS_APPKIT
        mod.HAS_APPKIT = False
        try:
            name, bundle_id = detect_frontmost_app()
            assert name == "Unknown"
            assert bundle_id == ""
        finally:
            mod.HAS_APPKIT = original


class TestGetAppContext:
    """Test the full get_app_context() public API."""

    def test_returns_app_context(self):
        """get_app_context returns an AppContext instance."""
        ctx = get_app_context()
        assert isinstance(ctx, AppContext)
        assert isinstance(ctx.text_input_format, TextInputFormat)

    def test_unknown_app_gets_plaintext(self):
        """Unknown apps default to PLAINTEXT format."""
        import tommy_talker.utils.app_context as mod
        mod._profiles_cache = None

        with patch.object(mod, 'detect_frontmost_app', return_value=("UnknownXYZ123", "com.unknown")):
            ctx = get_app_context()
            assert ctx.text_input_format == TextInputFormat.PLAINTEXT
            assert ctx.profile is None
        mod._profiles_cache = None
