# Next Session Plan: NexusBrowser Rebuild + Nexus API

> **Goal:** Rebuild NexusBrowser as a local browser engine (no NST dependency),
> then expose our profile manager as a standalone API (like NST's API) so
> external tools/scripts can manage profiles programmatically.

---

## Current State (What's Done)

### Working
- NST Browser integration fully working (API at `localhost:8848/api/v2`)
- NST fingerprint flags: `BasedOnIp` for timezone/geo/localization
- CDP overrides thread (`_run_cdp_overrides()`) for persistent screen/timezone/locale lock
- Real-time profile status polling in UI (2s interval)
- Server-side profile filtering (All, Running, Logged In, etc.)
- SOCKS5 bridge in `stealth_chrome.py` for Chrome SOCKS5 auth
- `--disable-features` consolidated into single flag
- `ChromeRootStoreUsed` disabled for SSL on custom Chromium
- `about:blank` removed from Chrome startup
- Input focus fix after delete confirm dialog
- App close no longer kills user's personal Chrome

### Deleted (Needs Rebuilding)
- ALL NexusBrowser code removed from `shared/nexus_profile_manager.py`:
  - `_DESKTOP_UA_TEMPLATES`, `_DESKTOP_PLATFORMS`, `_WEBGL_CONFIGS`
  - `_HARDWARE_SPECS`, `_FONT_LISTS`
  - `_generate_nexus_fingerprint(os_type)`
  - NexusBrowser branches in `create_profile()`, `launch_profile()`,
    `launch_and_connect()`, `stop_nst_browser()`, `close_profile()`
  - Entire `_run_nexus_browser()` function

### Kept Intact
- `shared/stealth_chrome.py` — full StealthChrome class with:
  - Chrome process launch with stealth flags
  - SOCKS5 TCP bridge (`_start_socks5_bridge()`)
  - HTTP proxy auth extension
  - CDP connection + overrides
  - All C++ config flags and stealth injection scripts

---

## Part 1: Rebuild NexusBrowser Engine

NexusBrowser = our own Chromium browser using `shared/stealth_chrome.py`.
Alternative to NST for users who don't have NST installed.

### Step 1.1 — Fingerprint Data Tables
**File:** `shared/nexus_profile_manager.py` (add after `_SCREEN_RESOLUTIONS`)

Rebuild these data structures with modern values:

```python
_DESKTOP_UA_TEMPLATES = {
    'windows': [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{ver} Safari/537.36',
    ],
    'macos': [...],
    'linux': [...],
}
# Use Chrome versions 130-136+ (keep updated)

_DESKTOP_PLATFORMS = {
    'windows': 'Win32',
    'macos': 'MacIntel',
    'linux': 'Linux x86_64',
}

_WEBGL_CONFIGS = [
    {'vendor': 'Google Inc. (NVIDIA)', 'renderer': 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)'},
    {'vendor': 'Google Inc. (AMD)', 'renderer': 'ANGLE (AMD, AMD Radeon RX 580 Direct3D11 vs_5_0 ps_5_0, D3D11)'},
    {'vendor': 'Google Inc. (Intel)', 'renderer': 'ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)'},
    # 10-15 entries covering common GPUs
]

_HARDWARE_SPECS = [
    {'concurrency': 4, 'memory': 8},
    {'concurrency': 8, 'memory': 8},
    {'concurrency': 8, 'memory': 16},
    {'concurrency': 12, 'memory': 16},
    {'concurrency': 16, 'memory': 32},
]

_FONT_LISTS = {
    'windows': ['Arial', 'Calibri', 'Cambria', 'Comic Sans MS', 'Consolas', 'Courier New', ...],
    'macos': ['Helvetica', 'Helvetica Neue', 'Lucida Grande', ...],
    'linux': ['Liberation Sans', 'DejaVu Sans', ...],
}
```

### Step 1.2 — `_generate_nexus_fingerprint(os_type)`
**File:** `shared/nexus_profile_manager.py`

```python
def _generate_nexus_fingerprint(os_type: str = 'windows') -> dict:
    """Generate a realistic browser fingerprint for NexusBrowser."""
    screen = random.choice([s for s in _SCREEN_RESOLUTIONS if s[0] <= 1920])
    chrome_ver = random.randint(130, 136)
    ua = random.choice(_DESKTOP_UA_TEMPLATES[os_type]).format(ver=f'{chrome_ver}.0.0.0')
    gpu = random.choice(_WEBGL_CONFIGS)
    hw = random.choice(_HARDWARE_SPECS)
    fonts = random.sample(_FONT_LISTS.get(os_type, _FONT_LISTS['windows']), k=min(20, ...))

    return {
        'user_agent': ua,
        'platform': _DESKTOP_PLATFORMS.get(os_type, 'Win32'),
        'screen_width': screen[0],
        'screen_height': screen[1],
        'webgl_vendor': gpu['vendor'],
        'webgl_renderer': gpu['renderer'],
        'hardware_concurrency': hw['concurrency'],
        'device_memory': hw['memory'],
        'noise_seed': random.randint(1, 999999),
        'audio_seed': random.randint(1, 999999),
        'fonts': fonts,
    }
```

### Step 1.3 — `create_profile()` Nexus Branch
**File:** `shared/nexus_profile_manager.py` → `create_profile()`

When `engine='nexus'`:
- Generate ID: `nexus-{uuid4().hex[:12]}`
- Call `_generate_nexus_fingerprint(os_type)`
- Create profile dir: `{storage_path}/profiles/{id}`
- Save to local `profiles.json` (NO NST API calls)
- Return same dict format as NST profiles

### Step 1.4 — `_run_nexus_browser()` Function
**File:** `shared/nexus_profile_manager.py` (new function)

```python
def _run_nexus_browser(profile_id: str, profile: dict, stop_event: threading.Event):
    """Launch StealthChrome browser in background thread."""
    from shared.stealth_chrome import StealthChrome

    fp = profile.get('fingerprint', {})
    proxy_data = profile.get('proxy')

    # Build proxy arg
    proxy_arg = None
    if proxy_data and proxy_data.get('host'):
        ptype = proxy_data.get('type', 'http')
        host, port = proxy_data['host'], proxy_data.get('port', '')
        user, pw = proxy_data.get('username', ''), proxy_data.get('password', '')
        server = f'socks5://{host}:{port}' if ptype == 'socks5' else f'http://{host}:{port}'
        proxy_arg = {'server': server}
        if user: proxy_arg['username'] = user
        if pw: proxy_arg['password'] = pw

    nexus_config = {
        'hardwareConcurrency': fp.get('hardware_concurrency', 8),
        'deviceMemory': fp.get('device_memory', 8),
        'platform': fp.get('platform', 'Win32'),
        'webglVendor': fp.get('webgl_vendor', ''),
        'webglRenderer': fp.get('webgl_renderer', ''),
        'noiseSeed': fp.get('noise_seed', 0),
        'audioSeed': fp.get('audio_seed', 0),
    }

    sc = StealthChrome()
    loop = asyncio.new_event_loop()
    ws = loop.run_until_complete(sc.start(
        profile_dir=profile.get('profile_dir', ''),
        proxy=proxy_arg,
        window_size=(fp.get('screen_width', 1920), fp.get('screen_height', 1080)),
        nexus_config=nexus_config,
    ))
    loop.close()

    with _lock:
        _active_browsers[profile_id] = {
            'status': 'running',
            'ws_endpoint': ws,
            'stealth_chrome': sc,
            'stop_event': stop_event,
        }

    # Start persistent CDP overrides (timezone from proxy, screen lock)
    cdp_thread = threading.Thread(
        target=_run_cdp_overrides,
        args=(ws, stop_event),
        kwargs={
            'timezone': '',  # resolved from proxy IP
            'locale': 'en-US',
            'screen_w': fp.get('screen_width', 1920),
            'screen_h': fp.get('screen_height', 1080),
        },
        daemon=True,
    )
    cdp_thread.start()

    # Wait until stop requested
    stop_event.wait()

    # Cleanup
    try:
        loop2 = asyncio.new_event_loop()
        loop2.run_until_complete(sc.stop())
        loop2.close()
    except Exception:
        if sc.process:
            try: sc.process.kill()
            except: pass

    with _lock:
        _active_browsers.pop(profile_id, None)
```

### Step 1.5 — `launch_profile()` Nexus Branch
**File:** `shared/nexus_profile_manager.py` → `launch_profile()`

Add after existing NST branch:
```python
elif engine == 'nexus':
    stop_event = threading.Event()
    t = threading.Thread(target=_run_nexus_browser, args=(profile_id, profile, stop_event), daemon=True)
    t.start()
    # Wait briefly for browser to start
    for _ in range(30):
        time.sleep(1)
        with _lock:
            if profile_id in _active_browsers and _active_browsers[profile_id].get('ws_endpoint'):
                return {'status': 'running', 'ws_endpoint': _active_browsers[profile_id]['ws_endpoint']}
    return {'status': 'error', 'message': 'Timeout waiting for NexusBrowser'}
```

### Step 1.6 — `launch_and_connect()` Nexus Branch
Add after NST branch:
```python
# NexusBrowser — launch and return CDP endpoint
from shared.stealth_chrome import StealthChrome
# ... (same setup as _run_nexus_browser but synchronous, return ws URL)
```

### Step 1.7 — `stop_nst_browser()` + `close_profile()` Nexus Branch
Add `engine='nexus'` handling:
- Pop from `_active_browsers`
- Set `stop_event` to signal `_run_nexus_browser` thread
- Async `sc.stop()` with process kill fallback

### Step 1.8 — `update_profile()` / `delete_profile()` Nexus Branch
- `update_profile()`: when `engine='nexus'`, skip all `_nst_put()` calls, just update local JSON
- `delete_profile()`: when `engine='nexus'`, skip `_nst_delete()` calls, just remove dir + JSON entry

---

## Part 2: Nexus API (Our Own REST API)

Build a REST API that exposes our profile manager functionality, mirroring NST's
API structure. This lets external scripts, other apps, or future microservices
manage profiles without going through the Electron UI.

### Why Build This?
1. **External automation** — scripts can create/launch/stop profiles via HTTP
2. **Decoupled architecture** — profile management isn't tied to Electron app
3. **Consistent interface** — same API shape whether using NST or NexusBrowser
4. **Future-proof** — could run as standalone service, Docker container, etc.

### Step 2.1 — API Design (NST-Compatible Format)

**Base URL:** `http://localhost:5000/api/nexus/v2`
(Mounted in existing Flask server — no separate process needed)

**Auth:** `x-api-key` header (reads from `config/browser.json` → `nexus_api_key`)

**Response format (matches NST):**
```json
{
  "err": false,
  "msg": "success",
  "data": { ... }
}
```
Error:
```json
{
  "err": true,
  "msg": "Profile not found",
  "data": null
}
```

### Step 2.2 — Profile CRUD Endpoints

#### `GET /api/nexus/v2/profiles`
List all profiles with optional filtering.

Query params: `search`, `filter` (all|running|logged_in|not_logged_in), `page`, `per_page`

Response:
```json
{
  "err": false,
  "msg": "success",
  "data": {
    "profiles": [...],
    "total": 42,
    "page": 1,
    "per_page": 20
  }
}
```

Maps to: `nexus_profile_manager.get_profiles(search, filter, page, per_page)`

#### `GET /api/nexus/v2/profiles/{id}`
Get single profile.

Response:
```json
{
  "err": false,
  "msg": "success",
  "data": {
    "id": "abc123",
    "name": "Profile 1",
    "engine": "nst",
    "email": "...",
    "status": "logged_in",
    "browser_open": "stopped",
    "proxy": {...},
    "fingerprint": {...},
    "nst_profile_id": "..."
  }
}
```

Maps to: `nexus_profile_manager.get_profile(id)`

#### `POST /api/nexus/v2/profiles`
Create new profile.

Request body:
```json
{
  "name": "My Profile",
  "engine": "nst",        // or "nexus"
  "os_type": "windows",   // windows, macos, linux
  "email": "user@gmail.com",
  "password": "...",
  "proxy": "socks5://user:pass@host:port",
  "notes": "optional notes",
  "totp_secret": "...",
  "backup_codes": ["123456", "789012"]
}
```

Response:
```json
{
  "err": false,
  "msg": "Profile created",
  "data": { "id": "abc123", "name": "My Profile", ... }
}
```

Maps to: `nexus_profile_manager.create_profile(...)`

#### `PUT /api/nexus/v2/profiles/{id}`
Update profile fields.

Request body (all optional):
```json
{
  "name": "New Name",
  "email": "new@gmail.com",
  "password": "...",
  "proxy": "http://host:port",
  "status": "logged_in",
  "notes": "...",
  "totp_secret": "...",
  "backup_codes": [...]
}
```

Maps to: `nexus_profile_manager.update_profile(id, **fields)`

#### `DELETE /api/nexus/v2/profiles/{id}`
Delete single profile (closes browser first, deletes from NST if applicable).

Maps to: `nexus_profile_manager.delete_profile(id)`

#### `DELETE /api/nexus/v2/profiles`
Delete ALL profiles.

Maps to: `nexus_profile_manager.delete_all_profiles()`

### Step 2.3 — Browser Control Endpoints

#### `POST /api/nexus/v2/browsers/{id}`
Launch browser for profile. Returns CDP WebSocket URL.

Response:
```json
{
  "err": false,
  "msg": "Browser launched",
  "data": {
    "webSocketDebuggerUrl": "ws://127.0.0.1:9222/devtools/browser/abc..."
  }
}
```

Maps to: `nexus_profile_manager.launch_and_connect(id)`

#### `DELETE /api/nexus/v2/browsers/{id}`
Stop browser for profile.

Maps to: `nexus_profile_manager.stop_nst_browser(id)`

#### `POST /api/nexus/v2/browsers/{id}/launch`
Launch browser for UI viewing (Play button equivalent). Does NOT return CDP URL.

Maps to: `nexus_profile_manager.launch_profile(id)`

#### `POST /api/nexus/v2/browsers/{id}/close`
Close browser (same as DELETE but POST for consistency with existing routes).

Maps to: `nexus_profile_manager.close_profile(id)`

#### `POST /api/nexus/v2/browsers/close-all`
Close all running browsers.

Maps to: `nexus_profile_manager.close_all_profiles()`

### Step 2.4 — Status Endpoints

#### `GET /api/nexus/v2/browsers/{id}/status`
Get browser status for single profile.

Response:
```json
{
  "err": false,
  "msg": "success",
  "data": {
    "browser_open": "running",  // or "stopped"
    "ws_endpoint": "ws://...",
    "engine": "nst"
  }
}
```

Maps to: `nexus_profile_manager.profile_status(id)`

#### `GET /api/nexus/v2/browsers/status`
Get status of ALL profiles (for polling).

Response:
```json
{
  "err": false,
  "msg": "success",
  "data": {
    "profiles": {
      "abc123": {"browser_open": "running", "engine": "nst"},
      "def456": {"browser_open": "stopped", "engine": "nexus"}
    },
    "running_count": 1,
    "total_count": 2
  }
}
```

Maps to: `nexus_profile_manager.all_status()`

### Step 2.5 — Batch Operations

#### `POST /api/nexus/v2/profiles/batch-create`
Create multiple profiles at once.

Request body:
```json
{
  "count": 10,
  "engine": "nexus",
  "os_type": "windows",
  "proxy_list": ["socks5://...", "http://..."]  // round-robin assignment
}
```

Maps to: `nexus_profile_manager.batch_create(count, blueprint)`

#### `POST /api/nexus/v2/profiles/batch-login`
Batch login from Excel file.

Request body: `multipart/form-data` with Excel file

Maps to: `nexus_profile_manager.batch_login(file_path, num_workers)`

#### `POST /api/nexus/v2/profiles/run-operations`
Run bot operations on selected profiles.

Request body:
```json
{
  "profile_ids": ["abc123", "def456"],
  "steps": [1, 2],
  "operations": {"L1": true, "L2": false, "M1": true, ...},
  "num_workers": 3
}
```

#### `GET /api/nexus/v2/profiles/ops-status`
Get current operations progress.

### Step 2.6 — Config Endpoints

#### `GET /api/nexus/v2/config`
Get profile manager config (storage path, NST settings, etc.)

#### `POST /api/nexus/v2/config`
Update config.

#### `POST /api/nexus/v2/profiles/export`
Export profiles to JSON/Excel.

Request body:
```json
{
  "profile_ids": ["abc123", "def456"],
  "format": "json"  // or "excel"
}
```

Maps to: `nexus_profile_manager.export_profiles(profile_ids)`

### Step 2.7 — Implementation in server.py
**File:** `electron-app/backend/server.py`

Add a Flask Blueprint for clean separation:
```python
from flask import Blueprint
nexus_api = Blueprint('nexus_api', __name__, url_prefix='/api/nexus/v2')

def _napi_response(data=None, msg='success', err=False, status=200):
    """NST-compatible response wrapper."""
    return jsonify({'err': err, 'msg': msg, 'data': data}), status

@nexus_api.before_request
def check_api_key():
    """Optional API key validation."""
    # Read expected key from config/browser.json → nexus_api_key
    # If set, validate x-api-key header
    pass

@nexus_api.route('/profiles', methods=['GET'])
def api_list_profiles():
    ...

@nexus_api.route('/profiles', methods=['POST'])
def api_create_profile():
    ...

# ... all endpoints ...

# Register in main app:
app.register_blueprint(nexus_api)
```

### Step 2.8 — API Key Management
**File:** `config/browser.json`

Add field:
```json
{
  "use_nst": true,
  "nst_api_key": "a025417d-...",
  "nst_api_base": "http://localhost:8848/api/v2",
  "nexus_api_key": "",        // <-- NEW: key for our Nexus API
  "nexus_binary": "..."
}
```

**File:** `electron-app/renderer/modules/config.js`

Add input field in NST config panel for users to set/view their Nexus API key.

---

## Part 3: UI Changes

### Step 3.1 — Engine Selector in Profile Creation
**File:** `electron-app/renderer/modules/profiles.js`

In the "Create Profile" modal:
```html
<select id="profileEngine">
  <option value="nst">NST Browser (Recommended)</option>
  <option value="nexus">NexusBrowser (Local)</option>
</select>
```

Pass selected engine to `POST /api/profiles` body.

### Step 3.2 — Engine Badge on Profile Cards
Show small badge on each profile card:
- NST profiles: blue "NST" badge
- NexusBrowser profiles: green "LOCAL" badge

### Step 3.3 — NST API Key Input
**File:** `electron-app/renderer/modules/config.js`

Add to Browser Config section:
- NST API Key input (password field with show/hide toggle)
- NST API Base URL input (default: `http://localhost:8848/api/v2`)
- "Test Connection" button that hits NST health endpoint

---

## Part 4: Implementation Order (Step by Step)

### Phase 1 — NexusBrowser Core (Do First)
| # | Task | File | Est. |
|---|------|------|------|
| 1 | Add fingerprint data tables | `nexus_profile_manager.py` | 15 min |
| 2 | Add `_generate_nexus_fingerprint()` | `nexus_profile_manager.py` | 10 min |
| 3 | Add nexus branch to `create_profile()` | `nexus_profile_manager.py` | 10 min |
| 4 | Add `_run_nexus_browser()` function | `nexus_profile_manager.py` | 20 min |
| 5 | Add nexus branch to `launch_profile()` | `nexus_profile_manager.py` | 10 min |
| 6 | Add nexus branch to `launch_and_connect()` | `nexus_profile_manager.py` | 10 min |
| 7 | Add nexus branch to `stop_nst_browser()` + `close_profile()` | `nexus_profile_manager.py` | 10 min |
| 8 | Add nexus branch to `update_profile()` + `delete_profile()` | `nexus_profile_manager.py` | 5 min |
| **9** | **Test: create → launch → browserscan → close** | manual | 15 min |

### Phase 2 — Nexus API
| # | Task | File | Est. |
|---|------|------|------|
| 10 | Create Blueprint + response helper | `server.py` | 10 min |
| 11 | Profile CRUD endpoints (GET/POST/PUT/DELETE) | `server.py` | 20 min |
| 12 | Browser control endpoints (launch/close) | `server.py` | 15 min |
| 13 | Status + batch endpoints | `server.py` | 15 min |
| 14 | API key auth middleware | `server.py` | 5 min |
| **15** | **Test: curl/Postman all endpoints** | manual | 15 min |

### Phase 3 — UI Integration
| # | Task | File | Est. |
|---|------|------|------|
| 16 | Engine selector in create profile modal | `profiles.js` + `index.html` | 10 min |
| 17 | Engine badge on profile cards | `profiles.js` + `styles.css` | 10 min |
| 18 | NST API key + Nexus API key config inputs | `config.js` + `index.html` | 15 min |
| **19** | **Test: full UI flow** | manual | 10 min |

### Phase 4 — Verification
| # | Task | Check |
|---|------|-------|
| 20 | HTTP proxy works on NexusBrowser | browserscan.net shows proxy IP |
| 21 | SOCKS5 proxy works on NexusBrowser | browserscan.net shows proxy IP |
| 22 | Timezone matches proxy IP | browserscan.net shows correct TZ |
| 23 | Screen ≤ 1920 and locked | Can't resize bigger |
| 24 | No WebRTC IP leak | browserleaks.com |
| 25 | SSL works (browserscan.net loads) | No "secure connection" error |
| 26 | Canvas/Audio noise working | browserscan.net fingerprint |
| 27 | Profile CRUD via Nexus API | curl tests |
| 28 | Browser launch/stop via Nexus API | curl tests |

---

## Key Constraints (MUST Follow)
1. **Screen ≤ 1920** — enforced via CDP `Emulation.setDeviceMetricsOverride`
2. **Timezone = proxy IP** — CDP `Emulation.setTimezoneOverride` via persistent thread
3. **SOCKS5 auth** — local TCP bridge (Chrome can't do SOCKS5 auth natively)
4. **Single `--disable-features`** — Chrome only reads the LAST occurrence
5. **`ChromeRootStoreUsed` disabled** — custom Chromium lacks bundled root CAs
6. **CDP `Target.setAutoAttach`** — overrides must apply to every new tab
7. **No `about:blank`** — removed from Chrome startup args
8. **App close ≠ kill all Chrome** — only kill bot-launched browsers
9. **NST API format** — Nexus API responses match `{err, msg, data}` structure

---

## Key Files Reference
| File | What It Does |
|------|-------------|
| `shared/nexus_profile_manager.py` | Core profile CRUD + browser launch/stop (NST + NexusBrowser) |
| `shared/stealth_chrome.py` | Chrome process mgmt, CDP, SOCKS5 bridge, stealth scripts |
| `shared/nexus_proxy_manager.py` | Proxy string parsing |
| `electron-app/backend/server.py` | Flask backend — existing `/api/profiles/` + new `/api/nexus/v2/` |
| `electron-app/renderer/modules/profiles.js` | Profile list UI, real-time polling, filtering |
| `electron-app/renderer/modules/config.js` | Config panel (add NST/Nexus API key inputs) |
| `electron-app/renderer/index.html` | HTML structure (add engine selector, API key fields) |
| `electron-app/renderer/styles.css` | Styling (engine badges) |
| `config/browser.json` | NST API key, Nexus API key, binary paths |

---

## How to Start Next Session
Just say: **"Follow NEXT_SESSION_PLAN.md"** and we'll execute Phase 1 → 2 → 3 → 4 in order.
