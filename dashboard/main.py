"""Real-time evolution dashboard for the self-referential forge.

FastAPI web application that exposes the current state of the
self-referential evolution loop — fitness trajectory, operator
weights, population stats, and archive history.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Self-Referential Forge Dashboard",
    description="Real-time visualization of the self-referential evolution loop",
    version="0.1.0",
)

ARCHIVE_DIR = Path(os.environ.get("FORGE_ARCHIVE_DIR", "archive/data"))
META_STATE_PATH = Path(os.environ.get("META_PATH", "meta_state.json"))


def _load_json(path: Path) -> dict[str, Any]:
    """Safely load a JSON file, returning empty dict on failure."""
    try:
        if path.exists():
            return json.loads(path.read_text())
    except Exception as exc:
        logger.debug("Could not load %s: %s", path, exc)
    return {}


def _load_archive() -> list[dict[str, Any]]:
    """Load archive snapshots from disk."""
    snapshots: list[dict[str, Any]] = []
    try:
        if ARCHIVE_DIR.exists():
            for fpath in sorted(ARCHIVE_DIR.glob("snapshot_*.json*"))[-50:]:
                try:
                    snapshots.append(_load_json(fpath))
                except Exception:
                    continue
    except Exception as exc:
        logger.debug("Could not load archive: %s", exc)
    return snapshots


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    """Serve the dashboard HTML."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Self-Referential Forge</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, -apple-system, sans-serif; background: #0d1117; color: #c9d1d9; padding: 2rem; }
  h1 { margin-bottom: 0.5rem; }
  .subtitle { color: #8b949e; margin-bottom: 2rem; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 1.5rem; }
  .card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 1.5rem; }
  .card h2 { font-size: 1.1rem; margin-bottom: 1rem; color: #58a6ff; }
  .stat-row { display: flex; justify-content: space-between; padding: 0.4rem 0; border-bottom: 1px solid #21262d; }
  .stat-row:last-child { border: none; }
  .stat-label { color: #8b949e; }
  .stat-value { font-weight: 600; font-variant-numeric: tabular-nums; }
  .positive { color: #3fb950; }
  .neutral { color: #d29922; }
  .negative { color: #f85149; }
  .mono { font-family: ui-monospace, monospace; font-size: 0.85rem; }
  .bar-container { background: #21262d; border-radius: 4px; height: 8px; margin: 0.5rem 0; }
  .bar-fill { background: #58a6ff; height: 8px; border-radius: 4px; transition: width 0.3s; }
  #refresh-note { text-align: center; color: #484f58; margin-top: 2rem; font-size: 0.85rem; }
  pre { background: #0d1117; padding: 1rem; border-radius: 6px; overflow-x: auto; font-size: 0.8rem; max-height: 300px; }
</style>
</head>
<body>
  <h1>🧬 Self-Referential Forge</h1>
  <p class="subtitle">Real-time dashboard — auto-refreshes every 5 seconds</p>
  <div class="grid" id="dashboard"></div>
  <p id="refresh-note">⏳ Loading...</p>

  <script>
    async function refresh() {
      try {
        const res = await fetch('/api/state');
        const data = await res.json();
        render(data);
        document.getElementById('refresh-note').textContent =
          '🔄 Auto-refreshing every 5s · Last update: ' + new Date().toLocaleTimeString();
      } catch (e) {
        document.getElementById('refresh-note').textContent = '⚠️ Could not reach forge';
      }
    }

    function render(data) {
      const meta = data.meta_state || {};
      const ops = meta.operators || meta.weights || {};
      const fits = data.fitness_history || [];
      const best = fits.length > 0 ? fits[fits.length - 1] : 0;
      const prev = fits.length > 1 ? fits[fits.length - 2] : best;
      const delta = (best - prev).toFixed(4);

      const html = `
        <div class="card">
          <h2>📊 Evolution Status</h2>
          <div class="stat-row"><span class="stat-label">Generation</span><span class="stat-value">${data.generation || 0}</span></div>
          <div class="stat-row"><span class="stat-label">Best Fitness</span><span class="stat-value">${best.toFixed(4)}</span></div>
          <div class="stat-row"><span class="stat-label">Last Delta</span><span class="stat-value ${delta > 0 ? 'positive' : delta < 0 ? 'negative' : 'neutral'}">${delta > 0 ? '+' : ''}${delta}</span></div>
          <div class="stat-row"><span class="stat-label">Population</span><span class="stat-value">${data.population_size || 0}</span></div>
          <div class="stat-row"><span class="stat-label">Failures</span><span class="stat-value ${(data.consecutive_failures || 0) > 3 ? 'negative' : ''}">${data.consecutive_failures || 0}</span></div>
          <div class="stat-row"><span class="stat-label">Mutation Rate</span><span class="stat-value">${(meta.mutation_rate || 0.8).toFixed(2)}</span></div>
          <div class="stat-row"><span class="stat-label">Crossover Rate</span><span class="stat-value">${(meta.crossover_rate || 0.2).toFixed(2)}</span></div>
        </div>
        <div class="card">
          <h2>🧬 Operator Weights</h2>
          ${Object.entries(ops).map(([op, w]) => {
            const weight = typeof w === 'number' ? w : (w.weight || w || 1);
            const pct = (weight / Math.max(...Object.values(ops).map(v => typeof v === 'number' ? v : (v.weight || v || 1)))) * 100;
            return `<div class="stat-row"><span class="stat-label mono">${op}</span><span class="stat-value">${typeof weight === 'number' ? weight.toFixed(2) : weight}</span></div>
                    <div class="bar-container"><div class="bar-fill" style="width:${Math.min(pct, 100)}%"></div></div>`;
          }).join('')}
        </div>
        <div class="card">
          <h2>📈 Fitness Trajectory</h2>
          <pre>${fits.length > 0 ? fits.map((f, i) => `#${String(i).padStart(3)}  ${f.toFixed(6)}`).slice(-30).join('\\n') : '(no data)'}</pre>
        </div>
        <div class="card">
          <h2>💾 Raw State</h2>
          <pre>${JSON.stringify(data, null, 2).slice(0, 2000)}</pre>
        </div>
      `;
      document.getElementById('dashboard').innerHTML = html;
    }

    setInterval(refresh, 5000);
    refresh();
  </script>
</body>
</html>"""


@app.get("/api/state")
async def api_state() -> JSONResponse:
    """Return the current evolution state."""
    state = _load_json(META_STATE_PATH.parent / "evolution_state.json")
    meta = _load_json(META_STATE_PATH)

    archive = _load_archive()
    if archive:
        latest = archive[-1]
        state.setdefault("generation", latest.get("generation", 0))
        state.setdefault("best_fitness", latest.get("best_fitness", 0.0))
        state.setdefault("population_size", latest.get("population_size", 0))
        state.setdefault("consecutive_failures", latest.get("consecutive_failures", 0))

    if "fitness_history" not in state or not state["fitness_history"]:
        state["fitness_history"] = [e.get("best_fitness", 0.0) for e in archive if "best_fitness" in e]

    state.setdefault("meta_state", meta)
    state.setdefault("generation", 0)
    state.setdefault("best_fitness", 0.0)
    state.setdefault("population_size", 0)
    state.setdefault("fitness_history", [])
    state.setdefault("consecutive_failures", 0)

    return JSONResponse(state)


@app.get("/health")
async def health() -> JSONResponse:
    """Health check endpoint."""
    return JSONResponse({"status": "ok"})


def main() -> None:
    """Run the dashboard server."""
    import uvicorn
    port = int(os.environ.get("DASHBOARD_PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    main()
