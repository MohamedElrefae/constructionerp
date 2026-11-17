"""Run the deterministic MCP simulator as a separate process (test-only)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _mcp_sim import SimServer, SimState


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--token", required=True)
    parser.add_argument("--fail", default=None)
    parser.add_argument("--events", default=None)
    parser.add_argument("--delay", type=float, default=0.0)
    parser.add_argument(
        "--legacy-marker-mode",
        action="store_true",
        help="test-only low-level protocol fixture; emits marker-only assistant text",
    )
    args = parser.parse_args()
    state = SimState(
        token=args.token, fail=args.fail, delay=args.delay, legacy_marker_mode=args.legacy_marker_mode
    )
    state.event_file = args.events
    server = SimServer(state)
    server.__enter__()
    print(json.dumps({"ready": True, "url": server.url, "pid": __import__("os").getpid()}), flush=True)
    try:
        server.thread.join()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
