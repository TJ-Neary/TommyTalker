"""
Prompt Injection & Content Security Utilities

Defense-in-depth content validation for AI applications.

Provides:
- FileValidator: Magic byte & extension verification for file uploads
- PromptInjectionDetector: Pattern-based detection of jailbreaks and injection attempts
- ContentSanitizer: Cleaning untrusted text before LLM processing

Usage:
    from tommy_talker.utils.prompt_injection import scan_text, scan_file, ThreatLevel

    # Scan user input before sending to LLM
    result = scan_text(user_input)
    if result.blocked:
        return f"Input blocked: {result.reason}"

    # Validate file before ingestion
    result = scan_file("/path/to/upload.pdf")
    if not result.passed:
        return f"File rejected: {result.reason}"

Contributed by: Kendra
Synced from: _HQ/templates/src-skeleton/utils/prompt_injection.py v1
"""

import os
import re
import logging
import hashlib
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple, Set
from enum import Enum

logger = logging.getLogger(__name__)


class ThreatLevel(Enum):
    """Severity levels for detected threats."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Threat:
    """Represents a detected security threat."""
    level: ThreatLevel
    category: str
    description: str
    evidence: str = ""
    line_number: Optional[int] = None


@dataclass
class SecurityResult:
    """Result of security validation."""
    passed: bool
    blocked: bool = False
    reason: str = ""
    threats: List[Threat] = field(default_factory=list)
    sanitized_content: Optional[str] = None
    original_hash: str = ""
    sanitized_hash: str = ""

    @property
    def threat_count(self) -> int:
        return len(self.threats)

    @property
    def highest_threat(self) -> Optional[ThreatLevel]:
        """Return the highest threat level found."""
        if not self.threats:
            return None
        priority = {
            ThreatLevel.CRITICAL: 4,
            ThreatLevel.HIGH: 3,
            ThreatLevel.MEDIUM: 2,
            ThreatLevel.LOW: 1,
            ThreatLevel.NONE: 0,
        }
        return max(self.threats, key=lambda t: priority.get(t.level, 0)).level


class FileValidator:
    """
    Validates files using extension allowlist and magic byte verification.

    Use this to validate file uploads before processing or ingestion.
    """

    # Safe extensions for typical RAG/document ingestion
    SAFE_EXTENSIONS: Set[str] = {
        '.txt', '.md', '.markdown', '.rst', '.text',
        '.json', '.csv', '.xml', '.yaml', '.yml', '.toml',
        '.html', '.htm', '.xhtml',
        '.pdf',
        '.py', '.js', '.ts',  # Code files (scan separately if executing)
    }

    # Extensions that should NEVER be allowed
    BLOCKED_EXTENSIONS: Set[str] = {
        '.exe', '.bat', '.cmd', '.sh', '.bash', '.ps1',
        '.app', '.dmg', '.pkg', '.deb', '.rpm', '.msi',
        '.dll', '.so', '.dylib', '.sys',
        '.zip', '.tar', '.gz', '.rar', '.7z',
        '.docm', '.xlsm', '.pptm',  # Office files with macros
    }

    # Magic bytes (file signatures) for verification
    MAGIC_BYTES: Dict[str, List[Tuple[bytes, int]]] = {
        '.pdf': [(b'%PDF', 0)],
        '.html': [(b'<!DOCTYPE', 0), (b'<html', 0), (b'<HTML', 0)],
        '.xml': [(b'<?xml', 0)],
        '.json': [(b'{', 0), (b'[', 0)],
        '.png': [(b'\x89PNG\r\n\x1a\n', 0)],
        '.jpg': [(b'\xff\xd8\xff', 0)],
        '.exe': [(b'MZ', 0)],
        '.zip': [(b'PK\x03\x04', 0)],
    }

    # Max file sizes by extension (bytes)
    MAX_SIZES: Dict[str, int] = {
        '.txt': 50 * 1024 * 1024,   # 50 MB
        '.md': 50 * 1024 * 1024,
        '.json': 100 * 1024 * 1024,  # 100 MB
        '.pdf': 100 * 1024 * 1024,
        'default': 20 * 1024 * 1024,  # 20 MB
    }

    def __init__(self, custom_allowed: Optional[Set[str]] = None):
        """
        Initialize validator with optional custom allowed extensions.

        Args:
            custom_allowed: Additional extensions to allow beyond SAFE_EXTENSIONS
        """
        self.allowed = self.SAFE_EXTENSIONS.copy()
        if custom_allowed:
            self.allowed.update(custom_allowed)

    def validate_extension(self, path: str) -> Tuple[bool, str]:
        """Check if file extension is allowed."""
        ext = os.path.splitext(path)[1].lower()
        if ext in self.BLOCKED_EXTENSIONS:
            return False, f"Blocked extension: {ext}"
        if ext not in self.allowed:
            return False, f"Extension not in allowlist: {ext}"
        return True, "Extension allowed"

    def validate_magic_bytes(self, path: str) -> Tuple[bool, str]:
        """Verify file content matches expected magic bytes for extension."""
        ext = os.path.splitext(path)[1].lower()
        if not os.path.exists(path):
            return False, "File not found"

        try:
            with open(path, 'rb') as f:
                header = f.read(32)
        except Exception as e:
            return False, f"Cannot read file: {e}"

        if not header:
            return True, "Empty file"

        # Check for executable signatures in non-executable files
        if ext not in {'.exe', '.dll', '.app', '.so', '.dylib'}:
            if header[:2] == b'MZ':
                return False, "File contains executable signature (MZ header)"
            if header[:4] == b'\x7fELF':
                return False, "File contains executable signature (ELF header)"

        # Specific magic byte checks
        if ext in self.MAGIC_BYTES:
            matches = False
            for magic, offset in self.MAGIC_BYTES[ext]:
                if header[offset:offset + len(magic)] == magic:
                    matches = True
                    break
            if not matches:
                return False, f"Magic bytes do not match expected for {ext}"

        return True, "Magic bytes verified"

    def validate_size(self, path: str) -> Tuple[bool, str]:
        """Check if file size is within limits."""
        try:
            size = os.path.getsize(path)
        except Exception:
            return False, "Cannot get file size"

        ext = os.path.splitext(path)[1].lower()
        max_size = self.MAX_SIZES.get(ext, self.MAX_SIZES['default'])

        if size > max_size:
            return False, f"File too large: {size} bytes (max: {max_size})"
        return True, "Size OK"

    def validate_file(self, path: str) -> SecurityResult:
        """
        Perform full file validation.

        Returns:
            SecurityResult with pass/fail status and any detected threats
        """
        threats = []

        ext_ok, ext_reason = self.validate_extension(path)
        if not ext_ok:
            threats.append(Threat(
                ThreatLevel.HIGH,
                "blocked_extension",
                ext_reason,
                os.path.basename(path)
            ))

        size_ok, size_reason = self.validate_size(path)
        if not size_ok:
            threats.append(Threat(
                ThreatLevel.MEDIUM,
                "size_limit",
                size_reason
            ))

        if ext_ok:
            magic_ok, magic_reason = self.validate_magic_bytes(path)
            if not magic_ok:
                threats.append(Threat(
                    ThreatLevel.CRITICAL,
                    "magic_byte_mismatch",
                    magic_reason,
                    os.path.basename(path)
                ))

        criticals = [t for t in threats if t.level in {ThreatLevel.CRITICAL, ThreatLevel.HIGH}]
        return SecurityResult(
            passed=len(criticals) == 0,
            blocked=len(criticals) > 0,
            reason=criticals[0].description if criticals else "File validated",
            threats=threats
        )


class PromptInjectionDetector:
    """
    Detect prompt injection attempts in text content.

    Patterns cover:
    - Instruction override attempts ("ignore previous instructions")
    - System prompt injection ("system: ...")
    - Jailbreak patterns (DAN, roleplay)
    - Authority impersonation ("as your developer")
    - Data exfiltration attempts ("send all emails to")
    - Urgency manipulation (common in phishing)
    """

    SUSPICIOUS_PATTERNS: List[Tuple[str, ThreatLevel, str]] = [
        # Core injection patterns
        (r'(?i)ignore\s+(all\s+)?previous\s+instructions?', ThreatLevel.CRITICAL, "Instruction override attempt"),
        (r'(?i)disregard\s+(all\s+)?previous', ThreatLevel.CRITICAL, "Instruction override attempt"),
        (r'(?i)forget\s+(all\s+)?(your\s+)?instructions?', ThreatLevel.CRITICAL, "Instruction override attempt"),
        (r'(?i)system\s*:\s*', ThreatLevel.HIGH, "System prompt injection"),
        (r'(?i)do\s+anything\s+now', ThreatLevel.CRITICAL, "DAN jailbreak pattern"),
        (r'(?i)jailbreak', ThreatLevel.HIGH, "Explicit jailbreak mention"),
        (r'(?i)bypass\s+(your\s+)?restrictions?', ThreatLevel.HIGH, "Bypass attempt"),
        (r'(?i)respond\s+only\s+with', ThreatLevel.MEDIUM, "Output format override"),

        # Authority impersonation
        (r'(?i)as\s+(your\s+)?(developer|admin|administrator|owner|anthropic|openai)', ThreatLevel.HIGH, "Authority impersonation"),
        (r'(?i)i\s+am\s+(your\s+)?(creator|developer|admin)', ThreatLevel.HIGH, "Authority impersonation"),
        (r'(?i)this\s+is\s+a\s+system\s+message', ThreatLevel.HIGH, "Fake system message"),
        (r'(?i)user\s+has\s+(pre-?)?authorized', ThreatLevel.HIGH, "False authorization claim"),

        # Roleplay/persona manipulation
        (r'(?i)pretend\s+(you\s+are|to\s+be)', ThreatLevel.MEDIUM, "Roleplay attempt"),
        (r'(?i)act\s+as\s+if\s+you', ThreatLevel.MEDIUM, "Roleplay attempt"),
        (r'(?i)you\s+are\s+now\s+', ThreatLevel.MEDIUM, "Identity override attempt"),

        # Data exfiltration attempts
        (r'(?i)send\s+(all\s+)?(my\s+)?(contacts?|emails?|files?|data)\s+to', ThreatLevel.CRITICAL, "Data exfiltration attempt"),
        (r'(?i)forward\s+(all\s+)?(emails?|messages?)\s+to', ThreatLevel.HIGH, "Email forwarding attempt"),
        (r'(?i)export\s+(all\s+)?(my\s+)?data\s+to', ThreatLevel.HIGH, "Data export attempt"),

        # Urgency manipulation (common in phishing content)
        (r'(?i)act\s+(immediately|now|urgently)', ThreatLevel.MEDIUM, "Urgency manipulation"),
        (r'(?i)click\s+(here|this|the\s+link)\s+(immediately|now|urgently)', ThreatLevel.MEDIUM, "Urgent click request"),
        (r'(?i)your\s+account\s+(will\s+be|has\s+been)\s+(suspended|locked|terminated)', ThreatLevel.MEDIUM, "Account threat manipulation"),
    ]

    # Unicode invisible characters often used to hide injection
    INVISIBLE_CHARS: Set[str] = {
        '\u200b',  # Zero-width space
        '\u200c',  # Zero-width non-joiner
        '\u200d',  # Zero-width joiner
        '\u2060',  # Word joiner
        '\ufeff',  # Zero-width no-break space (BOM)
    }

    def __init__(self, strict_mode: bool = True, custom_patterns: Optional[List[Tuple[str, ThreatLevel, str]]] = None):
        """
        Initialize detector.

        Args:
            strict_mode: If True, be more aggressive with detection
            custom_patterns: Additional patterns to check (regex, level, description)
        """
        self.strict_mode = strict_mode
        patterns = list(self.SUSPICIOUS_PATTERNS)
        if custom_patterns:
            patterns.extend(custom_patterns)
        self._compiled_patterns = [
            (re.compile(p, re.MULTILINE), l, d) for p, l, d in patterns
        ]

    def detect(self, text: str) -> List[Threat]:
        """
        Scan text for injection attempts.

        Args:
            text: The text content to scan

        Returns:
            List of detected Threat objects
        """
        threats = []

        # Check for invisible characters (often used to hide payloads)
        found_invis = [c for c in text if c in self.INVISIBLE_CHARS]
        if found_invis:
            threats.append(Threat(
                ThreatLevel.MEDIUM,
                "invisible_characters",
                f"Found {len(found_invis)} invisible/zero-width characters"
            ))

        # Check all patterns
        for pattern, level, desc in self._compiled_patterns:
            matches = pattern.finditer(text)
            for match in matches:
                threats.append(Threat(
                    level,
                    "pattern_match",
                    desc,
                    match.group(0)[:100]  # Truncate evidence
                ))

        return threats


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

MAX_SCAN_TEXT_LENGTH = 50_000  # 50K chars max for scan_text


def scan_text(text: str, strict: bool = True) -> SecurityResult:
    """
    Quick scan text for prompt injection attempts.

    Args:
        text: Text content to scan
        strict: Enable strict mode for more aggressive detection

    Returns:
        SecurityResult with pass/fail status and detected threats
    """
    if len(text) > MAX_SCAN_TEXT_LENGTH:
        return SecurityResult(
            passed=False,
            blocked=True,
            reason=f"Input too long ({len(text)} chars, max {MAX_SCAN_TEXT_LENGTH})",
            threats=[Threat(
                ThreatLevel.HIGH,
                "input_length",
                f"Input exceeds {MAX_SCAN_TEXT_LENGTH} character limit"
            )],
        )

    detector = PromptInjectionDetector(strict_mode=strict)
    threats = detector.detect(text)

    critical_threats = [t for t in threats if t.level in {ThreatLevel.CRITICAL, ThreatLevel.HIGH}]
    return SecurityResult(
        passed=len(critical_threats) == 0,
        blocked=len(critical_threats) > 0,
        reason=critical_threats[0].description if critical_threats else "Content safe",
        threats=threats
    )


def scan_file(path: str, custom_allowed: Optional[Set[str]] = None) -> SecurityResult:
    """
    Quick scan file for safety before processing.

    Args:
        path: Path to file to validate
        custom_allowed: Additional extensions to allow

    Returns:
        SecurityResult with pass/fail status
    """
    validator = FileValidator(custom_allowed=custom_allowed)
    return validator.validate_file(path)
