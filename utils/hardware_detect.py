"""
TommyTalker Hardware Detection
RAM and chip detection with tier-based model recommendations.
"""

import platform
import subprocess
from dataclasses import dataclass

import psutil


@dataclass
class HardwareProfile:
    """Hardware profile with tier-based model recommendations."""
    ram_gb: int
    chip_type: str  # "M1", "M2", "M3", "M4", "Intel", etc.
    tier: int       # 1, 2, or 3
    
    # Recommended models based on tier
    whisper_model: str
    llm_model: str
    diarization_enabled: bool


# Tier thresholds and recommendations
TIER_CONFIG = {
    1: {  # <16GB RAM - Basic
        "whisper_model": "mlx-community/distil-whisper-small",
        "llm_model": "llama3.2:3b",  # More efficient/newer than Phi-3
        "diarization_enabled": False,
    },
    2: {  # 16-32GB RAM - Standard
        "whisper_model": "mlx-community/distil-whisper-medium.en",
        "llm_model": "llama3.1:8b",  # Upgrade from standard llama3
        "diarization_enabled": False,  # Optional, user can enable
    },
    3: {  # >32GB RAM - Pro (Max chips)
        "whisper_model": "mlx-community/distil-whisper-large-v3",
        "llm_model": "gemma2:27b",  # High-performance model for Max chips
        "diarization_enabled": True,
    },
}


def detect_chip_type() -> str:
    """Detect Apple Silicon or Intel chip type."""
    try:
        # Check if running on Apple Silicon
        machine = platform.machine()
        
        if machine == "arm64":
            # Get specific chip info via sysctl
            result = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True,
                text=True
            )
            brand = result.stdout.strip()
            
            # Extract chip generation (M1, M2, M3, M4)
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
        print(f"[HardwareDetect] Error detecting chip: {e}")
        return "Unknown"


def detect_ram_gb() -> int:
    """Detect total system RAM in GB."""
    try:
        total_bytes = psutil.virtual_memory().total
        ram_gb = int(total_bytes / (1024 ** 3))
        return ram_gb
    except Exception as e:
        print(f"[HardwareDetect] Error detecting RAM: {e}")
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
    Detect hardware and return profile with recommendations.
    
    This is the "Smart Logic" installer that runs on app launch.
    
    Returns:
        HardwareProfile with tier-appropriate model recommendations
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
        llm_model=config["llm_model"],
        diarization_enabled=config["diarization_enabled"],
    )
    
    print(f"[HardwareDetect] Detected: {chip_type}, {ram_gb}GB RAM → Tier {tier}")
    print(f"[HardwareDetect] Recommended Whisper: {profile.whisper_model}")
    print(f"[HardwareDetect] Recommended LLM: {profile.llm_model}")
    print(f"[HardwareDetect] Diarization: {'Enabled' if profile.diarization_enabled else 'Disabled'}")
    
    return profile


def get_tier_description(tier: int) -> str:
    """Get human-readable tier description."""
    descriptions = {
        1: "Basic (optimized for 8-16GB RAM)",
        2: "Standard (optimized for 16-32GB RAM)",
        3: "Pro (optimized for 32GB+ RAM)",
    }
    return descriptions.get(tier, "Unknown")
