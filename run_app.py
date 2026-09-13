#!/usr/bin/env python3
"""Run the THREAD Application Server and Viewer."""

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.server import run_server

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="THREAD Web Application & Coordination Service")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port (default: 8000)")
    parser.add_argument("--db", default=None, help="SQLite database path for persistence (e.g. thread.db)")
    args = parser.parse_args()

    server = run_server(args.host, args.port, db_path=args.db)
    print(f"Open your browser to http://{args.host}:{args.port}/ to interact with the working path.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nTHREAD server stopped.")
        server.shutdown()
