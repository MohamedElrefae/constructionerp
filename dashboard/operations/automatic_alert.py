#!/usr/bin/env python3
"""Fail-closed operator alert for t3-dashboard-auto.service.

Reads only the private, reason-coded status document.  Best-effort local desktop
notification plus journal output; never reads tokens, credentials or task data and
never starts/stops a service.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def emit(message):
    print(message, file=sys.stderr, flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--status', required=True)
    p.add_argument('--unit', default='t3-dashboard-auto.service')
    a = p.parse_args()
    status_path = Path(a.status)
    try:
        status = json.loads(status_path.read_text())
    except (OSError, ValueError):
        status = {'phase': 'missing_or_unreadable', 'reason': 'status_document_unavailable'}
    phase = status.get('phase', 'unknown')
    reason = status.get('reason') or 'no_reason'
    action = status.get('operator_action') or (
        'Inspect the unit journal and preserve current dashboard state; do not force '
        'kill, restore old state or reset authentication.')
    message = (f'T3 dashboard automatic start {phase}: {reason}. '
               f'{action} Unit={a.unit}')
    emit(message)
    # Journal transport is always available for a user unit; desktop notification
    # is best-effort and depends on the local login session.
    if shutil.which('systemd-cat'):
        subprocess.run(['systemd-cat', '-t', 't3-dashboard-auto-alert'], input=message + '\n',
                       text=True, check=False)
    if os.environ.get('DBUS_SESSION_BUS_ADDRESS') and shutil.which('notify-send'):
        subprocess.run(['notify-send', '--urgency=critical', '--app-name=T3 dashboard',
                        'T3 dashboard automatic start blocked', message], check=False)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
