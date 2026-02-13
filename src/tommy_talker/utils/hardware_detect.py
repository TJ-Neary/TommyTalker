"""
TommyTalker Hardware Detection
RAM and chip detection with tier-based Whisper model recommendations.
"""

import platform
import subprocess
from dataclasses import dataclass

import logging

import psutil

log = logging.getLogger("TommyTalker")


@dataclass
class HardwareProfile:
    """Hardware profile with tier-based model recommendations."""
    ram_gb: int
    chip_type: str  # "M1", "M2", "M3", "M4", "Intel", etc.
    tier: int       # 1, 2, or 3
    whisper_model: str


# Tier thresholds and recommendations
TIER_CONFIG = {
    1: {  # <16GB RAM - Basic
        "whisper_model": "mlx-community/distil-whisper-small",
    },
    2: {  # 16-32GB RAM - Standard
        "whisper_model": "mlx-community/distil-whisper-medium.en",
    },
    3: {  # >32GB RAM - Pro (Max chips)
        "whisper_model": "mlx-community/distil-whisper-large-v3",
    },
}


def detect_chip_type() -> str:
    """Detect Apple Silicon or Intel chip type."""
    try:
        machine = platform.machine()

        if machine == "arm64":
            result = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True,
                text=True
            )
            brand = result.stdout.strip()

            if "M4" in brand:
                return "M4"
            elif "M3" in brand:
                return "M3"
            elif "M2" in brand:
                return "M2"
            elif "M1" in brand:
                return "M1"
            else:
                return "Apple Silicon"

        elif machine == "x86_64":
            return "Intel"
        else:
            return "Unknown"

    except Exception as e:
        log.error("Error detecting chip: %s", e)
        return "Unknown"


def detect_ram_gb() -> int:
    """Detect total system RAM in GB."""
    try:
        total_bytes = psutil.virtual_memory().total
        ram_gb = int(total_bytes / (1024 ** 3))
        return ram_gb
    except Exception as e:
        log.error("Error detecting RAM: %s", e)
        return 8  # Conservative default


def calculate_tier(ram_gb: int) -> int:
    """Calculate hardware tier based on RAM."""
    if ram_gb < 16:
        return 1
    elif ram_gb <= 32:
        return 2
    else:
        return 3


def detect_hardware() -> HardwareProfile:
    """
    Detect hardware and return profile with Whisper model recommendation.

    Returns:
        HardwareProfile with tier-appropriate model recommendation
    """
    ram_gb = detect_ram_gb()
    chip_type = detect_chip_type()
    tier = calculate_tier(ram_gb)

    config = TIER_CONFIG[tier]

    profile = HardwareProfile(
        ram_gb=ram_gb,
        chip_type=chip_type,
        tier=tier,
        whisper_model=config["whisper_model"],
    )

    log.debug("%s, %sGB RAM -> Tier %s", chip_type, ram_gb, tier)
    log.debug("Whisper model: %s", profile.whisper_model)

    return profile


def get_tier_description(tier: int) -> str:
    """Get human-readable tier description."""
    descriptions = {
        1: "Basic (optimized for 8-16GB RAM)",
        2: "Standard (optimized for 16-32GB RAM)",
        3: "Pro (optimized for 32GB+ RAM)",
    }
    return descriptions.get(tier, "Unknown")
