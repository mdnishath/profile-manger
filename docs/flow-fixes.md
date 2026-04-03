# Flow Fixes: Login to Signout (Proxy-Safe Waits)

All issues discovered and fixed step-by-step.
Give this file to Claude in the next session if any step needs revisiting.

---

## Issue 1: `_is_inbox_url()` False Positive on SetOSID Redirect

**File:** `src/login_flow.py`
**Function:** `_is_inbox_url()`

**Problem:**
After login, Google does a multi-step redirect chain:
1. `mail.google.com/accounts/SetOSID?...continue=...mail.google.com/mail/...`
2. `accounts.youtube.com/accounts/SetSID?...`
3. `mail.google.com/mail/u/0/#inbox` (actual inbox)

The old check `"mail.google.com/mail" in url` matched step 1 because the
`continue=` query parameter contained `mail.google.com/mail`. Bot thought
it was on the inbox but was actually on an intermediate redirect page.

**Fix:**
Strip query params before checking:
```python
def _is_inbox_url(url: str) -> bool:
    base_url = url.split('?')[0]
    return INBOX_URL in base_url
```

**Impact:** Bot now waits for the ACTUAL inbox URL before starting operations.
Previously it would start operations (like Write Review) while still on the
redirect page, causing them to fail.

---

## Issue 2: Static `asyncio.sleep()` Calls Don't Adapt to Proxy Speed

**File:** `src/login_flow.py`

**Problem:**
All page transition waits used static `asyncio.sleep(3)` or `sleep(5)`.
With proxy, pages load slower. Static sleeps are:
- Too short on slow proxy: bot clicks before page is ready
- Too long on fast connection: wastes time

**Fix:**
Added `_wait_for_page_settle()` helper:
```python
async def _wait_for_page_settle(page, worker_id, label="", timeout=15000):
    try:
        await page.wait_for_load_state('networkidle', timeout=timeout)
    except Exception:
        pass  # Timeout fallback
    await asyncio.sleep(1)  # DOM buffer
```

`networkidle` = Playwright waits until no network requests for 500ms.
Automatically adapts to any connection speed.

**16 static sleeps replaced** across the entire login flow:
- After `goto()` navigation (was 3s)
- After email Next click (was 4s)
- After password Next click (was 5s)
- After TOTP submit (was 5s)
- After passkey/recovery skip (was 3s each)
- After backup code submit (was 5s)
- After "Try another way" click (was 3s)
- After auth/backup option selection (was 3s each)
- Chrome error recovery (was 3s)
- Unknown/unhandled screens (was 3s each)

---

## Issue 3: Buttons Clicked Before They're Visible

**File:** `src/login_flow.py`

**Problem:**
"Next" buttons were clicked immediately after filling input fields.
With proxy, the button might not be rendered yet or might be disabled.

**Fix:**
Added `wait_for(state='visible', timeout=10000)` before every button click:
- Email "Next" button
- Password "Next" button
- Backup code "Next" button
- TOTP "Next"/"Verify" button (already had wait)

Pattern:
```python
try:
    await page.locator('button:has-text("Next")').first.wait_for(
        state='visible', timeout=10000
    )
except Exception:
    _log(worker_id, "Next button wait timed out, trying click anyway...")
await page.locator('button:has-text("Next")').first.click()
```

---

## Issue 4: Input Fields Filled Before Ready

**File:** `src/login_flow.py`

**Problem:**
Password, TOTP, and backup code input fields were filled without waiting
for them to appear. With proxy, the form might still be loading.

**Fix:**
Added `wait_for_selector(state='visible', timeout=10000)` before every fill:
- Password input (was already added in previous session)
- TOTP input (was already added in previous session)
- Backup code input (NEW - added this session)

---

## Issue 5: `_wait_for_inbox_load` Timeout Too Short for Proxy

**File:** `src/login_flow.py`
**Function:** `_wait_for_inbox_load()`

**Problem:**
Default timeout was 15 seconds. With proxy, the redirect chain
(SetOSID -> SetSID -> inbox) can take 20+ seconds.

**Fix:**
Increased default timeout from 15s to 30s:
```python
async def _wait_for_inbox_load(page, worker_id: int, timeout: int = 30):
```

---

## Issue 6: Write Review Page Not Fully Loaded Before Interaction

**File:** `step3/operations/write_review.py`

**Problem:**
After navigating to the Maps place URL, the code waited only 2s
(`asyncio.sleep(2)`) before looking for the "Write a review" button.
With proxy, Maps takes much longer to fully load its interactive elements.

**Fix:**
1. Replaced `sleep(2)` after goto with `wait_for_load_state('networkidle')`:
   ```python
   await page.goto(str(place_url), wait_until='domcontentloaded', timeout=45000)
   try:
       await page.wait_for_load_state('networkidle', timeout=15000)
   except Exception:
       pass
   await asyncio.sleep(1)
   ```

2. Increased "Write a review" button wait timeout from 8s to 15s

3. Replaced `sleep(3)` after contrib page navigation with `networkidle`

4. Replaced `sleep(3)` before review list wait with `networkidle`

5. Replaced `sleep(3)` after page reload in `_reload_until_live()` with `networkidle`

---

## Issue 7: Signout Wait Too Short

**File:** `shared/signout.py`

**Problem:**
Static `asyncio.sleep(3)` after logout navigation. With proxy,
the logout page might not be fully processed yet.

**Fix:**
Replaced with `wait_for_load_state('networkidle')` + 1s buffer.

---

## Summary of Changes by File

### `src/login_flow.py`
- `_is_inbox_url()`: Strip query params before matching (fixes SetOSID false positive)
- `_wait_for_inbox_load()`: Timeout 15s -> 30s
- `_wait_for_page_settle()`: New helper function (replaces all static sleeps)
- 16 static `asyncio.sleep()` replaced with `_wait_for_page_settle()`
- 3 button `wait_for(visible)` added before clicks
- 1 input `wait_for_selector(visible)` added for backup code

### `step3/operations/write_review.py`
- Maps page goto: `sleep(2)` -> `networkidle` wait
- "Write a review" button timeout: 8s -> 15s
- Contrib page goto: `sleep(3)` -> `networkidle` wait
- Review list wait: `sleep(3)` -> `networkidle` wait
- Reload in `_reload_until_live()`: `sleep(3)` -> `networkidle` wait

### `shared/signout.py`
- Logout wait: `sleep(3)` -> `networkidle` + 1s buffer

---

## Remaining `asyncio.sleep()` Calls (Intentionally Kept)

These small sleeps are intentional and serve specific purposes:

| File | Sleep | Purpose |
|------|-------|---------|
| login_flow.py | `sleep(1)` x4 | Stabilization before click/fill (prevents race conditions) |
| login_flow.py | `sleep(1)` in _wait_for_page_settle | DOM transition buffer after networkidle |
| login_flow.py | `sleep(1)` in _wait_for_inbox_load | Polling interval |
| login_flow.py | `sleep(2)` in inbox #inbox URL check | Extra DOM wait for hash change |
| login_flow.py | `sleep(4)` in chrome error retry | Network failure recovery wait |
| login_flow.py | `sleep(2)` in go_back recovery | Page restore wait |
| write_review.py | `sleep(0.5)` after scroll | Scroll settle time |
| write_review.py | `sleep(1)` x3 | Post-action JS processing waits |
| write_review.py | `sleep(5)` after Post click | Wait for review to register on Google |
| write_review.py | `sleep(2)` x2 | Menu/dialog render waits |
| write_review.py | `sleep(3)` x2 | Share dialog waits |

---

## How to Debug Future Issues

1. Check logs for `"networkidle timeout"` messages - means page is slow to settle
2. Check logs for `"wait timed out, trying click anyway"` - means element took >10s
3. If operations fail after login, check if `_is_inbox_url()` matched correctly
4. Look for `"INBOX_WAIT: SUCCESS (timeout but inbox URL present)"` - this means
   the inbox URL matched but Gmail UI elements were never found (15s -> 30s wait)
5. For write_review: check if "Write a review button not found" - Maps didn't load
