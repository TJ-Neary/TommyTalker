"""
Shared test fixtures for TommyTalker.

Provides common setup: temporary directories, mock configurations,
and test data factories.
"""

import os
import sys
from pathlib import Path

import pytest

# Ensure `src/` package layout resolves when running tests from repo root.
SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


@pytest.fixture
def tmp_project_dir(tmp_path):
    """Create a temporary project directory with standard structure."""
    dirs = ["data", "logs", "recordings", "chroma"]
    for d in dirs:
        (tmp_path / d).mkdir()
    return tmp_path


@pytest.fixture
def mock_env(monkeypatch, tmp_project_dir):
    """Set environment variables pointing to temporary directories."""
    monkeypatch.setenv("TOMMY_TALKER_STATE_DIR", str(tmp_project_dir))
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("DEBUG", "true")
    return tmp_project_dir


@pytest.fixture
def sample_audio_path(tmp_path):
    """Create a path for sample audio (actual file creation requires soundfile)."""
    return tmp_path / "sample.wav"


@pytest.fixture
def sample_transcript():
    """Return sample transcript text for testing."""
    return (
        "Hello, this is a test transcription. "
        "The quick brown fox jumps over the lazy dog. "
        "Testing one two three."
    )


@pytest.fixture
def mock_config():
    """Return a mock UserConfig for testing."""
    from tommy_talker.utils.config import UserConfig
    return UserConfig(
        default_mode="cursor",
        vocabulary=["TommyTalker", "mlx-whisper"],
        skip_onboarding=True,
        logging_enabled=False,
    )


@pytest.fixture
def mock_hardware():
    """Return a mock HardwareProfile for testing."""
    from tommy_talker.utils.hardware_detect import HardwareProfile
    return HardwareProfile(
        chip_type="M4 Max",
        ram_gb=48,
        tier=3,
        whisper_model="large-v3-turbo",
        llm_model="qwen2.5:32b",
        diarization_enabled=True
    )
