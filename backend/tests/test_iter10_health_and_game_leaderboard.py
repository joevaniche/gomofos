"""Iteration 10 tests:
- GET /api/health/time
- GET /api/games/{game_id}/leaderboard
"""
import os
import re
import pytest
import requests
from pathlib import Path


def _load_frontend_env():
    env = Path('/app/frontend/.env')
    if env.exists():
        for line in env.read_text().splitlines():
            m = re.match(r'^([A-Z_][A-Z0-9_]*)=(.*)$', line.strip())
            if m and m.group(1) not in os.environ:
                os.environ[m.group(1)] = m.group(2)


_load_frontend_env()
BASE_URL = os.environ['REACT_APP_BACKEND_URL'].rstrip('/')
USER_EMAIL = 'davidjovanic@yahoo.com.au'
USER_PASS = 'Andmay123'


@pytest.fixture(scope='module')
def user_session():
    s = requests.Session()
    s.headers.update({'Content-Type': 'application/json'})
    r = s.post(f'{BASE_URL}/api/auth/login', json={'email': USER_EMAIL, 'password': USER_PASS})
    if r.status_code != 200:
        pytest.skip(f'Login failed for {USER_EMAIL}: {r.status_code} {r.text}')
    return s


# ---- /api/health/time ----
class TestHealthTime:
    def test_health_time_unauthenticated(self):
        r = requests.get(f'{BASE_URL}/api/health/time')
        assert r.status_code == 200, r.text
        body = r.json()
        for key in ('server_time_utc', 'server_time_local', 'server_timezone', 'tz_offset_hours'):
            assert key in body, f'missing {key} in {body}'
        # Validate types
        assert isinstance(body['server_time_utc'], str) and 'T' in body['server_time_utc']
        assert isinstance(body['server_time_local'], str) and 'T' in body['server_time_local']
        assert isinstance(body['server_timezone'], str)
        assert isinstance(body['tz_offset_hours'], (int, float))


# ---- /api/games/{id}/leaderboard ----
class TestGameLeaderboard:
    @pytest.fixture(scope='class')
    def some_game_id(self, user_session):
        r = user_session.get(f'{BASE_URL}/api/games')
        assert r.status_code == 200, r.text
        games = r.json()
        if not games:
            pytest.skip('No games in catalog')
        return games[0]['id'], games[0].get('name')

    def test_leaderboard_valid_game(self, user_session, some_game_id):
        game_id, game_name = some_game_id
        r = user_session.get(f'{BASE_URL}/api/games/{game_id}/leaderboard')
        assert r.status_code == 200, r.text
        body = r.json()
        for key in ('game_id', 'game_name', 'platform', 'category', 'rows'):
            assert key in body, f'missing {key} in {body}'
        assert body['game_id'] == game_id
        assert body['game_name'] == game_name
        assert isinstance(body['rows'], list)
        # row contract
        for row in body['rows']:
            assert 'username' in row
            assert 'equipped_thumbs' in row and isinstance(row['equipped_thumbs'], list)
            assert 'wins' in row and 'losses' in row and 'net_credits' in row
            assert 'user_id' in row and 'total_matches' in row

    def test_leaderboard_invalid_game_id_404(self, user_session):
        # syntactically-valid ObjectId that doesn't exist
        r = user_session.get(f'{BASE_URL}/api/games/000000000000000000000000/leaderboard')
        assert r.status_code == 404, f'expected 404, got {r.status_code}: {r.text}'

    def test_leaderboard_malformed_game_id_404(self, user_session):
        r = user_session.get(f'{BASE_URL}/api/games/not-a-real-id/leaderboard')
        assert r.status_code == 404, f'expected 404, got {r.status_code}: {r.text}'

    def test_leaderboard_requires_auth(self):
        # without session cookie
        r = requests.get(f'{BASE_URL}/api/games/000000000000000000000000/leaderboard')
        assert r.status_code in (401, 403), f'expected auth required, got {r.status_code}'

    def test_leaderboard_sorted_by_wins_desc(self, user_session):
        # Find a game that has rows if possible
        games = user_session.get(f'{BASE_URL}/api/games').json()
        for g in games[:25]:
            body = user_session.get(f'{BASE_URL}/api/games/{g["id"]}/leaderboard').json()
            if len(body.get('rows', [])) >= 2:
                wins = [r['wins'] for r in body['rows']]
                assert wins == sorted(wins, reverse=True), f'rows not sorted desc by wins: {wins}'
                return
        pytest.skip('No game has >=2 leaderboard rows to verify sort')
