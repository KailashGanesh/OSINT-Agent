#!/usr/bin/env bash
set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { printf "${GREEN}[✓]${NC} %s\n" "$*"; }
warn() { printf "${YELLOW}[!]${NC} %s\n" "$*"; }
fail() { printf "${RED}[✗]${NC} %s\n" "$*"; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

echo ""
echo "  OSINT Agent — Setup"
echo "  --------------------"
echo ""

# Detect platform
case "$(uname -s)" in
    Darwin)  OS="macos";;
    Linux)   OS="linux";;
    *)       fail "Unsupported OS: $(uname -s)";;
esac
log "Detected: $OS"

# Check Python
if ! command -v python3 &>/dev/null; then
    fail "python3 not found. Install Python 3.10+ first."
fi
PY_VER="$(python3 --version)"
PY_MAJOR=$(python3 -c 'import sys; print(sys.version_info[0])')
PY_MINOR=$(python3 -c 'import sys; print(sys.version_info[1])')
log "Found: $PY_VER"

# ── Create venv if missing ──
PIP="$VENV_DIR/bin/pip"
PYTHON="$VENV_DIR/bin/python"

if [ ! -d "$VENV_DIR" ]; then
    log "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

"$PIP" install --upgrade pip setuptools wheel -q
"$PIP" install -r "$SCRIPT_DIR/requirements.txt"

# ── theHarvester (needs Python ≥ 3.12) ──
HARVESTER_OK=0
if command -v theHarvester &>/dev/null; then
    log "theHarvester — found"
    HARVESTER_OK=1
elif [ "$PY_MAJOR" -ge 3 ] && [ "$PY_MINOR" -ge 12 ]; then
    warn "theHarvester not found — installing from PyPI..."
    "$PIP" install theHarvester 2>/dev/null && HARVESTER_OK=1 || warn "theHarvester install failed"
else
    warn "theHarvester requires Python ≥ 3.12 (you have $PY_VER) — skipped"
fi

# ── Verify CLI tools on PATH ──
for tool in sherlock holehe; do
    if command -v "$tool" &>/dev/null; then
        log "$tool — ready"
    else
        warn "$tool — not on PATH (it's inside .venv; activate with: source .venv/bin/activate)"
    fi
done

if [ "$HARVESTER_OK" -eq 1 ]; then
    if command -v theHarvester &>/dev/null; then
        log "theHarvester — ready"
    fi
fi

# Create .env if missing
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    cat > "$SCRIPT_DIR/.env" <<'EOF'
# ── API Provider (uncomment ONE section) ──

# OpenCode (default — free tier at opencode.ai/auth)
LLM_API_KEY=your-key-here
# LLM_MODEL=deepseek-v4-pro
# LLM_BASE_URL=https://opencode.ai/zen/go/v1

# OpenAI (alternative — platform.openai.com/api-keys)
# LLM_API_KEY=sk-your-key-here
# LLM_MODEL=gpt-5.4
# LLM_BASE_URL=https://api.openai.com/v1

# ── Optional ──
# HIBP_API_KEY=your-hibp-key-here
EOF
    warn ".env created — edit it to set your API key and provider"
fi

echo ""
log "Setup complete."
echo ""
echo "  To use the agent:"
echo "    1. source .venv/bin/activate"
echo "    2. Edit .env — uncomment your provider and set the key"
echo "       OpenCode: https://opencode.ai/auth"
echo "       OpenAI:   https://platform.openai.com/api-keys"
echo "    3. (optional) Set HIBP_API_KEY for breach checks"
echo '    4. python3 main.py --name "John Doe" --location "New York"'
echo ""
