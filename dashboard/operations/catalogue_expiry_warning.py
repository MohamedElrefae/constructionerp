#!/usr/bin/env python3
"""Metadata-only expiry warnings. No token file, T3 API, issuer or auth secret access."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile

ALLOWED = {'sessionId', 'method', 'scopes', 'expiresAt', 'last_rotation_report', 'superseded_session_pending_revocation'}
ROTATE = '/usr/bin/python3.12 -I -S ' + str(Path(__file__).resolve().with_name('rotate_catalogue_credential.py'))


def evaluate(metadata, now):
    if not isinstance(metadata, dict) or set(metadata) - ALLOWED:
        raise ValueError('Invalid metadata')
    if metadata.get('method') != 'bearer-access-token' or metadata.get('scopes') != ['orchestration:read']:
        raise ValueError('Wrong dedicated grant metadata')
    if not isinstance(metadata.get('expiresAt'), str):
        raise ValueError('Expiry string required')
    expiry = datetime.fromisoformat(metadata['expiresAt'].replace('Z', '+00:00'))
    if expiry.tzinfo is None:
        raise ValueError('Timezone required')
    seconds = (expiry - now).total_seconds()
    level = 'expired' if seconds <= 0 else 'urgent' if seconds <= 86400 else 'warning' if seconds <= 7 * 86400 else 'healthy'
    return {'level': level, 'expires_at': expiry.isoformat(), 'seconds_remaining': int(seconds),
            'action': 'Rotate the dedicated read-only credential before expiry with the documented operator command.',
            'rotation_command': ROTATE, 'automatic_renewal': False}


def private_path(value):
    p = Path(value)
    if not p.is_absolute() or '..' in p.parts or any(x.is_symlink() for x in [p, *p.parents]):
        raise ValueError('Unsafe path')
    parent = p.parent.stat()
    if parent.st_uid != os.getuid() or parent.st_mode & 0o077:
        raise ValueError('Private parent required')
    return p


def read_metadata(value):
    p = private_path(value)
    fd = os.open(p, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        st = os.fstat(stream.fileno())
        if not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid() or st.st_mode & 0o077 or st.st_nlink != 1 or st.st_size > 16384:
            raise ValueError('Unsafe metadata')
        return json.load(stream)


def atomic(path, doc):
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix='.expiry-')
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(doc, stream, indent=2); stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        Path(temp).unlink(missing_ok=True)


def notify(result, test=False):
    title = 'T3 catalogue reminder test' if test else 'T3 catalogue credential ' + result['level']
    text = ('Warning transport test. No credential or dashboard change.' if test else
            'Expires: ' + (result.get('expires_at') or 'metadata unavailable') + '\nRun the documented read-only credential rotation command.')
    try:
        done = subprocess.run(['/usr/bin/notify-send', '--app-name=T3 Dashboard Catalogue',
            '--urgency=' + ('critical' if result['level'] in ('urgent', 'expired', 'unknown') and not test else 'normal'),
            title, text], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=6)
        return done.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--metadata', required=True)
    parser.add_argument('--status-dir', required=True)
    parser.add_argument('--test-notification', action='store_true')
    args = parser.parse_args(argv)
    status_dir = Path(args.status_dir)
    if status_dir.is_symlink() or status_dir.stat().st_uid != os.getuid() or status_dir.stat().st_mode & 0o077:
        raise ValueError('Private status directory required')
    output = private_path(status_dir / 'status.json')
    now = datetime.now(timezone.utc)
    try:
        result = evaluate(read_metadata(args.metadata), now)
    except (OSError, ValueError, KeyError, TypeError):
        result = {'level': 'unknown', 'expires_at': None, 'automatic_renewal': False,
                  'action': 'Credential expiry metadata is unavailable/invalid. Inspect operator status; do not expose token values.',
                  'rotation_command': ROTATE}
    result['checked_at'] = now.isoformat()
    previous = {}
    try:
        previous = read_metadata(output)
    except (OSError, ValueError, TypeError):
        pass
    signature = [now.date().isoformat(), result['level'], result['expires_at']]
    result['notification_signature'] = previous.get('notification_signature')
    due = result['level'] != 'healthy' and previous.get('notification_signature') != signature
    if due or args.test_notification:
        delivered = notify(result, args.test_notification)
        result['notification_delivery'] = 'desktop service accepted' if delivered else 'unavailable; journal and private status retained'
        if delivered and not args.test_notification:
            result['notification_signature'] = signature
    else:
        result['notification_delivery'] = 'not due'
    atomic(output, result)
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception:
        print(json.dumps({'level': 'unknown', 'error': 'Expiry warning could not write private status; inspect this unit journal.'}))
        raise SystemExit(1)
