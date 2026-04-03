"""
licensing.py — Offline license validation engine for MailNexus Pro.

Encodes/decodes license keys in MNX-XXXXX-XXXXX-XXXXX-XXXXX format,
generates machine fingerprints from WMI, and handles activation/validation.

No external dependencies — uses only Python standard library.
"""

import hmac
import hashlib
import subprocess
import json
import os
import time
import urllib.request
import threading
from datetime import date, timedelta
from pathlib import Path

# ── Constants ──────────────────────────────────────────────────────────────────

# Base31 alphabet — avoids confusing chars (0/O, 1/I/L)
ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
BASE = len(ALPHABET)  # 31

KEY_PREFIX = "MNX"
KEY_VERSION = 1

# ── License Tiers ────────────────────────────────────────────────────────────
# Encoded in the 4-bit `version` field of the license key.
# version=1 → Pro (backward compat: all existing keys stay Pro)
# version=2 → Basic (Steps 1-2 only)
TIER_MAP = {1: 'pro', 2: 'basic'}
TIER_STEPS = {'pro': [1, 2, 3, 4], 'basic': [1, 2]}

# Shared secret for HMAC signing — MUST match tools/license_generator.py
SECRET_KEY = b'f7a3d91c4e6b8205fa9c1d3e7b4a6082c5f8e1d9b3a7604c2e8f5d1a9b3c7e40'

# Epoch for creation_day field (days since this date)
EPOCH = date(2025, 1, 1)

# Online blacklist URL — GitHub Gist raw URL
# Set this to your Gist raw URL after creating it
# Format: {"revoked": [1, 5, 12]}  (list of revoked license IDs)
BLACKLIST_URL = 'https://gist.githubusercontent.com/mdnishath/4781b52137098ddced727568fa31be7a/raw/revoked_licenses.json'
BLACKLIST_TIMEOUT = 2  # seconds

# Cache for blacklist (refreshes every 5 minutes)
BLACKLIST_REFRESH = 300  # seconds
_blacklist_cache = {'last_check': 0, 'revoked': set()}

# ── Base31 Encode / Decode ─────────────────────────────────────────────────────


def _bytes_to_int(data: bytes) -> int:
    """Convert bytes to a big-endian integer."""
    result = 0
    for b in data:
        result = (result << 8) | b
    return result


def _int_to_bytes(n: int, length: int) -> bytes:
    """Convert integer to big-endian bytes of given length."""
    result = []
    for _ in range(length):
        result.append(n & 0xFF)
        n >>= 8
    return bytes(reversed(result))


def _base31_encode(data: bytes, length: int = 20) -> str:
    """Encode bytes to Base31 string of fixed length."""
    n = _bytes_to_int(data)
    chars = []
    for _ in range(length):
        chars.append(ALPHABET[n % BASE])
        n //= BASE
    return ''.join(reversed(chars))


def _base31_decode(s: str) -> int:
    """Decode Base31 string back to integer."""
    n = 0
    for ch in s:
        idx = ALPHABET.find(ch)
        if idx < 0:
            raise ValueError(f"Invalid character in license key: {ch}")
        n = n * BASE + idx
    return n


# ── Key Encoding / Decoding ───────────────────────────────────────────────────

def format_license_key(version: int, license_id: int, days_valid: int,
                       creation_date: date) -> str:
    """Encode license fields into MNX-XXXXX-XXXXX-XXXXX-XXXXX format.

    Payload (6 bytes = 48 bits):
        version     :  4 bits  (0-15)
        license_id  : 16 bits  (0-65535)
        days_valid  : 12 bits  (0-4095)
        creation_day: 16 bits  (days since EPOCH)
    HMAC tag (6 bytes = 48 bits): truncated HMAC-SHA256 of payload

    Total: 12 bytes → encoded as 20 Base31 chars.
    """
    creation_day = (creation_date - EPOCH).days
    if creation_day < 0:
        raise ValueError("Creation date cannot be before epoch (2025-01-01)")

    # Pack 48-bit payload
    payload_int = (
        ((version & 0xF) << 44) |
        ((license_id & 0xFFFF) << 28) |
        ((days_valid & 0xFFF) << 16) |
        (creation_day & 0xFFFF)
    )
    payload_bytes = _int_to_bytes(payload_int, 6)

    # HMAC-SHA256, take first 6 bytes
    mac = hmac.new(SECRET_KEY, payload_bytes, hashlib.sha256).digest()
    tag = mac[:6]

    # Combine: 6 + 6 = 12 bytes
    raw = payload_bytes + tag
    chars = _base31_encode(raw, 20)

    return f"{KEY_PREFIX}-{chars[0:5]}-{chars[5:10]}-{chars[10:15]}-{chars[15:20]}"


def parse_license_key(key_str: str) -> dict | None:
    """Decode and verify a license key.

    Returns dict with fields on success, None on failure.
    """
    # Normalize: uppercase, strip whitespace
    key_str = key_str.strip().upper()

    # Remove prefix
    if key_str.startswith(KEY_PREFIX + '-'):
        key_str = key_str[len(KEY_PREFIX) + 1:]

    # Remove dashes
    chars = key_str.replace('-', '')

    if len(chars) != 20:
        return None

    # Validate characters
    for ch in chars:
        if ch not in ALPHABET:
            return None

    try:
        raw_int = _base31_decode(chars)
    except ValueError:
        return None

    raw_bytes = _int_to_bytes(raw_int, 12)
    payload_bytes = raw_bytes[:6]
    tag_received = raw_bytes[6:]

    # Verify HMAC
    mac = hmac.new(SECRET_KEY, payload_bytes, hashlib.sha256).digest()
    tag_expected = mac[:6]

    if not hmac.compare_digest(tag_received, tag_expected):
        return None

    # Unpack payload
    payload_int = _bytes_to_int(payload_bytes)
    version = (payload_int >> 44) & 0xF
    license_id = (payload_int >> 28) & 0xFFFF
    days_valid = (payload_int >> 16) & 0xFFF
    creation_day = payload_int & 0xFFFF

    creation_date = EPOCH + timedelta(days=creation_day)

    return {
        'version': version,
        'license_id': license_id,
        'days_valid': days_valid,
        'creation_date': creation_date.isoformat(),
        'creation_day': creation_day,
        'tier': TIER_MAP.get(version, 'basic'),
    }


# ── Machine ID ─────────────────────────────────────────────────────────────────

def get_machine_id() -> str:
    """Generate a deterministic 32-char hex machine fingerprint from WMI."""
    components = []
    queries = [
        ('wmic baseboard get serialnumber', 'BOARD'),
        ('wmic cpu get processorid', 'CPU'),
        ('wmic bios get serialnumber', 'BIOS'),
        ('wmic diskdrive where Index=0 get SerialNumber', 'DISK'),
    ]

    for cmd, label in queries:
        try:
            out = subprocess.check_output(
                cmd, shell=True, timeout=10, stderr=subprocess.DEVNULL
            )
            lines = out.decode('utf-8', errors='ignore').strip().split('\n')
            # WMI output: first line is header, second line is value
            val = lines[-1].strip() if len(lines) > 1 else ''
            if val and val.lower() not in ('', 'to be filled by o.e.m.',
                                           'default string', 'none'):
                components.append(f"{label}:{val}")
        except Exception:
            pass

    if not components:
        # Fallback: hostname + username
        import platform
        fallback = f"HOST:{platform.node()}|USER:{os.getenv('USERNAME', 'unknown')}"
        components.append(fallback)

    components.sort()
    raw = '|'.join(components)
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()[:32]


# ── Online Blacklist Check ─────────────────────────────────────────────────────

def _fetch_blacklist() -> set:
    """Fetch revoked license IDs from online blacklist (GitHub Gist).
    Returns set of revoked license IDs. Cached for BLACKLIST_REFRESH seconds."""
    now = time.time()
    if now - _blacklist_cache['last_check'] < BLACKLIST_REFRESH:
        return _blacklist_cache['revoked']

    _blacklist_cache['last_check'] = now

    if not BLACKLIST_URL:
        return set()

    try:
        req = urllib.request.Request(BLACKLIST_URL, headers={
            'User-Agent': 'MailNexus-Pro/1.0',
            'Cache-Control': 'no-cache',
        })
        with urllib.request.urlopen(req, timeout=BLACKLIST_TIMEOUT) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            revoked = set(data.get('revoked', []))
            _blacklist_cache['revoked'] = revoked
            return revoked
    except Exception:
        # Offline or URL not set — skip blacklist check
        return _blacklist_cache['revoked']


def is_license_revoked(license_id: int) -> bool:
    """Check if a license ID is in the online blacklist."""
    revoked = _fetch_blacklist()
    return license_id in revoked


def check_blacklist_async():
    """Pre-fetch blacklist in background thread on app startup."""
    if BLACKLIST_URL:
        t = threading.Thread(target=_fetch_blacklist, daemon=True)
        t.start()


# ── License File I/O ───────────────────────────────────────────────────────────

def _get_license_path(resources_path: Path) -> Path:
    return resources_path / 'config' / 'license.json'


def _compute_integrity_hash(data: dict) -> str:
    """SHA256 of key fields + secret to detect tampering."""
    payload = (
        data.get('license_key', '') +
        data.get('machine_id', '') +
        data.get('activation_date', '') +
        data.get('expiry_date', '') +
        str(data.get('license_id', '')) +
        SECRET_KEY.decode('utf-8')
    )
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def load_license(resources_path: Path) -> dict | None:
    """Load license.json, return dict or None."""
    p = _get_license_path(resources_path)
    if not p.exists():
        return None
    try:
        with open(p, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError, OSError):
        return None


def save_license(resources_path: Path, data: dict) -> None:
    """Write license.json with integrity hash."""
    data['integrity_hash'] = _compute_integrity_hash(data)
    p = _get_license_path(resources_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def delete_license(resources_path: Path) -> bool:
    """Delete license.json. Returns True if deleted."""
    p = _get_license_path(resources_path)
    if p.exists():
        p.unlink()
        return True
    return False


# ── Validation ─────────────────────────────────────────────────────────────────

def validate_license(resources_path: Path) -> dict:
    """Full license validation.

    Returns:
        {
            'valid': bool,
            'error': None | str,
            'expiry_date': str | None,
            'days_remaining': int | None,
            'license_id': int | None,
        }
    """
    lic = load_license(resources_path)

    if lic is None:
        return {'valid': False, 'error': 'not_activated',
                'expiry_date': None, 'days_remaining': None, 'license_id': None}

    # Check integrity hash
    expected_hash = _compute_integrity_hash(lic)
    if lic.get('integrity_hash') != expected_hash:
        return {'valid': False, 'error': 'tampered',
                'expiry_date': None, 'days_remaining': None, 'license_id': None}

    # Re-verify the license key HMAC
    key_data = parse_license_key(lic.get('license_key', ''))
    if key_data is None:
        return {'valid': False, 'error': 'invalid_key',
                'expiry_date': None, 'days_remaining': None, 'license_id': None}

    # Check machine ID
    current_machine = get_machine_id()
    if lic.get('machine_id') != current_machine:
        return {'valid': False, 'error': 'wrong_machine',
                'expiry_date': lic.get('expiry_date'),
                'days_remaining': None, 'license_id': key_data['license_id']}

    # Check online blacklist (revoked licenses)
    if is_license_revoked(key_data['license_id']):
        return {'valid': False, 'error': 'revoked',
                'expiry_date': lic.get('expiry_date'),
                'days_remaining': 0, 'license_id': key_data['license_id']}

    # Check expiry (days_valid=0 means lifetime)
    expiry_str = lic.get('expiry_date')
    if key_data['days_valid'] > 0 and expiry_str:
        today = date.today()
        try:
            expiry = date.fromisoformat(expiry_str)
        except ValueError:
            return {'valid': False, 'error': 'tampered',
                    'expiry_date': expiry_str, 'days_remaining': None,
                    'license_id': key_data['license_id']}
        days_remaining = (expiry - today).days
        if days_remaining < 0:
            return {'valid': False, 'error': 'expired',
                    'expiry_date': expiry_str, 'days_remaining': 0,
                    'license_id': key_data['license_id']}
    else:
        # Lifetime license
        days_remaining = -1  # -1 signals lifetime

    return {
        'valid': True,
        'error': None,
        'expiry_date': expiry_str,
        'days_remaining': days_remaining,
        'license_id': key_data['license_id'],
        'tier': key_data.get('tier', 'pro'),
    }


# ── Activation ─────────────────────────────────────────────────────────────────

def activate_license(resources_path: Path, key_str: str) -> dict:
    """Activate a license key on this machine.

    Returns:
        {
            'success': bool,
            'error': None | str,
            'expiry_date': str | None,
            'days_remaining': int | None,
        }
    """
    key_data = parse_license_key(key_str)
    if key_data is None:
        return {'success': False, 'error': 'invalid_key',
                'expiry_date': None, 'days_remaining': None}

    today = date.today()
    creation_date = date.fromisoformat(key_data['creation_date'])
    days_valid = key_data['days_valid']

    # Check if key is too old to activate (only for non-lifetime keys)
    if days_valid > 0:
        key_absolute_expiry = creation_date + timedelta(days=days_valid)
        if today > key_absolute_expiry:
            return {'success': False, 'error': 'key_expired_before_activation',
                    'expiry_date': None, 'days_remaining': None}

    # Compute expiry from activation date
    if days_valid > 0:
        expiry_date = today + timedelta(days=days_valid)
        days_remaining = days_valid
    else:
        expiry_date = None  # Lifetime
        days_remaining = -1

    # Normalize key format
    normalized = key_str.strip().upper()
    if not normalized.startswith(KEY_PREFIX + '-'):
        chars = normalized.replace('-', '')
        normalized = f"{KEY_PREFIX}-{chars[0:5]}-{chars[5:10]}-{chars[10:15]}-{chars[15:20]}"

    # Generate machine fingerprint
    machine_id = get_machine_id()

    tier = key_data.get('tier', 'pro')

    # Save license data
    lic_data = {
        'license_key': normalized,
        'machine_id': machine_id,
        'activation_date': today.isoformat(),
        'expiry_date': expiry_date.isoformat() if expiry_date else None,
        'license_id': key_data['license_id'],
        'version': key_data['version'],
        'tier': tier,
    }
    save_license(resources_path, lic_data)

    return {
        'success': True,
        'error': None,
        'expiry_date': lic_data['expiry_date'],
        'days_remaining': days_remaining,
        'tier': tier,
    }
