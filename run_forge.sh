#!/usr/bin/env bash
set -euo pipefail

# Self-Referential Forge — bash automation wrapper
# Launches the evolution loop with optional dashboard.

FORGE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="${FORGE_DIR}:${PYTHONPATH:-}"

# Source .env if present
if [ -f "${FORGE_DIR}/.env" ]; then
    set -a
    source "${FORGE_DIR}/.env"
    set +a
fi

DASHBOARD="${DASHBOARD:-false}"
CYCLES="${CYCLES:--1}"

echo "=== Self-Referential Forge ==="
echo "Cycles: ${CYCLES}"
echo "Dashboard: ${DASHBOARD}"
echo ""

if [ "${DASHBOARD}" = "true" ]; then
    echo "Starting dashboard on http://0.0.0.0:8080 ..."
    python -m uvicorn dashboard.main:app --host 0.0.0.0 --port 8080 &
    DASH_PID=$!
    trap "kill ${DASH_PID} 2>/dev/null" EXIT
fi

python -c "
import asyncio
from forge.orchestrator import SelfReferentialOrchestrator, EvolutionConfig

async def main():
    config = EvolutionConfig()
    orchestrator = SelfReferentialOrchestrator(config=config)
    await orchestrator.run(cycles=${CYCLES})

asyncio.run(main())
"
