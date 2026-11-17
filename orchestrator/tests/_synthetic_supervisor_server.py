"""Test-owned supervisor process used only with the local MCP simulator."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from t3_supervisor import Supervisor, serve  # noqa: E402


class SyntheticWorkflowSupervisor(Supervisor):
    # The production supervisor class has no builder-enabling CLI or env flag.
    allow_builder_for_tests = True


def main():
    import argparse

    parser = argparse.ArgumentParser()
    for name in ("socket", "state", "token-file", "base-url", "mcp-token-file", "model"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--allowed-model", action="append", default=[])
    parser.add_argument("--peer-uid", type=int, default=None)
    args = parser.parse_args()
    supervisor = SyntheticWorkflowSupervisor(
        socket_path=Path(args.socket), state_path=Path(args.state),
        token=Path(args.token_file).read_text().strip(), base_url=args.base_url,
        mcp_token=Path(args.mcp_token_file).read_text().strip(), model=args.model,
        allowed_models=args.allowed_model or [args.model], peer_uid=args.peer_uid)
    serve(supervisor)


if __name__ == "__main__":
    main()
