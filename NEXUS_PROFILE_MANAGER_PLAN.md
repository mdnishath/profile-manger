# NexusBrowser Profile Manager — Complete Rebuild Plan

## Reference: NST Browser Profile Create UI (15 screenshots analyzed)

---

## PHASE 0: DELETE OLD CODE COMPLETELY

### Files to DELETE:
```
electron-app/renderer/modules/profiles.js    → DELETE entirely
shared/profile_manager.py                    → DELETE entirely (2,958 lines)
shared/fingerprint_manager.py                → DELETE if exists
nexusbrowser/modules/                        → DELETE entirely (old module system)
```

### Files to REWRITE from scratch:
```
electron-app/renderer/modules/profiles.js    → New UI (NST-style)
electron-app/renderer/index.html             → New Profiles section HTML
shared/nexus_profile_manager.py              → New backend (clean, modular)
nexusbrowser/fingerprint/                    → New fingerprint engine
```

---

## PHASE 1: PROFILE LIST PAGE (NST Main Screen)

### UI Layout (from NST screenshot 1):
```
┌─────────────────────────────────────────────────────────┐
│  NexusBrowser    Profile Manager                         │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Filter Bar:                                             │
│  [All(478)] [Default(1)] [WIN10/CHROME(6)] [Mac(225)]   │
│                                                          │
│  Action Bar:                                             │
│  [+ Create Profile ▼] [Launch] [Stop] [🗑] [⚙]         │
│    └─ Create Profile                                     │
│    └─ Batch Create                                       │
│    └─ Batch Import                                       │
│                                                          │
│  Search: [Name ▼] [________________] [Search]            │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │ ☐ │ Profile        │ Actions │ Status │ Group │   │   │
│  │   │                │ ▶ ✎ ⋮  │        │       │   │   │
│  ├───┼────────────────┼─────────┼────────┼───────┤   │  │
│  │ ☐ │ Gmail-sheet..  │ ▶ ✎ ⋮  │ Ready  │ Main  │   │  │
│  │   │ user@gmail.com │         │        │       │   │  │
│  ├───┼────────────────┼─────────┼────────┼───────┤   │  │
│  │ ☐ │ ishramohon..   │ ▶ ✎ ⋮  │ Ready  │ Main  │   │  │
│  │   │ ish@gmail.com  │         │        │       │   │  │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  Proxy column: 🇫🇷 FR · Europe/Paris · 10.86.67.77     │
│                🇧🇩 BD · Asia/Dhaka · 103.181.75.9      │
│                                                          │
│  Tags | Notes | Update Time columns                      │
│                                                          │
│  Pagination: [< 1 2 3 4 > ] [10/page ▼]                │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Actions Context Menu (from NST screenshot 5):
```
▶ Open (Launch browser)
✎ Edit profile
📋 Copy
📁 Move to Group
🔄 Transfer and Share
🔀 Modify Proxy
🏷 Modify Tag
📝 Modify Note
🔗 Create Like Task
🧹 Clear local cache
🍪 Clear local cookies
📤 Export Profiles
📥 Export Cookies
🗑 Delete
```

### Search Filter (from NST screenshot 6):
```
Search by: [Name ▼]
  - Name
  - ID
  - Notes
  - Proxy IP
  - Proxy Country
```

---

## PHASE 2: PROFILE CREATE PAGE (NST Profile Create)

### 4 Tabs: Overview | Proxy | Hardware | Advanced

### Tab 1: OVERVIEW (from NST screenshot 7-8)
```
┌─────────────────────────────────────────────────────────┐
│  Profile Create                                          │
│                                                          │
│  [Overview] [Proxy] [Hardware] [Advanced]                │
│                                                          │
│  ─── Overview ───                                        │
│                                                          │
│  Name:           [___________________] (auto-generated)  │
│  Profile Group:  [Nishanth Master ▼]                     │
│                                                          │
│  Browser Kernel: (●) NexusChrome  ( ) Firefox            │
│  Kernel Version: [nexuschrome 133 ▼]                     │
│                                                          │
│  Operating       (●) Windows  ( ) macOS  ( ) Linux       │
│  System:         ( ) Android  ( ) iOS                    │
│                                                          │
│  System Version: [Windows 11 ▼]                          │
│                                                          │
│  User Agent:     [Mozilla/5.0 (Windows NT 10.0; Win64;  │
│                   x64) AppleWebKit/537.36 (KHTML, like   │
│                   Gecko) Chrome/133.0.6943.98 Safari/    │
│                   537.36                            ] 🔄 │
│                                                          │
│  Startup URLs:   [_________________________________]     │
│                                                          │
│                                     ┌─────────────────┐ │
│  SUMMARY (right panel):             │ [New Fingerprint]│ │
│                                     ├─────────────────┤ │
│  Overview                           │                  │ │
│    Operating System: Windows        │ Overview         │ │
│    Browser Kernel:   NexusChrome    │   OS: Windows    │ │
│    User Agent:       Mozilla/5.0... │   Kernel: Nexus  │ │
│                                     │   UA: Mozilla... │ │
│  Proxy                              │                  │ │
│    (none)                           │ Proxy            │ │
│                                     │   (none)         │ │
│  Hardware                           │                  │ │
│    WebGL Vendor:     Masked         │ Hardware         │ │
│    WebGL Renderer:   Masked         │   WebGL: Masked  │ │
│    AudioContext:     Noise          │   Audio: Noise   │ │
│                                     │                  │ │
│  [Create Profile]  [Cancel]         └─────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### Tab 2: PROXY
```
┌─────────────────────────────────────────────────────────┐
│  [Overview] [Proxy*] [Hardware] [Advanced]               │
│                                                          │
│  ─── Proxy ───                                           │
│                                                          │
│  Proxy Type:    [HTTP ▼]  (HTTP / SOCKS5 / None)         │
│  Host:          [gate.nstproxy.io___________________]    │
│  Port:          [24125_____]                             │
│  Username:      [F3F7D9FDFF89B512-residential-count...]  │
│  Password:      [V9qtzxK6_____]                          │
│                                                          │
│  [Check Proxy]  → Shows: IP, Country, ISP, Speed         │
│                                                          │
│  ─── OR paste full proxy string: ───                     │
│  [gate.nstproxy.io:24125:user:pass________________]     │
│  [Parse]                                                 │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Tab 3: HARDWARE (from NST screenshots 9-12)
```
┌─────────────────────────────────────────────────────────┐
│  [Overview] [Proxy] [Hardware*] [Advanced]               │
│                                                          │
│  ─── Hardware ───                                        │
│                                                          │
│  WebGL:          (●) Noise  ( ) Real                     │
│                  Add random noise for WebGL              │
│                                                          │
│  WebGL Metadata: (●) Masked  ( ) Custom  ( ) Real        │
│                  Generate WebGL configuration based on   │
│                  current settings                        │
│                                                          │
│  WebGPU:         [Match WebGL ▼]  Real  Disabled         │
│                                                          │
│  Canvas:         (●) Noise  ( ) Real                     │
│                  Add random noise for Canvas             │
│                                                          │
│  Hardware        (●) Allow  ( ) Disabled                 │
│  Acceleration:                                           │
│                                                          │
│  AudioContext:   (●) Noise  ( ) Real                     │
│                  Add random noise for Audio              │
│                                                          │
│  ClientRects:    ( ) Noise  (●) Real                     │
│                                                          │
│  SpeechVoice:    (●) Masked  ( ) Real                    │
│                                                          │
│  Media Devices:  (●) Custom  ( ) Real                    │
│    Video inputs: [0] Audio inputs: [1] Audio outputs: [1]│
│                                                          │
│  Battery:        (●) Masked  ( ) Real                    │
│                                                          │
│  Hardware        [2________________]                     │
│  Concurrency:                                            │
│                                                          │
│  Device Memory:  [2________________]                     │
│                                                          │
│  Device Name:    (●) Custom  ( ) Real                    │
│                  [LAPTOP-7BCCS86____________] 🔄         │
│                                                          │
│  Mac Address:    (●) Custom  ( ) Real                    │
│                  [8D:7B:D8:D8:41:50_________] 🔄        │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Tab 4: ADVANCED (from NST screenshots 13-15)
```
┌─────────────────────────────────────────────────────────┐
│  [Overview] [Proxy] [Hardware] [Advanced*]               │
│                                                          │
│  ─── IP ───                                              │
│  Language:       (●) Based on IP  ( ) Custom  ( ) Real   │
│  Timezone:       (●) Based on IP  ( ) Custom  ( ) Real   │
│  Geolocation:    (●) Prompt  ( ) Allow  ( ) Disabled     │
│  Geolocation:    (●) Based on IP  ( ) Custom             │
│                                                          │
│  ─── WebRTC ───                                          │
│  WebRTC:         (●) Masked  ( ) Custom  ( ) Real        │
│                  ( ) Disabled                             │
│                  Create WebRTC that blocks IP address     │
│                  leakage                                 │
│                                                          │
│  ─── Browser ───                                         │
│  Screen          (●) Random  ( ) Custom  ( ) Real        │
│  Resolution:                                             │
│                                                          │
│  Fonts:          (●) Masked  ( ) Custom  ( ) Real        │
│                                                          │
│  Do Not Track:   [OFF toggle]                            │
│                                                          │
│  Port Scan       ( ) Custom  (●) Disabled                │
│  Protection:                                             │
│                                                          │
│  Disable Image   [OFF toggle]                            │
│  Loading:                                                │
│                                                          │
│  Save Tabs:      [ON toggle]                             │
│                                                          │
│  Launch Args:    [--blink-settings=imagesEnabled=true]   │
│                  Additional Chrome launch arguments       │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## PHASE 3: BACKEND ARCHITECTURE (Python)

### File: `shared/nexus_profile_manager.py` (NEW — from scratch)

```python
# Architecture:
#
# NexusProfileManager
#   ├── create_profile(config) → profile_id
#   ├── delete_profile(profile_id)
#   ├── delete_all_profiles()
#   ├── get_profiles(search, filter) → [profiles]
#   ├── update_profile(profile_id, config)
#   ├── launch_profile(profile_id) → browser
#   ├── close_profile(profile_id)
#   ├── close_all_profiles()
#   ├── batch_create(count, blueprint)
#   ├── batch_import(file_path)
#   └── export_profiles(profile_ids)
#
# NexusFingerprintEngine
#   ├── generate_fingerprint(os_type, device_type) → config
#   ├── get_chrome_args(config) → [args]
#   ├── get_env_vars(config) → {env}
#   └── validate_fingerprint(config) → bool
#
# NexusProxyManager (SEPARATE — clean)
#   ├── parse_proxy(string) → ProxyConfig
#   ├── check_proxy(proxy) → {ip, country, isp, speed}
#   ├── get_geo_info(proxy) → {tz, locale, lat, lon}
#   └── format_proxy_for_chrome(proxy) → string
```

### Profile JSON Schema:
```json
{
    "id": "hex8",
    "name": "Profile 1",
    "group": "default",
    "status": "ready",
    "created_at": "ISO",
    "last_used": "ISO",
    "tags": [],
    "notes": "",

    "overview": {
        "os": "windows",
        "os_version": "Windows 11",
        "device_type": "desktop",
        "browser_kernel": "nexuschrome",
        "kernel_version": 133,
        "user_agent": "Mozilla/5.0 ...",
        "startup_urls": []
    },

    "proxy": {
        "type": "http",
        "host": "gate.nstproxy.io",
        "port": 24125,
        "username": "...",
        "password": "..."
    },

    "hardware": {
        "webgl": "noise",
        "webgl_metadata": "masked",
        "webgl_vendor": "Google Inc. (NVIDIA)",
        "webgl_renderer": "ANGLE (NVIDIA, ...)",
        "canvas": "noise",
        "canvas_seed": 123456789,
        "audio_context": "noise",
        "audio_seed": 987654321,
        "client_rects": "real",
        "speech_voice": "masked",
        "media_devices": {
            "mode": "custom",
            "video_inputs": 0,
            "audio_inputs": 1,
            "audio_outputs": 1
        },
        "battery": "masked",
        "hardware_concurrency": 4,
        "device_memory": 8,
        "device_name": "LAPTOP-7BCCS86",
        "mac_address": "8D:7B:D8:D8:41:50",
        "hardware_acceleration": true
    },

    "advanced": {
        "language": "based_on_ip",
        "language_value": "",
        "timezone": "based_on_ip",
        "timezone_value": "",
        "geolocation_prompt": "prompt",
        "geolocation_source": "based_on_ip",
        "webrtc": "masked",
        "screen_resolution": "random",
        "screen_width": 1920,
        "screen_height": 1080,
        "fonts": "masked",
        "do_not_track": false,
        "port_scan_protection": "disabled",
        "disable_image_loading": false,
        "save_tabs": true,
        "launch_args": ""
    },

    "profile_dir": "C:/path/to/profile"
}
```

---

## PHASE 4: FINGERPRINT ENGINE (C++ Level)

### What NexusBrowser handles natively (NO JS injection):
```
C++ Patches Already Applied:
  ├── navigator.webdriver → undefined (IDL removed)
  ├── navigator.hardwareConcurrency → --nexus-hardware-concurrency
  ├── navigator.deviceMemory → --nexus-device-memory
  ├── navigator.language/languages → --nexus-accept-lang + C++ patch
  ├── navigator.userAgentData.platform → --nexus-ua-platform + C++ patch
  ├── WebGL vendor/renderer → --nexus-webgl-vendor/renderer
  ├── Canvas noise → NEXUS_CANVAS_SEED env var (Skia level)
  ├── Screen width/height → --nexus-screen-width/height
  ├── outerHeight/outerWidth → patched to match inner
  ├── debugger statement → disabled (V8 patch)
  └── console profiler → stealth mode (V8 patch)

Chrome Flags (no C++ patch needed):
  ├── --user-agent="..." → Full UA string
  ├── --accept-lang=fr-FR,fr → HTTP Accept-Language
  ├── --proxy-server=host:port → Proxy
  ├── --force-webrtc-ip-handling-policy=disable_non_proxied_udp
  ├── --window-size=WxH → Window dimensions
  ├── --user-data-dir=path → Profile isolation
  └── --remote-debugging-port=PORT → CDP

Safe JS Scripts (only via Page.addScriptToEvaluateOnNewDocument):
  ├── Timezone override (Intl.DateTimeFormat) → SAFE, not detectable
  ├── WebRTC IP masking (RTCPeerConnection) → SAFE
  ├── Geolocation mock → SAFE
  ├── Audio noise (AudioContext) → seed-based
  └── Battery API mock → SAFE

DO NOT USE JS FOR (detectable via Object.defineProperty):
  ├── navigator.platform → use C++ patch
  ├── navigator.hardwareConcurrency → use C++ flag
  ├── navigator.deviceMemory → use C++ flag
  ├── navigator.plugins → native (don't touch)
  ├── navigator.mimeTypes → native (don't touch)
  └── screen.width/height → use C++ patch
```

---

## PHASE 5: OS/DEVICE SUPPORT

### Supported Devices:
```
┌─────────────┬──────────┬────────────┬──────────────────┐
│ OS          │ Platform │ Device     │ UA Pattern       │
├─────────────┼──────────┼────────────┼──────────────────┤
│ Windows 10  │ Win32    │ Desktop    │ Windows NT 10.0  │
│ Windows 11  │ Win32    │ Desktop    │ Windows NT 10.0  │
│ macOS 13    │ MacIntel │ Desktop    │ Macintosh; Intel  │
│ macOS 14    │ MacIntel │ Desktop    │ Macintosh; Intel  │
│ Linux       │ Linux    │ Desktop    │ X11; Linux x86_64│
│ Android 13  │ Linux    │ Mobile     │ Linux; Android 13│
│ Android 14  │ Linux    │ Mobile     │ Linux; Android 14│
│ iOS 17      │ iPhone   │ Mobile     │ iPhone; CPU...   │
│ iOS 18      │ iPhone   │ Mobile     │ iPhone; CPU...   │
├─────────────┴──────────┴────────────┴──────────────────┤
│ Each OS has pre-built UA templates, screen sizes,      │
│ WebGL configs, font lists, and hardware specs          │
└────────────────────────────────────────────────────────┘
```

### Blueprints (Pre-built Device Profiles):
```json
{
    "Win-Desktop-16GB": {
        "os": "windows", "os_version": "Windows 11",
        "cores": [4, 8, 12, 16], "memory": [8, 16, 32],
        "screens": ["1920x1080", "2560x1440", "1366x768"],
        "webgl_vendors": ["Google Inc. (NVIDIA)", "Google Inc. (AMD)"],
        "fonts": "windows_default"
    },
    "Mac-MBP-8GB": {
        "os": "macos", "os_version": "macOS 14",
        "cores": [8, 10, 12], "memory": [8, 16, 24],
        "screens": ["1440x900", "1680x1050", "2560x1600"],
        "webgl_vendors": ["Apple"],
        "fonts": "macos_default"
    },
    "Linux-Desktop-8GB": {
        "os": "linux", "os_version": "Linux",
        "cores": [2, 4, 8], "memory": [4, 8, 16],
        "screens": ["1920x1080", "1366x768"],
        "webgl_vendors": ["Mesa"],
        "fonts": "linux_default"
    },
    "Android-Phone": {
        "os": "android", "os_version": "Android 14",
        "cores": [4, 8], "memory": [4, 6, 8],
        "screens": ["412x915", "393x873", "360x800"],
        "webgl_vendors": ["Qualcomm", "ARM"],
        "fonts": "android_default"
    },
    "iPhone-iOS": {
        "os": "ios", "os_version": "iOS 17",
        "cores": [6], "memory": [6],
        "screens": ["390x844", "393x852", "428x926"],
        "webgl_vendors": ["Apple GPU"],
        "fonts": "ios_default"
    }
}
```

---

## PHASE 6: IsDevtoolOpen FIX (FINAL)

### Root Cause:
Playwright's `connect_over_cdp()` creates internal CDP sessions.
Chrome detects any CDP session as "DevTools is open".

### Solution Options:
1. **Patch Chromium's DevToolsAgentHost** to not report attached clients
2. **Use Playwright's `launch_persistent_context`** instead of `connect_over_cdp`
3. **Use rebrowser-patches approach** — patch Runtime.enable in V8

### Recommended: Option 1 — Patch DevToolsAgentHost
```cpp
// File: content/browser/devtools/devtools_agent_host_impl.cc
// Make IsAttached() always return false for web content targets
bool DevToolsAgentHostImpl::IsAttached() {
    return false;  // [NexusBrowser] Hide CDP attachment
}
```

---

## PHASE 7: IMPLEMENTATION ORDER

### Step 1: Delete old code (30 min)
- Delete shared/profile_manager.py
- Delete electron-app/renderer/modules/profiles.js
- Delete nexusbrowser/modules/
- Clean HTML sections

### Step 2: Build NexusFingerprintEngine (2 hours)
- Fingerprint generation per OS
- Chrome args builder
- Blueprint system
- UA template database

### Step 3: Build NexusProfileManager backend (2 hours)
- CRUD operations
- Profile storage (JSON files)
- Launch/close browser
- Batch create/import

### Step 4: Build NexusProxyManager backend (1 hour)
- Parse all proxy formats (host:port:user:pass)
- Check proxy (IP, country, speed)
- Geo lookup (timezone, locale)

### Step 5: Build Profile List UI (2 hours)
- Table with columns (NST-style)
- Search/filter bar
- Context menu actions
- Pagination

### Step 6: Build Profile Create UI (3 hours)
- 4 tabs: Overview, Proxy, Hardware, Advanced
- All fields from NST
- Summary panel (right side)
- New Fingerprint button

### Step 7: Apply IsDevtoolOpen C++ fix (1 hour)
- Patch DevToolsAgentHost
- Rebuild NexusBrowser
- Test on rebrowser

### Step 8: Full Testing (1 hour)
- Create profiles for each OS
- Test on pixelscan, rebrowser, creepjs
- Verify fingerprint uniqueness
- Verify fingerprint consistency

### TOTAL: ~12 hours of implementation

---

## KEY PRINCIPLES

1. **NO JS Object.defineProperty** — all navigator/screen overrides via C++ patches
2. **NO persistent CDP sessions** — inject scripts then detach
3. **Modular** — each feature is independent (can enable/disable)
4. **Data-driven** — JSON config drives everything
5. **Clean code** — no 3000-line files, max 500 lines per module
6. **NST-quality UI** — professional, clean, intuitive

---

*Created: 2026-03-25*
*Status: PLAN READY — Awaiting approval for implementation*
