#!/usr/bin/env bash
# =============================================================================
#  Self-Referential Forge — Evolution Loop Automation
# =============================================================================
#  Starts the self-referential evolution loop with environment validation,
#  proper signal handling, auto-install, and optional dashboard launch.
#
#  Usage:
#    bash run_forge.sh                    # Infinite evolution
#    bash run_forge.sh --cycles 50        # 50 evolution cycles
#    bash run_forge.sh --dashboard        # Launch dashboard alongside
#    bash run_forge.sh --human-approval   # Manual approval per mutation
#    bash run_forge.sh --help             # Show help
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# ────────────────────────────────────────────────── Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

FORGE_PID=""
DASHBOARD_PID=""
EXTRA_ARGS=()

# ────────────────────────────────────────────────── Signal handling
cleanup() {
    echo -e "\n${YELLOW}Shutting down forge...${NC}"
    if [ -n "$FORGE_PID" ]; then
        kill "$FORGE_PID" 2>/dev/null || true
        wait "$FORGE_PID" 2>/dev/null || true
    fi
    if [ -n "$DASHBOARD_PID" ]; then
        kill "$DASHBOARD_PID" 2>/dev/null || true
    fi
    echo -e "${GREEN}Forge stopped.${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# ────────────────────────────────────────────────── Banner
print_banner() {
    echo -e "${CYAN}"
    echo "  ╔══════════════════════════════════════════════════════════╗"
    echo "  ║           Self-Referential Forge                         ║"
    echo "  ║   Darwin-style evolution of the forge's own components   ║"
    echo "  ╚══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# ────────────────────────────────────────────────── Help
show_help() {
    cat <<EOF
Usage: bash run_forge.sh [OPTIONS]

Options:
  --cycles N         Run N evolution cycles (default: infinite)
  --human-approval   Require manual approval per mutation
  --auto-commit      Auto-commit improvements to git
  --dashboard        Launch the real-time dashboard alongside the forge
  --apply            Apply mutations to forge's own .py files (self-referential)
  --safety-off       Disable safety validation (NOT RECOMMENDED)
  --verbose          Enable debug logging
  --help             Show this help message and exit

Examples:
  bash run_forge.sh                         # Infinite self-referential evolution
  bash run_forge.sh --cycles 50             # 50 evolution cycles
  bash run_forge.sh --dashboard             # Evolution + live dashboard
  bash run_forge.sh --human-approval        # Manual approval per mutation
EOF
    exit 0
}

# ────────────────────────────────────────────────── Parse arguments
parse_args() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --help) show_help ;;
            --cycles) EXTRA_ARGS+=("--cycles" "$2"); shift 2 ;;
            --human-approval) EXTRA_ARGS+=("--human-approval"); shift ;;
            --auto-commit) EXTRA_ARGS+=("--auto-commit"); shift ;;
            --dashboard) LAUNCH_DASHBOARD=1; shift ;;
            --safety-off) EXTRA_ARGS+=("--safety-off"); shift ;;
            --apply) EXTRA_ARGS+=("--apply"); shift ;;
            --verbose) EXTRA_ARGS+=("--verbose"); shift ;;
            *) echo -e "${RED}Unknown option: $1${NC}"; exit 1 ;;
        esac
    done
}

# ────────────────────────────────────────────────── Environment validation
check_env() {
    local missing=0

    # Load .env if present
    if [ -f .env ]; then
        set -a
        source .env
        set +a
    fi

    # Check Python
    if ! command -v python3 &>/dev/null; then
        echo -e "${RED}ERROR: python3 not found${NC}"
        missing=1
    fi

    # Check / validate package install
    if ! python3 -c "import forge" 2>/dev/null; then
        echo -e "${YELLOW}forge module not found — installing...${NC}"
        pip install -e . 2>/dev/null || {
            echo -e "${RED}ERROR: Failed to install dependencies${NC}"
            echo -e "  Try: ${BLUE}pip install -e .${NC}"
            missing=1
        }
    fi

    # Warn about LLM_API_KEY (optional for this forge, but useful)
    if [ -z "${LLM_API_KEY:-}" ]; then
        echo -e "${YELLOW}WARNING: LLM_API_KEY not set — LLM-dependent features disabled${NC}"
    fi

    return "$missing"
}

# ────────────────────────────────────────────────── Main
parse_args "$@"
print_banner

echo -e "${BLUE}Validating environment...${NC}"
if ! check_env; then
    echo -e "${RED}Environment validation failed. Exiting.${NC}"
    exit 1
fi
echo -e "${GREEN}Environment OK${NC}"

# Launch dashboard if requested
if [ "${LAUNCH_DASHBOARD:-0}" = "1" ]; then
    echo -e "${BLUE}Launching dashboard...${NC}"
    python3 -m uvicorn dashboard.main:app --host 0.0.0.0 --port "${DASHBOARD_PORT:-8000}" &
    DASHBOARD_PID=$!
    echo -e "${GREEN}Dashboard running on http://localhost:${DASHBOARD_PORT:-8000} (PID: $DASHBOARD_PID)${NC}"
fi

echo -e "${BLUE}Starting self-referential evolution loop...${NC}"
python3 -m forge "${EXTRA_ARGS[@]}" &
FORGE_PID=$!

echo -e "${GREEN}"
echo "  Forge is running (PID: $FORGE_PID)"
if [ "${LAUNCH_DASHBOARD:-0}" = "1" ]; then
    echo "  Dashboard: ${BLUE}http://localhost:${DASHBOARD_PORT:-8000}${GREEN}"
fi
echo -e "  Press Ctrl+C to stop.${NC}"

wait "$FORGE_PID"
