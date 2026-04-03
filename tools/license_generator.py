"""
MailNexus Pro — License Key Generator (Admin Tool)

Standalone script to generate offline license keys.

Usage:
    python license_generator.py --days 90
    python license_generator.py --days 90 --id 42
    python license_generator.py --days 365 --batch 10
    python license_generator.py --days 0          # lifetime license

Output:
    License #    1 |   90 days | MNX-XXXXX-XXXXX-XXXXX-XXXXX
"""

import argparse
import hmac
import hashlib
from datetime import date, timedelta
from pathlib import Path

# ── Constants (MUST match electron-app/backend/licensing.py) ───────────────────

ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # 31 chars
BASE = len(ALPHABET)
KEY_PREFIX = "MNX"
SECRET_KEY = b'f7a3d91c4e6b8205fa9c1d3e7b4a6082c5f8e1d9b3a7604c2e8f5d1a9b3c7e40'
EPOCH = date(2025, 1, 1)

COUNTER_FILE = Path(__file__).parent / 'license_counter.txt'

# Tier mapping (MUST match licensing.py)
TIER_VERSION = {'pro': 1, 'basic': 2}

# ── Base31 Encode ──────────────────────────────────────────────────────────────


def _bytes_to_int(data: bytes) -> int:
    result = 0
    for b in data:
        result = (result << 8) | b
    return result


def _int_to_bytes(n: int, length: int) -> bytes:
    result = []
    for _ in range(length):
        result.append(n & 0xFF)
        n >>= 8
    return bytes(reversed(result))


def _base31_encode(data: bytes, length: int = 20) -> str:
    n = _bytes_to_int(data)
    chars = []
    for _ in range(length):
        chars.append(ALPHABET[n % BASE])
        n //= BASE
    return ''.join(reversed(chars))


# ── Key Generation ─────────────────────────────────────────────────────────────

def generate_key(license_id: int, days_valid: int, version: int = 1) -> str:
    """Generate a single license key."""
    creation_day = (date.today() - EPOCH).days

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


# ── Counter Management ─────────────────────────────────────────────────────────

def _read_counter() -> int:
    if COUNTER_FILE.exists():
        try:
            return int(COUNTER_FILE.read_text().strip())
        except (ValueError, OSError):
            pass
    return 0


def _write_counter(val: int) -> None:
    COUNTER_FILE.write_text(str(val))


def next_license_id() -> int:
    current = _read_counter()
    new_id = current + 1
    _write_counter(new_id)
    return new_id


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='MailNexus Pro — License Key Generator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            'Examples:\n'
            '  python license_generator.py --days 30\n'
            '  python license_generator.py --days 90 --id 100\n'
            '  python license_generator.py --days 365 --batch 5\n'
            '  python license_generator.py --days 0           # lifetime\n'
        )
    )
    parser.add_argument('--days', type=int, required=True,
                        help='License validity in days (0 = lifetime)')
    parser.add_argument('--id', type=int, default=None,
                        help='License ID (auto-incremented if omitted)')
    parser.add_argument('--batch', type=int, default=1,
                        help='Number of keys to generate')
    parser.add_argument('--tier', type=str, default='pro',
                        choices=['basic', 'pro'],
                        help='License tier: basic (Steps 1-2) or pro (Steps 1-4)')

    args = parser.parse_args()

    if args.days < 0 or args.days > 4095:
        print("Error: --days must be between 0 and 4095")
        return

    version = TIER_VERSION[args.tier]

    print(f"\n{'='*60}")
    print(f"  MailNexus Pro License Generator")
    print(f"  Date: {date.today().isoformat()}")
    print(f"  Validity: {args.days} days" if args.days > 0 else "  Validity: Lifetime")
    print(f"  Tier: {args.tier.upper()}")
    print(f"{'='*60}\n")

    for i in range(args.batch):
        if args.id is not None:
            lid = args.id + i
        else:
            lid = next_license_id()

        key = generate_key(lid, args.days, version=version)
        days_label = f"{args.days:>4d} days" if args.days > 0 else "Lifetime"
        print(f"  License #{lid:>5d} | {days_label} | {args.tier.upper():>5s} | {key}")

    print(f"\n{'='*60}")
    print(f"  Generated {args.batch} key(s)")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    main()
