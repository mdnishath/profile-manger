"""
MailNexus Pro — Admin License Panel

A local web panel for managing licenses.
Run: python tools/admin_panel.py
Open: http://localhost:8500
"""

import json
import hmac
import hashlib
import urllib.request
import urllib.error
from datetime import date, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs

TOOLS_DIR = Path(__file__).parent
DB_FILE = TOOLS_DIR / 'license_db.json'
COUNTER_FILE = TOOLS_DIR / 'license_counter.txt'
BLACKLIST_FILE = TOOLS_DIR / 'revoked_licenses.json'
CONFIG_FILE = TOOLS_DIR / 'gist_config.json'

# License key constants (same as licensing.py)
ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
BASE = len(ALPHABET)
KEY_PREFIX = "MNX"
SECRET_KEY = b'f7a3d91c4e6b8205fa9c1d3e7b4a6082c5f8e1d9b3a7604c2e8f5d1a9b3c7e40'
EPOCH = date(2025, 1, 1)
GIST_API = 'https://api.github.com/gists'
GIST_FILENAME = 'revoked_licenses.json'
VERSION_MANIFEST_FILENAME = 'version_manifest.json'
VERSION_MANIFEST_FILE = TOOLS_DIR / 'version_manifest.json'

# Tier mapping (MUST match licensing.py)
TIER_VERSION = {'pro': 1, 'basic': 2}

PORT = 8500


# ── Key Generation (same as license_generator.py) ─────────────────────────────

def _bytes_to_int(data):
    r = 0
    for b in data:
        r = (r << 8) | b
    return r


def _int_to_bytes(n, length):
    r = []
    for _ in range(length):
        r.append(n & 0xFF)
        n >>= 8
    return bytes(reversed(r))


def _base31_encode(data, length=20):
    n = _bytes_to_int(data)
    chars = []
    for _ in range(length):
        chars.append(ALPHABET[n % BASE])
        n //= BASE
    return ''.join(reversed(chars))


def generate_key(license_id, days_valid, version=1):
    creation_day = (date.today() - EPOCH).days
    payload_int = (
        ((version & 0xF) << 44) |
        ((license_id & 0xFFFF) << 28) |
        ((days_valid & 0xFFF) << 16) |
        (creation_day & 0xFFFF)
    )
    payload_bytes = _int_to_bytes(payload_int, 6)
    mac = hmac.new(SECRET_KEY, payload_bytes, hashlib.sha256).digest()
    tag = mac[:6]
    raw = payload_bytes + tag
    chars = _base31_encode(raw, 20)
    return f"{KEY_PREFIX}-{chars[0:5]}-{chars[5:10]}-{chars[10:15]}-{chars[15:20]}"


# ── Data helpers ───────────────────────────────────────────────────────────────

def load_db():
    if DB_FILE.exists():
        try:
            return json.loads(DB_FILE.read_text())
        except Exception:
            pass
    return {'licenses': []}


def save_db(db):
    DB_FILE.write_text(json.dumps(db, indent=2))


def next_id():
    c = 0
    if COUNTER_FILE.exists():
        try:
            c = int(COUNTER_FILE.read_text().strip())
        except Exception:
            pass
    c += 1
    COUNTER_FILE.write_text(str(c))
    return c


def load_blacklist():
    if BLACKLIST_FILE.exists():
        try:
            return json.loads(BLACKLIST_FILE.read_text())
        except Exception:
            pass
    return {'revoked': []}


def save_blacklist(data):
    BLACKLIST_FILE.write_text(json.dumps(data, indent=2))


def load_version_manifest():
    if VERSION_MANIFEST_FILE.exists():
        try:
            return json.loads(VERSION_MANIFEST_FILE.read_text())
        except Exception:
            pass
    return {'latest_version': '3.0.0', 'download_url': '', 'release_date': '', 'changelog': []}


def save_version_manifest(data):
    VERSION_MANIFEST_FILE.write_text(json.dumps(data, indent=2))


def push_version_manifest_to_gist(data):
    """Push version_manifest.json as a second file in the same Gist."""
    cfg = load_gist_config()
    token = cfg.get('github_token', '')
    gist_id = cfg.get('gist_id', '')
    if not token or not gist_id:
        return False, 'Gist not configured'
    payload = json.dumps({
        'files': {VERSION_MANIFEST_FILENAME: {'content': json.dumps(data, indent=2)}}
    }).encode('utf-8')
    url = f'{GIST_API}/{gist_id}'
    req = urllib.request.Request(url, data=payload, method='PATCH', headers={
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json',
        'User-Agent': 'MailNexus-Pro-Admin',
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status == 200:
                # Extract raw URL for version manifest
                resp_data = json.loads(resp.read().decode('utf-8'))
                files = resp_data.get('files', {})
                if VERSION_MANIFEST_FILENAME in files:
                    raw_url = files[VERSION_MANIFEST_FILENAME].get('raw_url', '')
                    # Strip hash from URL for stable link
                    parts = raw_url.split('/raw/')
                    if len(parts) == 2:
                        file_part = parts[1].split('/', 1)[-1] if '/' in parts[1] else parts[1]
                        raw_url = f'{parts[0]}/raw/{file_part}'
                    cfg['version_manifest_url'] = raw_url
                    save_gist_config(cfg)
                return True, 'Version manifest synced'
    except urllib.error.HTTPError as e:
        return False, f'GitHub API Error: {e.code}'
    except Exception as e:
        return False, str(e)
    return False, 'Unknown error'


def load_gist_config():
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except Exception:
            pass
    return {}


def save_gist_config(cfg):
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))


def push_to_gist(data):
    cfg = load_gist_config()
    token = cfg.get('github_token', '')
    gist_id = cfg.get('gist_id', '')
    if not token or not gist_id:
        print(f'  [GIST] Not configured (token={bool(token)}, gist_id={gist_id})')
        return False, 'Gist not configured. Go to Settings tab.'
    print(f'  [GIST] Pushing to {gist_id}: {json.dumps(data)}')
    payload = json.dumps({
        'files': {GIST_FILENAME: {'content': json.dumps(data, indent=2)}}
    }).encode('utf-8')
    url = f'{GIST_API}/{gist_id}'
    req = urllib.request.Request(url, data=payload, method='PATCH', headers={
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json',
        'User-Agent': 'MailNexus-Pro-Admin',
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status == 200:
                print(f'  [GIST] OK - synced!')
                return True, 'Gist updated'
    except urllib.error.HTTPError as e:
        print(f'  [GIST] FAILED - HTTP {e.code}')
        return False, f'GitHub API Error: {e.code}'
    except Exception as e:
        print(f'  [GIST] FAILED - {e}')
        return False, str(e)
    return False, 'Unknown error'


def create_gist(token):
    payload = json.dumps({
        'description': 'MailNexus Pro - Revoked Licenses',
        'public': False,
        'files': {GIST_FILENAME: {'content': json.dumps({'revoked': []}, indent=2)}}
    }).encode('utf-8')
    req = urllib.request.Request(GIST_API, data=payload, method='POST', headers={
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json',
        'User-Agent': 'MailNexus-Pro-Admin',
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            gist_id = data['id']
            raw_url = data['files'][GIST_FILENAME]['raw_url']
            parts = raw_url.split('/raw/')
            if len(parts) == 2:
                file_part = parts[1].split('/', 1)[-1] if '/' in parts[1] else parts[1]
                raw_url = f'{parts[0]}/raw/{file_part}'
            return {'id': gist_id, 'raw_url': raw_url}
    except Exception as e:
        return None


# ── HTTP Handler ───────────────────────────────────────────────────────────────

class AdminHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        print(f'  [{self.command}] {self.path}')

    def _respond(self, code, body, content_type='application/json'):
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        if isinstance(body, str):
            body = body.encode('utf-8')
        self.wfile.write(body)

    def _json(self, data, code=200):
        self._respond(code, json.dumps(data))

    def _read_body(self):
        length = int(self.headers.get('Content-Length', 0))
        return json.loads(self.rfile.read(length)) if length else {}

    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            html_path = TOOLS_DIR / 'admin_panel.html'
            if html_path.exists():
                self._respond(200, html_path.read_text('utf-8'), 'text/html')
            else:
                self._respond(404, 'admin_panel.html not found', 'text/plain')

        elif self.path == '/api/licenses':
            db = load_db()
            bl = load_blacklist()
            revoked = set(bl.get('revoked', []))
            for lic in db.get('licenses', []):
                lic['revoked'] = lic['id'] in revoked
                if lic.get('days', 0) > 0:
                    try:
                        created = date.fromisoformat(lic['created'])
                        expiry = created + timedelta(days=lic['days'])
                        lic['expiry'] = expiry.isoformat()
                        lic['expired'] = date.today() > expiry
                    except Exception:
                        lic['expiry'] = '?'
                        lic['expired'] = False
                else:
                    lic['expiry'] = 'Lifetime'
                    lic['expired'] = False
            self._json(db)

        elif self.path == '/api/blacklist':
            self._json(load_blacklist())

        elif self.path == '/api/gist-status':
            cfg = load_gist_config()
            self._json({
                'configured': bool(cfg.get('github_token') and cfg.get('gist_id')),
                'gist_id': cfg.get('gist_id', ''),
                'raw_url': cfg.get('raw_url', ''),
            })

        elif self.path == '/api/version-manifest':
            self._json(load_version_manifest())

        else:
            self._respond(404, '{"error":"not found"}')

    def do_POST(self):
        if self.path == '/api/generate':
            body = self._read_body()
            days = int(body.get('days', 30))
            count = int(body.get('count', 1))
            tier = body.get('tier', 'pro').lower()
            if tier not in TIER_VERSION:
                tier = 'pro'
            if days < 0 or days > 4095:
                self._json({'error': 'Days must be 0-4095'}, 400)
                return
            if count < 1 or count > 50:
                self._json({'error': 'Count must be 1-50'}, 400)
                return

            version = TIER_VERSION[tier]
            db = load_db()
            generated = []
            for _ in range(count):
                lid = next_id()
                key = generate_key(lid, days, version=version)
                entry = {
                    'id': lid,
                    'key': key,
                    'days': days,
                    'tier': tier,
                    'created': date.today().isoformat(),
                }
                db['licenses'].append(entry)
                generated.append(entry)
            save_db(db)
            self._json({'success': True, 'generated': generated})

        elif self.path == '/api/revoke':
            body = self._read_body()
            lid = int(body.get('id', 0))
            bl = load_blacklist()
            revoked = set(bl.get('revoked', []))
            revoked.add(lid)
            bl['revoked'] = sorted(revoked)
            save_blacklist(bl)
            ok, msg = push_to_gist(bl)
            self._json({'success': True, 'synced': ok, 'message': msg})

        elif self.path == '/api/unrevoke':
            body = self._read_body()
            lid = int(body.get('id', 0))
            bl = load_blacklist()
            revoked = set(bl.get('revoked', []))
            revoked.discard(lid)
            bl['revoked'] = sorted(revoked)
            save_blacklist(bl)
            ok, msg = push_to_gist(bl)
            self._json({'success': True, 'synced': ok, 'message': msg})

        elif self.path == '/api/delete-license':
            body = self._read_body()
            lid = int(body.get('id', 0))
            db = load_db()
            db['licenses'] = [l for l in db['licenses'] if l['id'] != lid]
            save_db(db)
            self._json({'success': True})

        elif self.path == '/api/setup-gist':
            body = self._read_body()
            token = body.get('token', '').strip()
            gist_id = body.get('gist_id', '').strip()
            if not token:
                self._json({'error': 'Token required'}, 400)
                return
            cfg = load_gist_config()
            cfg['github_token'] = token
            # Use provided gist_id, or existing one, or create new
            if gist_id:
                cfg['gist_id'] = gist_id
                cfg['raw_url'] = f'https://gist.githubusercontent.com/mdnishath/{gist_id}/raw/{GIST_FILENAME}'
            elif not cfg.get('gist_id'):
                result = create_gist(token)
                if result:
                    cfg['gist_id'] = result['id']
                    cfg['raw_url'] = result['raw_url']
                else:
                    self._json({'error': 'Failed to create Gist. Check token.'}, 400)
                    return
            save_gist_config(cfg)
            # Test connection by pushing current blacklist
            bl = load_blacklist()
            ok, msg = push_to_gist(bl)
            self._json({
                'success': True,
                'gist_id': cfg['gist_id'],
                'raw_url': cfg.get('raw_url', ''),
                'synced': ok,
                'sync_msg': msg,
            })

        elif self.path == '/api/sync-gist':
            bl = load_blacklist()
            print(f'  [SYNC] Manual sync: {bl}')
            ok, msg = push_to_gist(bl)
            self._json({
                'success': True,
                'synced': ok,
                'message': msg,
                'revoked': bl.get('revoked', []),
            })

        elif self.path == '/api/update-version-manifest':
            body = self._read_body()
            version = body.get('latest_version', '').strip()
            download_url = body.get('download_url', '').strip()
            release_date = body.get('release_date', '').strip()
            change_type = body.get('type', 'patch').strip()
            changes = body.get('changes', [])
            migration = body.get('migration', '').strip()

            if not version:
                self._json({'error': 'Version is required'}, 400)
                return

            manifest = load_version_manifest()
            manifest['latest_version'] = version
            if download_url:
                manifest['download_url'] = download_url
            if release_date:
                manifest['release_date'] = release_date

            # Add changelog entry (prepend so newest is first)
            entry = {
                'version': version,
                'date': release_date or date.today().isoformat(),
                'type': change_type,
                'changes': changes if changes else [],
                'migration': migration,
            }
            # Replace if same version exists, else prepend
            existing = [i for i, c in enumerate(manifest.get('changelog', [])) if c.get('version') == version]
            if existing:
                manifest['changelog'][existing[0]] = entry
            else:
                manifest.setdefault('changelog', []).insert(0, entry)

            save_version_manifest(manifest)

            # Push to Gist
            ok, msg = push_version_manifest_to_gist(manifest)
            self._json({
                'success': True,
                'synced': ok,
                'message': msg,
                'manifest': manifest,
            })

        else:
            self._respond(404, '{"error":"not found"}')

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()


def main():
    server = HTTPServer(('127.0.0.1', PORT), AdminHandler)
    print(f'\n  MailNexus Pro - Admin License Panel')
    print(f'  Open: http://localhost:{PORT}')
    print(f'  Press Ctrl+C to stop\n')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nStopped.')
        server.server_close()


if __name__ == '__main__':
    main()
