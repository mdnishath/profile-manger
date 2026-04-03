"""
MailNexus Pro — License Revocation Manager (Admin Tool)

Automatically revokes licenses by updating your GitHub Gist.
Customer's app checks this Gist on startup and blocks revoked IDs.

Usage:
    python revoke_license.py --setup                # First time: set GitHub token
    python revoke_license.py --revoke 5             # Revoke license #5
    python revoke_license.py --revoke 1,3,7         # Revoke multiple
    python revoke_license.py --unrevoke 5           # Un-revoke
    python revoke_license.py --list                 # Show all revoked IDs
    python revoke_license.py --clear                # Clear all revocations
"""

import argparse
import json
import urllib.request
import urllib.error
from pathlib import Path

TOOLS_DIR = Path(__file__).parent
BLACKLIST_FILE = TOOLS_DIR / 'revoked_licenses.json'
CONFIG_FILE = TOOLS_DIR / 'gist_config.json'

# GitHub Gist API
GIST_API = 'https://api.github.com/gists'
GIST_FILENAME = 'revoked_licenses.json'


# ── Config (Gist ID + Token) ──────────────────────────────────────────────────

def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_config(cfg: dict) -> None:
    with open(CONFIG_FILE, 'w') as f:
        json.dump(cfg, f, indent=2)


def setup_gist():
    """Interactive setup: get GitHub token and Gist ID."""
    print('\n=== GitHub Gist Setup ===\n')
    print('You need a GitHub Personal Access Token with "gist" scope.')
    print('Create one at: https://github.com/settings/tokens/new')
    print('  - Select scope: "gist"')
    print('  - Click "Generate token"\n')

    token = input('Paste your GitHub token: ').strip()
    if not token:
        print('Error: Token cannot be empty')
        return

    cfg = load_config()
    cfg['github_token'] = token

    # Check if Gist already exists
    gist_id = cfg.get('gist_id', '')
    if gist_id:
        print(f'\nExisting Gist ID: {gist_id}')
        change = input('Keep this Gist? (y/n): ').strip().lower()
        if change != 'y':
            gist_id = ''

    if not gist_id:
        # Create a new Gist automatically
        print('\nCreating new Gist...')
        new_gist = _create_gist(token)
        if new_gist:
            cfg['gist_id'] = new_gist['id']
            cfg['raw_url'] = new_gist['raw_url']
            print(f'  Gist created: {new_gist["id"]}')
            print(f'  Raw URL: {new_gist["raw_url"]}')
            print(f'\n  IMPORTANT: Set this URL in licensing.py as BLACKLIST_URL:')
            print(f'  {new_gist["raw_url"]}')
        else:
            print('Error: Failed to create Gist. Check your token.')
            return

    save_config(cfg)
    print('\nSetup complete!')


def _create_gist(token: str) -> dict | None:
    """Create a new secret Gist with empty revoked list."""
    payload = json.dumps({
        'description': 'MailNexus Pro - Revoked Licenses',
        'public': False,
        'files': {
            GIST_FILENAME: {
                'content': json.dumps({'revoked': []}, indent=2)
            }
        }
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
            # Remove commit hash from raw_url for a "latest" URL
            # Format: https://gist.githubusercontent.com/USER/ID/raw/HASH/FILE
            # We want: https://gist.githubusercontent.com/USER/ID/raw/FILE
            parts = raw_url.split('/raw/')
            if len(parts) == 2:
                base = parts[0]
                # parts[1] = "HASH/FILE" -> extract just FILE
                file_part = parts[1].split('/', 1)[-1] if '/' in parts[1] else parts[1]
                raw_url = f'{base}/raw/{file_part}'
            return {'id': gist_id, 'raw_url': raw_url}
    except Exception as e:
        print(f'  API Error: {e}')
        return None


def _update_gist(data: dict) -> bool:
    """Push updated blacklist to GitHub Gist. Returns True on success."""
    cfg = load_config()
    token = cfg.get('github_token', '')
    gist_id = cfg.get('gist_id', '')

    if not token or not gist_id:
        print('\n  Error: Run --setup first to configure GitHub Gist')
        return False

    payload = json.dumps({
        'files': {
            GIST_FILENAME: {
                'content': json.dumps(data, indent=2)
            }
        }
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
                return True
    except urllib.error.HTTPError as e:
        print(f'  GitHub API Error: {e.code} {e.reason}')
        if e.code == 401:
            print('  Token expired or invalid. Run --setup again.')
    except Exception as e:
        print(f'  Error: {e}')

    return False


# ── Blacklist I/O ──────────────────────────────────────────────────────────────

def load_blacklist() -> dict:
    if BLACKLIST_FILE.exists():
        try:
            with open(BLACKLIST_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {'revoked': []}


def save_blacklist(data: dict) -> None:
    # Save locally
    with open(BLACKLIST_FILE, 'w') as f:
        json.dump(data, f, indent=2)

    # Push to GitHub Gist automatically
    print('  Updating GitHub Gist...', end=' ')
    if _update_gist(data):
        print('OK!')
        print('  Customer apps will be blocked on next startup.')
    else:
        print('FAILED')
        print('  Local file updated but Gist not synced.')
        print('  Run --setup to configure or check internet.')


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='MailNexus Pro - License Revocation Manager',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            'Examples:\n'
            '  python revoke_license.py --setup          # First time setup\n'
            '  python revoke_license.py --revoke 5       # Revoke license #5\n'
            '  python revoke_license.py --revoke 1,3,7   # Revoke multiple\n'
            '  python revoke_license.py --unrevoke 5     # Un-revoke\n'
            '  python revoke_license.py --list           # Show revoked IDs\n'
            '  python revoke_license.py --clear          # Clear all\n'
        )
    )
    parser.add_argument('--setup', action='store_true',
                        help='Setup GitHub Gist (first time)')
    parser.add_argument('--revoke', type=str, default=None,
                        help='License ID(s) to revoke (comma-separated)')
    parser.add_argument('--unrevoke', type=str, default=None,
                        help='License ID(s) to un-revoke (comma-separated)')
    parser.add_argument('--list', action='store_true',
                        help='List all revoked license IDs')
    parser.add_argument('--clear', action='store_true',
                        help='Clear all revocations')

    args = parser.parse_args()

    if args.setup:
        setup_gist()
        return

    data = load_blacklist()
    revoked = set(data.get('revoked', []))

    if args.list:
        if revoked:
            print(f'\nRevoked license IDs ({len(revoked)}):')
            for lid in sorted(revoked):
                print(f'  #{lid}')
        else:
            print('\nNo revoked licenses.')
        return

    if args.clear:
        data['revoked'] = []
        save_blacklist(data)
        print('\nAll revocations cleared.')
        return

    if args.revoke:
        ids = [int(x.strip()) for x in args.revoke.split(',')]
        for lid in ids:
            revoked.add(lid)
            print(f'  Revoked: License #{lid}')
        data['revoked'] = sorted(revoked)
        save_blacklist(data)
        return

    if args.unrevoke:
        ids = [int(x.strip()) for x in args.unrevoke.split(',')]
        for lid in ids:
            revoked.discard(lid)
            print(f'  Un-revoked: License #{lid}')
        data['revoked'] = sorted(revoked)
        save_blacklist(data)
        return

    parser.print_help()


if __name__ == '__main__':
    main()
