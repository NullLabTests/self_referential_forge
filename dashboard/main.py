"""FastAPI-based dashboard for real-time self-referential evolution monitoring.

Serves fitness charts, population stats, and operator usage heatmaps
via a lightweight HTTP server.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, Response
from fastapi.responses import HTMLResponse

logger = logging.getLogger(__name__)

app = FastAPI(title="Self-Referential Forge Dashboard")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/")
async def index() -> HTMLResponse:
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Self-Referential Forge</title></head>
    <body>
      <h1>Self-Referential Forge Dashboard</h1>
      <p>Monitoring evolution in real time.</p>
      <ul>
        <li><a href="/health">Health</a></li>
        <li><a href="/state">State</a></li>
      </ul>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.get("/state")
async def state() -> dict[str, Any]:
    return {"status": "dashboard initialized", "forges": []}


class DashboardApp:
    """Wrapper to start the dashboard server programmatically."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8080) -> None:
        self.host = host
        self.port = port

    def run(self) -> None:
        uvicorn.run(app, host=self.host, port=self.port)
