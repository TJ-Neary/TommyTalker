#!/usr/bin/env bash
# =============================================================================
# TommyTalker Pre-Commit Security Scanner
# =============================================================================
# Scans tracked (or staged) files for secrets, PII, hardcoded paths, and other
# data that should never be committed to a public repository.
#
# Usage:
#   ./scripts/security_scan.sh              # Scan all tracked files
#   ./scripts/security_scan.sh --staged     # Scan only staged changes (for pre-commit hook)
#   ./scripts/security_scan.sh --fix        # Show suggested fixes
#
# Exit codes:
#   0 = clean
#   1 = findings detected
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

FINDINGS=0
MODE="tracked"  # "tracked" or "staged"
SHOW_FIX=false

for arg in "$@"; do
    case $arg in
        --staged) MODE="staged" ;;
        --fix)    SHOW_FIX=true ;;
        --help|-h)
            echo "Usage: $0 [--staged] [--fix]"
            echo "  --staged  Scan only staged changes (for pre-commit hook)"
            echo "  --fix     Show suggested fixes for each finding"
            exit 0
            ;;
    esac
done

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
finding() {
    local severity="$1"  # CRITICAL, HIGH, MEDIUM, LOW
    local category="$2"
    local file="$3"
    local detail="$4"
    local fix="${5:-}"

    FINDINGS=$((FINDINGS + 1))

    case "$severity" in
        CRITICAL) color="$RED" ;;
        HIGH)     color="$RED" ;;
        MEDIUM)   color="$YELLOW" ;;
        LOW)      color="$CYAN" ;;
        *)        color="$NC" ;;
    esac

    echo -e "${color}[${severity}]${NC} ${BOLD}${category}${NC}"
    echo -e "  File: ${file}"
    echo -e "  Detail: ${detail}"
    if [ "$SHOW_FIX" = true ] && [ -n "$fix" ]; then
        echo -e "  ${GREEN}Fix: ${fix}${NC}"
    fi
    echo ""
}

get_files() {
    if [ "$MODE" = "staged" ]; then
        git diff --cached --name-only --diff-filter=ACMR 2>/dev/null || true
    else
        git ls-files 2>/dev/null || true
    fi
}

# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------
echo ""
echo -e "${BOLD}========================================${NC}"
echo -e "${BOLD} TommyTalker Security Scanner${NC}"
echo -e "${BOLD}========================================${NC}"
echo -e " Mode: ${CYAN}${MODE}${NC}"
echo -e " Date: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# ---------------------------------------------------------------------------
# 1. API Keys & Secrets
# ---------------------------------------------------------------------------
echo -e "${BOLD}[1/7] Scanning for API keys and secrets...${NC}"

SECRET_PATTERNS=(
    'sk-[a-zA-Z0-9]{20,}'                           # OpenAI keys
    'sk-proj-[a-zA-Z0-9]{20,}'                      # OpenAI project keys
    'hf_[a-zA-Z0-9]{20,}'                           # HuggingFace tokens
    'AKIA[0-9A-Z]{16}'                               # AWS access key IDs
    'ghp_[a-zA-Z0-9]{36}'                            # GitHub personal tokens
    'gho_[a-zA-Z0-9]{36}'                            # GitHub OAuth tokens
    'github_pat_[a-zA-Z0-9_]{22,}'                   # GitHub fine-grained tokens
    'xox[bsp]-[a-zA-Z0-9\-]{10,}'                   # Slack tokens
    'AIza[0-9A-Za-z\-_]{35}'                         # Google API keys
    'BEGIN (RSA |DSA |EC )?PRIVATE KEY'              # PEM private keys
    'password\s*=\s*["\x27][^"\x27]{8,}["\x27]'     # Hardcoded passwords
    'secret\s*=\s*["\x27][^"\x27]{8,}["\x27]'       # Hardcoded secrets
)

while IFS= read -r file; do
    [[ "$file" =~ \.(png|jpg|jpeg|gif|ico|woff|ttf|eot|svg|pyc|so|db|sqlite)$ ]] && continue
    [ ! -f "$file" ] && continue
    [[ "$file" =~ ^tests/ ]] && continue
    [[ "$file" =~ security_scan\.sh$ ]] && continue

    for pattern in "${SECRET_PATTERNS[@]}"; do
        matches=$(grep -nEi "$pattern" "$file" 2>/dev/null | head -5 || true)
        if [ -n "$matches" ]; then
            if ! echo "$matches" | grep -qiE '(example|template|placeholder|your-key-here|CHANGE_ME)'; then
                finding "CRITICAL" "Secret/API Key" "$file" \
                    "Possible secret matching pattern: ${pattern:0:40}..." \
                    "Move to .env (gitignored) and load via os.getenv()"
            fi
        fi
    done
done < <(get_files)

# ---------------------------------------------------------------------------
# 2. Hardcoded User Paths
# ---------------------------------------------------------------------------
echo -e "${BOLD}[2/7] Scanning for hardcoded user paths...${NC}"

while IFS= read -r file; do
    [[ "$file" =~ \.(png|jpg|jpeg|gif|ico|woff|ttf|eot|svg|pyc|so|db|sqlite)$ ]] && continue
    [ ! -f "$file" ] && continue

    matches=$(grep -nE '/Users/[a-z][a-z0-9_.-]+/' "$file" 2>/dev/null \
        | grep -vE '(/Users/yourname/|/Users/user/|/Users/test/|\$HOME|Path\.home|os\.path\.expanduser|example|placeholder)' \
        | head -5 || true)

    if [ -n "$matches" ]; then
        finding "HIGH" "Hardcoded User Path" "$file" \
            "$(echo "$matches" | head -1)" \
            "Use Path.home(), \$HOME, or os.path.expanduser() instead"
    fi
done < <(get_files)

# ---------------------------------------------------------------------------
# 3. PII Patterns
# ---------------------------------------------------------------------------
echo -e "${BOLD}[3/7] Scanning for PII patterns...${NC}"

while IFS= read -r file; do
    [[ "$file" =~ \.(png|jpg|jpeg|gif|ico|woff|ttf|eot|svg|pyc|so|db|sqlite)$ ]] && continue
    [ ! -f "$file" ] && continue
    [[ "$file" =~ ^tests/ ]] && continue
    [[ "$file" =~ security_scan\.sh$ ]] && continue

    # SSN pattern
    matches=$(grep -nE '\b[0-9]{3}-[0-9]{2}-[0-9]{4}\b' "$file" 2>/dev/null \
        | grep -vE '(example|123-45-6789|000-00-0000|XXX-XX-XXXX|regex|pattern|detect|format|test)' \
        | head -3 || true)
    if [ -n "$matches" ]; then
        finding "CRITICAL" "Possible SSN" "$file" \
            "$(echo "$matches" | head -1)" \
            "Remove or replace with placeholder (XXX-XX-XXXX)"
    fi

    # Email addresses
    matches=$(grep -nEio '\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b' "$file" 2>/dev/null \
        | grep -viE '(example\.com|example\.org|test\.com|noreply@|placeholder|user@|john\.doe)' \
        | head -3 || true)
    if [ -n "$matches" ]; then
        finding "HIGH" "Real Email Address" "$file" \
            "$(echo "$matches" | head -1)" \
            "Replace with user@example.com"
    fi
done < <(get_files)

# ---------------------------------------------------------------------------
# 4. Internal Project References
# ---------------------------------------------------------------------------
echo -e "${BOLD}[4/7] Scanning for internal/private references...${NC}"

PRIVATE_TERMS_FILE="$PROJECT_ROOT/.security_terms"

if [ -f "$PRIVATE_TERMS_FILE" ]; then
    while IFS= read -r term; do
        [[ -z "$term" || "$term" =~ ^# ]] && continue

        while IFS= read -r file; do
            [[ "$file" =~ \.(png|jpg|jpeg|gif|ico|woff|ttf|eot|svg|pyc|so|db|sqlite)$ ]] && continue
            [ ! -f "$file" ] && continue
            [[ "$file" =~ security_scan\.sh$ ]] && continue
            [[ "$file" =~ \.security_terms$ ]] && continue

            matches=$(grep -niF "$term" "$file" 2>/dev/null | head -3 || true)
            if [ -n "$matches" ]; then
                finding "HIGH" "Private Reference" "$file" \
                    "Contains private term '${term}'" \
                    "Replace with generic language"
            fi
        done < <(get_files)
    done < "$PRIVATE_TERMS_FILE"
else
    echo -e "  ${YELLOW}No .security_terms file found. Create one to scan for private terms.${NC}"
fi

# ---------------------------------------------------------------------------
# 5. Sensitive Files
# ---------------------------------------------------------------------------
echo -e "${BOLD}[5/7] Checking for sensitive files that should be gitignored...${NC}"

SENSITIVE_FILES=(".env" ".env.local" "secrets.json" "credentials.json")

while IFS= read -r file; do
    basename=$(basename "$file")
    for sensitive in "${SENSITIVE_FILES[@]}"; do
        if [ "$basename" = "$sensitive" ]; then
            finding "CRITICAL" "Sensitive File Tracked" "$file" \
                "This file should be gitignored" \
                "Run: git rm --cached '$file'"
        fi
    done
done < <(get_files)

# ---------------------------------------------------------------------------
# 6. Database Files
# ---------------------------------------------------------------------------
echo -e "${BOLD}[6/7] Checking for database and log files...${NC}"

while IFS= read -r file; do
    case "$file" in
        *.db|*.sqlite|*.sqlite3)
            finding "HIGH" "Database File Tracked" "$file" \
                "Database files shouldn't be committed" \
                "Add to .gitignore"
            ;;
        *.log)
            finding "MEDIUM" "Log File Tracked" "$file" \
                "Log files may contain sensitive data" \
                "Add to .gitignore"
            ;;
    esac
done < <(get_files)

# ---------------------------------------------------------------------------
# 7. Dangerous Code Patterns
# ---------------------------------------------------------------------------
echo -e "${BOLD}[7/7] Scanning for dangerous code patterns...${NC}"

while IFS= read -r file; do
    [[ "$file" =~ \.(py)$ ]] || continue
    [ ! -f "$file" ] && continue

    # shell=True with subprocess
    matches=$(grep -nE 'subprocess\.(run|call|Popen).*shell\s*=\s*True' "$file" 2>/dev/null | head -3 || true)
    if [ -n "$matches" ]; then
        finding "HIGH" "Shell Injection Risk" "$file" \
            "$(echo "$matches" | head -1)" \
            "Use list args instead of shell=True"
    fi

    # verify=False on HTTPS
    matches=$(grep -nE 'verify\s*=\s*False' "$file" 2>/dev/null | head -3 || true)
    if [ -n "$matches" ]; then
        finding "MEDIUM" "SSL Verification Disabled" "$file" \
            "$(echo "$matches" | head -1)" \
            "Remove verify=False"
    fi
done < <(get_files)

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo -e "${BOLD}========================================${NC}"
if [ "$FINDINGS" -eq 0 ]; then
    echo -e "${GREEN}${BOLD} CLEAN - No security findings${NC}"
    echo -e "${BOLD}========================================${NC}"
    exit 0
else
    echo -e "${RED}${BOLD} FOUND ${FINDINGS} ISSUE(S)${NC}"
    echo -e "${BOLD}========================================${NC}"
    echo -e "Run with ${CYAN}--fix${NC} to see remediation suggestions."
    exit 1
fi
