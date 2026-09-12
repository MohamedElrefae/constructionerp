import shutil
import subprocess
import time
from pathlib import Path

from candidates import freeze, recheck
from core import WorkflowError, bytes_hash, utc, write_json
from sandbox import command

_CAN_UNSHARE_NET = None


def can_unshare_net():
    global _CAN_UNSHARE_NET
    if _CAN_UNSHARE_NET is None:
        binary = shutil.which("bwrap")
        if not binary:
            _CAN_UNSHARE_NET = False
        else:
            try:
                r = subprocess.run(
                    [binary, "--unshare-net", "--ro-bind", "/", "/", "true"],
                    capture_output=True,
                    timeout=5,
                )
                _CAN_UNSHARE_NET = (r.returncode == 0)
            except Exception:
                _CAN_UNSHARE_NET = False
    return _CAN_UNSHARE_NET


def run(spec, destination, deadline):
    if not can_unshare_net():
        raise WorkflowError("Network isolation unavailable: offline validation requires unshared network")
    candidate = freeze(
        spec["root"],
        spec["base_commit"],
        spec["branch"],
        spec["allowed_paths"],
        destination / "tested-candidate",
        spec["generated"],
    )
    records = []
    for index, argv in enumerate(spec.get("validation_commands", [])):
        if not isinstance(argv, list) or not argv or not all(isinstance(x, str) and x for x in argv):
            raise WorkflowError("Validation commands must be nonempty argv arrays")
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Job deadline reached before validation")
        start = utc()
        wrapped = command(
            argv,
            spec["root"],
            spec["work_item_root"],
            hidden_roots=[spec["control_root"], spec["work_item_root"]],
            writable_source=False,
        )
        wrapped.insert(1, "--unshare-net")
        write_json(
            destination / "validation-intent.json", {"index": index, "argv": argv, "started_utc": start}
        )
        with (
            (destination / ("validation-" + str(index) + ".stdout")).open("wb") as out,
            (destination / ("validation-" + str(index) + ".stderr")).open("wb") as err,
        ):
            p = subprocess.run(
                wrapped, cwd=spec["root"], stdin=subprocess.DEVNULL, stdout=out, stderr=err, timeout=remaining
            )
        records.append(
            {
                "argv": argv,
                "cwd": spec["root"],
                "started_utc": start,
                "finished_utc": utc(),
                "exit_code": p.returncode,
                "stdout_sha256": bytes_hash(
                    (destination / ("validation-" + str(index) + ".stdout")).read_bytes()
                ),
                "stderr_sha256": bytes_hash(
                    (destination / ("validation-" + str(index) + ".stderr")).read_bytes()
                ),
            }
        )
        write_json(
            destination / "validation.json",
            {"candidate_id": candidate["candidate_id"], "records": records, "complete": False},
        )
    recheck(spec["root"], candidate["manifest"], spec["generated"])
    result = {
        "candidate_id": candidate["candidate_id"],
        "records": records,
        "complete": True,
        "passed": bool(records) and all(r["exit_code"] == 0 for r in records),
    }
    write_json(destination / "validation.json", result)
    return result
