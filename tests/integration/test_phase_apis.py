import requests

BASE = 'http://localhost:8001'


def test_phase_status_endpoints():
    paths = ['/api/phase3/status', '/api/phase4/status', '/api/v1/status']
    for p in paths:
        r = requests.get(f'http://localhost:8000{p}', timeout=5)
        assert r.status_code == 200, f"{p} returned {r.status_code}"


if __name__ == '__main__':
    test_phase_status_endpoints()
    print('ok')
