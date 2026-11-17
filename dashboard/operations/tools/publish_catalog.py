#!/usr/bin/env python3
"""Sanitize an authenticated T3 server.getConfig result from stdin; no network/provider calls.
Normally invoked by refresh_catalog.mjs after authenticated read-only discovery.
Stdin must be a full decoded server.getConfig result, never a truncated MCP response.
Output directory must already be owner-only (0700). Never persist raw config or credentials.
"""
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from dashboard.catalog_files import private_parent


def sanitize(config):
    providers = []
    for p in config['providers']:
        models = []
        for m in p['models']:
            options = []
            for o in (m.get('capabilities') or {}).get('optionDescriptors', []):
                options.append({'id': o['id'], 'values': [False, True] if o['type'] == 'boolean'
                    else [v['id'] for v in o['options']]})
            models.append({'id': m['slug'], 'label': m['name'], 'options': options,
                'sub_provider': m.get('subProvider'), 'is_custom': m.get('isCustom')})
        providers.append({'providerInstanceId': p['instanceId'], 'driverKind': p['driver'],
            'displayName': p.get('displayName'), 'enabled': p.get('enabled') is True,
            'available': p.get('availability') != 'unavailable' and p.get('installed') is True and p.get('status') not in ('error', 'disabled'),
            'authStatus': p.get('auth', {}).get('status', 'unknown'), 'checkedAt': p.get('checkedAt'), 'models': models})
    return {'source': 't3.server.getConfig', 'fetched_at': datetime.now(timezone.utc).isoformat(),
            'complete': True, 'providers': providers}


def main():
    doc = sanitize(json.load(sys.stdin))
    target = private_parent(sys.argv[1])
    fd, tmp = tempfile.mkstemp(dir=target.parent, prefix='.catalog-')
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(doc, f); f.flush(); os.fsync(f.fileno())
        os.replace(tmp, target)
        directory = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)


if __name__ == '__main__': main()
