"""
TommyTalker App Context Detection
Detects the frontmost app and looks up its text input format profile.
"""

import json
import logging
from enum import Enum
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

log = logging.getLogger("TommyTalker")

# Try to import NSWorkspace for frontmost app detection
try:
    from AppKit import NSWorkspace
    HAS_APPKIT = True
except ImportError:
    HAS_APPKIT = False


class TextInputFormat(Enum):
    """Text input format types for different app categories."""
    PLAINTEXT = "plaintext"
    CODE = "code"
    CHAT_MESSAGE = "chat_message"
    EMAIL = "email"
    MARKDOWN = "markdown"
    TERMINAL_COMMAND = "terminal_command"
    SEARCH_QUERY = "search_query"
    DOCUMENT_TEXT = "document_text"
    RICH_TEXT = "rich_text"
    URL = "url"
    SPREADSHEET_FORMULA = "spreadsheet_formula"


@dataclass
class AppProfile:
    """Profile for a known macOS application."""
    name: str
    bundle_id: str
    category: str
    text_input_format: TextInputFormat
    short_description: str = ""


@dataclass
class AppContext:
    """Snapshot of the current app context at a point in time."""
    app_name: str
    bundle_id: str
    profile: Optional[AppProfile]
    text_input_format: TextInputFormat


# Module-level cache for loaded profiles
_profiles_cache: Optional[dict[str, AppProfile]] = None


def detect_frontmost_app() -> tuple[str, str]:
    """
    Detect the frontmost application via NSWorkspace.

    Returns:
        (app_name, bundle_id) tuple. Falls back to ("Unknown", "") if unavailable.
    """
    if not HAS_APPKIT:
        return ("Unknown", "")

    try:
        app = NSWorkspace.sharedWorkspace().frontmostApplication()
        if app:
            name = app.localizedName() or "Unknown"
            bundle_id = app.bundleIdentifier() or ""
            return (name, bundle_id)
    except Exception as e:
        log.error("Error detecting frontmost app: %s", e)

    return ("Unknown", "")


def _get_bundled_profiles_path() -> Path:
    """Get path to the bundled app_profiles.json."""
    return Path(__file__).resolve().parent.parent / "data" / "app_profiles.json"


def _get_custom_profiles_path() -> Path:
    """Get path to user's custom app profiles override."""
    from tommy_talker.utils.config import BASE_DATA_DIR
    return BASE_DATA_DIR / "custom_app_profiles.json"


def load_app_profiles() -> dict[str, AppProfile]:
    """
    Load app profiles from bundled JSON and user custom overrides.
    Results are cached after first load.

    Returns:
        Dict mapping lowercased app name → AppProfile
    """
    global _profiles_cache
    if _profiles_cache is not None:
        return _profiles_cache

    profiles: dict[str, AppProfile] = {}

    # Load bundled profiles
    bundled_path = _get_bundled_profiles_path()
    if bundled_path.exists():
        try:
            with open(bundled_path) as f:
                data = json.load(f)

            for key, entry in data.get("apps", {}).items():
                try:
                    fmt = TextInputFormat(entry.get("text_input_format", "plaintext"))
                except ValueError:
                    fmt = TextInputFormat.PLAINTEXT

                profiles[key.lower()] = AppProfile(
                    name=entry.get("name", key),
                    bundle_id=entry.get("bundle_id", ""),
                    category=entry.get("category", ""),
                    text_input_format=fmt,
                    short_description=entry.get("short_description", ""),
                )

            log.debug("Loaded %s bundled app profiles", len(profiles))
        except Exception as e:
            log.error("Error loading bundled profiles: %s", e)

    # Load custom overrides (user profiles take precedence)
    custom_path = _get_custom_profiles_path()
    if custom_path.exists():
        try:
            with open(custom_path) as f:
                data = json.load(f)

            count = 0
            for key, entry in data.get("apps", {}).items():
                try:
                    fmt = TextInputFormat(entry.get("text_input_format", "plaintext"))
                except ValueError:
                    fmt = TextInputFormat.PLAINTEXT

                profiles[key.lower()] = AppProfile(
                    name=entry.get("name", key),
                    bundle_id=entry.get("bundle_id", ""),
                    category=entry.get("category", ""),
                    text_input_format=fmt,
                    short_description=entry.get("short_description", ""),
                )
                count += 1

            if count:
                log.debug("Loaded %s custom app profile overrides", count)
        except Exception as e:
            log.error("Error loading custom profiles: %s", e)

    _profiles_cache = profiles
    return profiles


def lookup_profile(
    app_name: str, bundle_id: str, profiles: dict[str, AppProfile]
) -> Optional[AppProfile]:
    """
    Look up an app profile by name and bundle_id.

    Matching order:
    1. Exact name match (case-insensitive)
    2. Bundle ID match
    3. Prefix match (e.g., "Google Chrome" matches "google chrome helper")

    Returns:
        AppProfile or None if not found.
    """
    name_lower = app_name.lower()

    # 1. Exact name match
    if name_lower in profiles:
        return profiles[name_lower]

    # 2. Bundle ID match
    if bundle_id:
        for profile in profiles.values():
            if profile.bundle_id and profile.bundle_id == bundle_id:
                return profile

    # 3. Prefix match
    for key, profile in profiles.items():
        if name_lower.startswith(key) or key.startswith(name_lower):
            return profile

    return None


def get_app_context() -> AppContext:
    """
    Detect the frontmost app and return its context with text input format.
    This is the main public API — call this at recording start time.

    Returns:
        AppContext snapshot.
    """
    app_name, bundle_id = detect_frontmost_app()
    profiles = load_app_profiles()
    profile = lookup_profile(app_name, bundle_id, profiles)

    text_format = profile.text_input_format if profile else TextInputFormat.PLAINTEXT

    return AppContext(
        app_name=app_name,
        bundle_id=bundle_id,
        profile=profile,
        text_input_format=text_format,
    )
