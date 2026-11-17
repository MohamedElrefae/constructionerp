"""Same-UID managed bridge fixture; only for the isolated simulator tests.

This fixture deliberately relaxes the production distinct-UID requirement so
the protocol can be exercised without privileged accounts. It is not evidence
of UID separation or permission to deploy the dispatcher.
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from managed_supervisor_service import ExperimentalManagedDispatcher  # noqa: E402
from _synthetic_supervisor_server import SyntheticWorkflowSupervisor  # noqa: E402


class SameUidFixture(ExperimentalManagedDispatcher):
    def _validate(self):
        if self.client_uid != os.geteuid() or self.uid != os.geteuid():
            raise RuntimeError("this fixture accepts only its own UID")
        if self.socket_path.parent.stat().st_uid != os.geteuid():
            raise RuntimeError("fixture socket parent must be owned by the test UID")


def main():
    parser = argparse.ArgumentParser()
    for name in ("socket", "state", "token-file", "base-url", "mcp-token-file", "model"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--allowed-model", action="append", default=[])
    parser.add_argument("--peer-uid", type=int, default=os.geteuid())
    args = parser.parse_args()
    token = Path(args.token_file).read_text().strip()
    core = SyntheticWorkflowSupervisor(
        socket_path=Path(args.socket), state_path=Path(args.state), token=token,
        base_url=args.base_url, mcp_token=Path(args.mcp_token_file).read_text().strip(),
        model=args.model, allowed_models=args.allowed_model or [args.model], peer_uid=args.peer_uid)
    service = SameUidFixture(core=core, socket_path=args.socket, token=token,
                             client_uid=args.peer_uid, socket_group_gid=os.getegid(),
                             attestation_verifier=lambda _path: True)
    try:
        service.start()
        print('{"ready": true}', flush=True)
        service.serve_forever()
    finally:
        service.close()


if __name__ == "__main__":
    main()
