"""Launch the local API and optional production React build."""

from __future__ import annotations

import argparse
from pathlib import Path

import uvicorn

from mcp_traffic_analysis.api.app import create_app


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--agent-root", type=Path, default=Path("artifacts/phase3"))
    parser.add_argument("--behavior-root", type=Path, default=Path("artifacts/phase4"))
    parser.add_argument("--frontend-dist", type=Path, default=Path("frontend/dist"))
    parser.add_argument("--api-only", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    app = create_app(
        agent_root=args.agent_root,
        behavior_root=args.behavior_root,
        frontend_dist=args.frontend_dist,
        serve_frontend=not args.api_only,
    )
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
