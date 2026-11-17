"""Test-only parent: spawns a PDEATHSIG child that spawns a grandchild."""

import asyncio
import json
import os
import sys

from dashboard.process import async_spawn_supervised_child

CHILD = (
    "import subprocess, sys, time\n"
    "g = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'])\n"
    "open(sys.argv[1], 'w').write(str(g.pid))\n"
    "time.sleep(120)\n"
)


async def main():
    pidfile = sys.argv[1]
    proc = await async_spawn_supervised_child(
        [sys.executable, "-c", CHILD, pidfile],
        lock_fd=None,
        cwd=os.getcwd(),
        env=dict(os.environ),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    print(json.dumps({"child": proc.pid}), flush=True)
    await asyncio.sleep(120)


asyncio.run(main())
