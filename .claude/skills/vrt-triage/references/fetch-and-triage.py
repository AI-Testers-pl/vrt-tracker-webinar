#!/usr/bin/env python3
"""
Fetch unresolved runs from Visual Regression Tracker and prepare for triage.
Token is kept in memory only — never exposed to command line or shell history.
"""

import json
import os
import sys
import urllib.request
from datetime import datetime

API = os.environ.get('VRT_APIURL', 'http://localhost:4200').rstrip('/')
PROJECT = os.environ.get('VRT_PROJECT', 'AiTesters Gallery')
EMAIL = os.environ.get('VRT_EMAIL', 'visual-regression-tracker@example.com')
PASSWORD = os.environ.get('VRT_PASSWORD', '123456')
OUT = '/tmp/vrt-triage'

def call(path, token=None, payload=None, raw=False):
    """HTTP call to VRT API. Token never leaves this process."""
    req = urllib.request.Request(API + path, method='POST' if payload is not None else 'GET')
    if token:
        req.add_header('Authorization', 'Bearer ' + token)
    if payload is not None:
        req.add_header('Content-Type', 'application/json')
        req.data = json.dumps(payload).encode()
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read()
    return body if raw else (json.loads(body) if body else None)

try:
    # Cleanup and setup
    os.system(f'rm -rf {OUT} && mkdir -p {OUT}')

    # Login — token held in memory only
    token = call('/users/login', payload={'email': EMAIL, 'password': PASSWORD})['token']

    # Fetch project
    projects = call('/projects', token)
    project = next(p for p in projects if p['name'] == PROJECT)

    # Fetch latest build
    builds = call(f"/builds?projectId={project['id']}&take=1&skip=0", token)
    build = (builds if isinstance(builds, list) else builds['data'])[0]

    # Fetch unresolved runs
    runs = [r for r in call(f"/test-runs?buildId={build['id']}", token)
            if r['status'] == 'unresolved']

    print(f"Entries to triage: {len(runs)}\n")

    # Fetch images and metadata
    for i, r in enumerate(runs, 1):
        for role, key in (('baseline', 'baselineName'), ('actual', 'imageName'), ('diff', 'diffName')):
            if r.get(key):
                img_data = call(f"/images/{r[key]}", token, raw=True)
                open(f"{OUT}/{i}-{role}.png", 'wb').write(img_data)

        # Metadata
        tol = r.get('diffTollerancePercent', 0)
        c = r.get('comment') or ''

        print(f"[{i}] {r['name']}  status={r['status']}")
        print(f"    diff {r['diffPercent']:.3f}% against {tol}% tolerance")
        print(f"    {r.get('browser','?')} / {r.get('os','?')} / branch {r.get('branchName','?')}")
        print(f"    comment: {'(none)' if not c or c.startswith('[AI]') else c}")
        print(f"    images: {OUT}/{i}-baseline.png, -actual.png, -diff.png\n")

        # Save metadata JSON for Claude
        metadata = {
            'id': r['id'],
            'name': r['name'],
            'diffPercent': r['diffPercent'],
            'tolerance': tol,
            'browser': r.get('browser'),
            'os': r.get('os'),
            'branch': r.get('branchName'),
            'comment': c.replace('[AI]', '').strip() if c else '',
            'imagePaths': [f"{OUT}/{i}-{role}.png" for role in ['baseline', 'actual', 'diff'] if r.get(['baselineName', 'imageName', 'diffName'][['baseline', 'actual', 'diff'].index(role)])]
        }
        with open(f"{OUT}/{i}-metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)

    if runs:
        # Save run list for Claude
        with open(f"{OUT}/runs.json", 'w') as f:
            json.dump([{
                'index': i,
                'id': r['id'],
                'name': r['name'],
                'diffPercent': r['diffPercent'],
                'tolerance': r.get('diffTollerancePercent', 0),
                'browser': r.get('browser'),
                'os': r.get('os'),
                'branch': r.get('branchName')
            } for i, r in enumerate(runs, 1)], f, indent=2)

    print(f"✓ Fetched {len(runs)} entries to {OUT}")
    sys.exit(0)

except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
