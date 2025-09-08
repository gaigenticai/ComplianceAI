#!/usr/bin/env python3
"""Fetch OpenAPI and GET all non-parameterized paths (smoke check).
Runs with only Python stdlib so it works inside the container.
"""
import json
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

BASE = 'http://127.0.0.1:8000'

try:
    data = urlopen(f"{BASE}/openapi.json", timeout=5).read().decode()
    api = json.loads(data)
except Exception as e:
    print('ERROR: failed to fetch openapi.json ->', e)
    raise SystemExit(2)

paths = sorted(api.get('paths', {}).keys())
print(f'Found {len(paths)} paths in OpenAPI')

skip_prefixes = ['/static', '/docs', '/redoc']

results = []
for p in paths:
    if '{' in p:
        results.append((p, 'SKIP_PARAM'))
        continue
    if any(p.startswith(pref) for pref in skip_prefixes):
        results.append((p, 'SKIP_STATIC'))
        continue
    url = BASE + p
    try:
        req = Request(url, method='GET')
        with urlopen(req, timeout=5) as r:
            results.append((p, r.getcode()))
    except HTTPError as he:
        results.append((p, he.code))
    except URLError as ue:
        results.append((p, f'ERROR:{ue}'))
    except Exception as e:
        results.append((p, f'ERROR:{e}'))

# Print summary
ok = [p for p,s in results if isinstance(s,int) and 200 <= s < 400]
fail = [p for p,s in results if not (isinstance(s,int) and 200 <= s < 400)]
print('\nResults:')
for p,s in results:
    print(f'{p} -> {s}')

print('\nSummary:')
print(f'  OK: {len(ok)}')
print(f'  SKIPPED/FAILED: {len(results)-len(ok)}')

# Exit non-zero if any real endpoints failed (exclude SKIP_ entries)
failed_real = [1 for p,s in results if not (isinstance(s,int) and 200<=s<400) and not str(s).startswith('SKIP')]
if failed_real:
    print('\nSome endpoints failed')
    raise SystemExit(1)

print('\nAll reachable GET endpoints returned 2xx/3xx')
