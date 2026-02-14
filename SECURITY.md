# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in TommyTalker, please report it responsibly.

**Do NOT open a public GitHub issue for security vulnerabilities.**

Instead, email the maintainer directly or use GitHub's private vulnerability reporting feature:

1. Go to the [Security tab](https://github.com/TJ-Neary/TommyTalker/security)
2. Click "Report a vulnerability"
3. Provide a description, steps to reproduce, and potential impact

You should receive a response within 7 days.

## Security Model

TommyTalker is designed with privacy and security as core principles:

- **Local-only processing** — All audio capture and speech recognition runs on-device via mlx-whisper. No audio or transcribed text is transmitted to external services.
- **No telemetry** — No usage tracking, analytics, or network calls.
- **Pre-commit security scanning** — A 9-phase scanner (`scripts/security_scan.sh`) checks for secrets, PII, hardcoded paths, dangerous code patterns, and sensitive file exposure before every commit.
- **AST code validation** — Static analysis detects dangerous imports and function calls.
- **Filesystem boundary enforcement** — Path guard prevents out-of-bounds file access.

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |

## Scope

The following are in scope for security reports:

- Unintended data exfiltration (audio, text, or configuration)
- Privilege escalation via the Accessibility or Microphone permissions
- Code injection through configuration files or app profiles
- Sensitive data exposure in logs or temporary files

The following are out of scope:

- Physical access attacks (macOS assumes a trusted local user)
- Denial of service against the local application
- Vulnerabilities in upstream dependencies (report these to the dependency maintainer)
