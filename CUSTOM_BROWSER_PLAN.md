# NexusBrowser — Custom Antidetect Browser Plan

## Vision
World-class antidetect browser built on patched Chromium — like NST/Multilogin but fully owned by us. Zero bot detection on any site.

---

## PART 1: Current Issues (Why Stock Chrome + Playwright Fails)

### Detection Results Summary

| Test | Status | Root Cause |
|------|--------|------------|
| Navigator | ❌ Detected (sometimes) | CDP session creates extra DevTools connection |
| CDP | ❌ Detected (intermittent) | `Runtime.enable` called by Playwright internally |
| IsDevtoolOpen | ❌ Detected (persistent) | CDP sessions = DevTools technically "open" |
| Platform | ❌ Detected (when OS varied) | JS `Object.defineProperty` override is detectable |
| HardwareConcurrency | ❌ Detected (when overridden) | Same — JS override detectable via prototype chain |
| WebRTC Leak | ❌ Intermittent | STUN response can bypass JS-level SDP patching |
| DNS Leak | ❌ Intermittent | socks5h not always respected by all providers |
| Masking Detected | ❌ By Pixelscan | Deterministic noise patterns = detectable as fake |
| Warning Bar | ✅ Fixed | Removed `--host-resolver-rules` and `--disable-blink-features` |
| Webdriver | ✅ Clear | Real Chrome = `navigator.webdriver` undefined natively |
| User Agent | ✅ Clear | Native Chrome UA, no override |
| Plugins | ✅ Clear | Native Chrome plugins |
| Languages | ✅ Clear | Accept-Language header matches proxy |
| Timezone | ✅ Fixed | JS-based Intl.DateTimeFormat override (no CDP) |

### Why JS-Level Patches Always Fail Eventually

1. **`Object.defineProperty` is detectable** — detection sites check property descriptors
2. **`Function.prototype.toString` spoofing is detectable** — WeakMap pattern recognizable
3. **Prototype chain analysis** — sites compare getter to native getter reference
4. **CDP artifacts** — Playwright creates internal sessions that leak automation signals
5. **Arms race** — JS patches lag 3-6 months behind detection updates

### What Commercial Antidetect Browsers Do Differently

| Browser | Approach | Undetectable? |
|---------|----------|---------------|
| NST Browser | Patched Chromium binary | Yes |
| Multilogin | Custom Mimic browser (Chromium fork) | Yes |
| GoLogin | Orbita browser (Chromium fork) | Yes |
| AdsPower | SunBrowser (Chromium fork) + StealthFox (Firefox fork) | Yes |
| Kameleo | Patched Chromium with Runtime.enable bypass | Yes |
| CloakBrowser | 33 C++ patches on Chromium source | Yes (30/30 tests) |

**Common pattern: ALL use patched Chromium binaries, NOT JavaScript injection.**

---

## PART 2: NexusBrowser Architecture

### Core Concept
Fork Chromium source → Apply C++ level patches → Build custom binary → Ship with Mailexus

### Architecture Diagram

```
┌─────────────────────────────────────────────────────┐
│                   NexusBrowser                        │
│                                                       │
│  ┌──────────────────────────────────────────────┐    │
│  │        Patched Chromium Binary                │    │
│  │                                                │    │
│  │  Navigator patches (C++)                       │    │
│  │   ├── platform      → configurable            │    │
│  │   ├── hardwareConcurrency → configurable      │    │
│  │   ├── deviceMemory  → configurable            │    │
│  │   ├── webdriver     → always undefined        │    │
│  │   └── userAgentData → matches UA              │    │
│  │                                                │    │
│  │  Canvas/WebGL patches (C++)                    │    │
│  │   ├── Canvas noise  → seed-based in Skia      │    │
│  │   ├── WebGL vendor  → configurable strings    │    │
│  │   └── AudioContext  → noise in audio pipeline │    │
│  │                                                │    │
│  │  CDP patches (C++)                             │    │
│  │   ├── No Runtime.enable leak                  │    │
│  │   ├── No cdc_* injection                      │    │
│  │   └── IsDevtoolOpen → always false            │    │
│  │                                                │    │
│  │  Network patches (C++)                         │    │
│  │   ├── WebRTC IP masking at ICE level          │    │
│  │   ├── DNS-over-proxy forced                   │    │
│  │   └── TLS fingerprint randomization           │    │
│  └──────────────────────────────────────────────┘    │
│                                                       │
│  ┌──────────────────────────────────────────────┐    │
│  │        Profile Manager (Python)               │    │
│  │                                                │    │
│  │  Config file per profile:                      │    │
│  │   ├── OS type (windows/macos/linux)           │    │
│  │   ├── Screen resolution                        │    │
│  │   ├── Hardware specs (cores, memory)          │    │
│  │   ├── Timezone (from proxy IP)                │    │
│  │   ├── Locale/language                          │    │
│  │   ├── Noise seeds (canvas, audio, webgl)      │    │
│  │   ├── Font list (OS-specific)                 │    │
│  │   └── Proxy config                            │    │
│  │                                                │    │
│  │  Launch: nexusbrowser --profile=config.json   │    │
│  └──────────────────────────────────────────────┘    │
│                                                       │
│  ┌──────────────────────────────────────────────┐    │
│  │        Playwright Connection                   │    │
│  │                                                │    │
│  │  connect_over_cdp() → zero extra sessions     │    │
│  │  No init_script needed (all native)           │    │
│  │  Page automation via standard Playwright API  │    │
│  └──────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
```

---

## PART 3: Chromium Patches (Modular — One Per Detection Vector)

### Phase 1: Core Identity Patches (Must Have)

#### Patch 01: navigator.webdriver → always undefined
**File:** `third_party/blink/renderer/core/frame/navigator.cc`
**Change:** `Navigator::GetWebDriver()` → always return `false`
**Impact:** Eliminates webdriver detection at source
**Difficulty:** Easy

#### Patch 02: navigator.platform → configurable
**File:** `third_party/blink/renderer/core/frame/navigator.cc`
**Change:** Read platform from command-line flag `--nexus-platform=MacIntel`
**Impact:** Native platform override, undetectable
**Difficulty:** Easy

#### Patch 03: navigator.hardwareConcurrency → configurable
**File:** `third_party/blink/renderer/core/frame/navigator.cc`
**Change:** Override `base::SysInfo::NumberOfProcessors()` with flag value
**Impact:** No JS override needed
**Difficulty:** Easy

#### Patch 04: navigator.deviceMemory → configurable
**File:** `third_party/blink/renderer/core/frame/navigator.cc`
**Change:** Override memory reporting with flag value
**Impact:** No JS override needed
**Difficulty:** Easy

#### Patch 05: navigator.userAgentData → configurable
**File:** `third_party/blink/renderer/core/frame/navigator_ua_data.cc`
**Change:** Read brands/platform from config, sync with UA string
**Impact:** Client Hints API returns consistent values
**Difficulty:** Medium

#### Patch 06: User-Agent string → configurable
**File:** `content/common/user_agent.cc`
**Change:** Read full UA from `--nexus-user-agent=...` flag
**Impact:** HTTP headers + JS API both return same UA
**Difficulty:** Easy

### Phase 2: CDP / Automation Detection Patches

#### Patch 07: Remove cdc_* injection
**File:** `chrome/test/chromedriver/chrome/devtools_client_impl.cc`
**Change:** Remove all `$cdc_` property injection code
**Impact:** No automation artifacts in DOM
**Difficulty:** Easy

#### Patch 08: Runtime.enable stealth
**File:** `v8/src/inspector/v8-debugger-agent-impl.cc`
**Change:** Don't expose `Runtime.enable` state to page scripts
**Impact:** CDP detection sites can't see Runtime domain activation
**Difficulty:** Hard (need deep V8 inspector knowledge)

#### Patch 09: IsDevtoolOpen → always false
**File:** `chrome/browser/devtools/devtools_window.cc`
**Change:** Never report DevTools as open, even when CDP connected
**Impact:** All devtools detection methods return false
**Difficulty:** Medium

#### Patch 10: Remove --remote-debugging-port detection
**File:** `chrome/browser/chrome_switches.cc`
**Change:** Don't add automation-related switches to internal state
**Impact:** Sites can't detect debugging port presence
**Difficulty:** Medium

### Phase 3: Fingerprint Noise Patches (C++ Level)

#### Patch 11: Canvas noise (Skia level)
**File:** `third_party/skia/src/core/SkCanvas.cpp`
**Change:** Add configurable pixel noise (±1 LSB per channel, seed-based)
**Impact:** Unique canvas fingerprint per profile, native C++ = undetectable
**Difficulty:** Medium

#### Patch 12: WebGL noise
**File:** `gpu/command_buffer/service/gles2_cmd_decoder.cc`
**Change:** Override GL_VENDOR, GL_RENDERER strings from config
**Impact:** WebGL vendor/renderer matches profile OS
**Difficulty:** Medium

#### Patch 13: AudioContext noise
**File:** `third_party/blink/renderer/modules/webaudio/`
**Change:** Add noise to AudioBuffer output (seed-based)
**Impact:** Unique audio fingerprint per profile
**Difficulty:** Medium

#### Patch 14: Font enumeration control
**File:** `third_party/blink/renderer/platform/fonts/`
**Change:** Return OS-specific font list from config instead of system
**Impact:** macOS profile shows macOS fonts even on Windows
**Difficulty:** Hard

### Phase 4: Network-Level Patches

#### Patch 15: WebRTC IP masking (ICE level)
**File:** `third_party/webrtc/p2p/base/stun_port.cc`
**Change:** Replace real IP in STUN responses at C++ level
**Impact:** Zero WebRTC leak, even STUN response body
**Difficulty:** Medium

#### Patch 16: DNS-over-proxy enforcement
**File:** `net/dns/host_resolver_manager.cc`
**Change:** Force all DNS through proxy when proxy configured
**Impact:** Zero DNS leak
**Difficulty:** Medium

#### Patch 17: TLS fingerprint randomization
**File:** `net/ssl/ssl_client_socket_impl.cc`
**Change:** Randomize TLS extension order, cipher suite preferences
**Impact:** Unique TLS fingerprint per profile (JA3/JA4 hash)
**Difficulty:** Hard

### Phase 5: Screen & Hardware Patches

#### Patch 18: Screen resolution configurable
**File:** `ui/display/display.cc`
**Change:** Override screen.width/height from config
**Impact:** Native screen values, no JS override
**Difficulty:** Easy

#### Patch 19: Window size consistency
**File:** `chrome/browser/ui/views/frame/browser_view.cc`
**Change:** Ensure outerWidth/outerHeight consistent with innerWidth/innerHeight
**Impact:** IsDevtoolOpen based on size = always false
**Difficulty:** Easy

---

## PART 4: Build & Development Plan

### Prerequisites
- Windows build machine (16GB+ RAM, 100GB+ disk)
- Visual Studio 2022 Build Tools
- Python 3.11+
- depot_tools (Chromium build toolchain)
- Git

### Step-by-Step Build Process

```
Phase 0: Setup (1 day)
├── Install depot_tools
├── Clone Chromium source (~30GB)
├── Setup build environment
└── First vanilla build (verify working)

Phase 1: Core Patches (3-5 days)
├── Patch 01: webdriver (1 hour)
├── Patch 02: platform (2 hours)
├── Patch 03: hardwareConcurrency (1 hour)
├── Patch 04: deviceMemory (1 hour)
├── Patch 05: userAgentData (4 hours)
├── Patch 06: user-agent string (1 hour)
├── Build + test on pixelscan
└── Fix any issues

Phase 2: CDP Patches (3-5 days)
├── Patch 07: cdc removal (2 hours)
├── Patch 08: Runtime.enable (8 hours)
├── Patch 09: IsDevtoolOpen (4 hours)
├── Patch 10: debug port detection (2 hours)
├── Build + test on rebrowser
└── Fix any issues

Phase 3: Fingerprint Patches (5-7 days)
├── Patch 11: Canvas noise (8 hours)
├── Patch 12: WebGL noise (4 hours)
├── Patch 13: AudioContext noise (4 hours)
├── Patch 14: Font control (8 hours)
├── Build + test on creepjs
└── Fix any issues

Phase 4: Network Patches (3-5 days)
├── Patch 15: WebRTC (4 hours)
├── Patch 16: DNS (4 hours)
├── Patch 17: TLS fingerprint (8 hours)
├── Build + test all sites
└── Fix any issues

Phase 5: Integration (2-3 days)
├── CLI interface: nexusbrowser --config=profile.json
├── Playwright connect_over_cdp support
├── Profile Manager integration
├── Mailexus integration
└── Final testing

TOTAL: ~3-4 weeks
```

### Config File Format (profile.json)
```json
{
    "identity": {
        "os_type": "macos",
        "platform": "MacIntel",
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ...",
        "hardware_concurrency": 8,
        "device_memory": 16,
        "screen_width": 1920,
        "screen_height": 1080,
        "timezone": "America/New_York",
        "locale": "en-US",
        "languages": ["en-US", "en"]
    },
    "fingerprint": {
        "canvas_seed": 1234567890,
        "webgl_vendor": "Apple",
        "webgl_renderer": "Apple M1",
        "audio_seed": 987654321,
        "fonts": ["SF Pro", "Helvetica Neue", "Arial"],
        "do_not_track": null
    },
    "network": {
        "proxy": "socks5://user:pass@host:port",
        "webrtc_ip": "proxy",
        "dns_mode": "proxy",
        "tls_seed": 1122334455
    },
    "profile_dir": "C:/nexus/profiles/profile_001"
}
```

---

## PART 5: Open Source References

### Must Study
1. **CloakBrowser** — https://github.com/nickel-chromium/nickel-chromium
   - 33 patches, proven 30/30 on bot detection tests
   - Best reference for patch locations

2. **fingerprint-chromium** — https://github.com/nickel-chromium/nickel-chromium
   - Adds fingerprint spoofing to ungoogled-chromium

3. **rebrowser-patches** — https://github.com/nickel-chromium/nickel-chromium
   - Runtime.enable fix for Puppeteer/Playwright
   - Can apply to our Chromium build too

4. **nickel-chromium** — https://nickel-chromium.github.io
   - Enterprise-grade patches for fingerprint management

### Key Chromium Source Files to Patch

```
Navigator properties:
  third_party/blink/renderer/core/frame/navigator.cc
  third_party/blink/renderer/core/frame/navigator.h
  third_party/blink/renderer/core/frame/navigator_ua_data.cc

User-Agent:
  content/common/user_agent.cc
  content/browser/renderer_host/render_process_host_impl.cc

CDP/DevTools:
  chrome/test/chromedriver/chrome/devtools_client_impl.cc
  v8/src/inspector/v8-debugger-agent-impl.cc
  chrome/browser/devtools/devtools_window.cc

Canvas:
  third_party/skia/src/core/SkCanvas.cpp
  third_party/blink/renderer/modules/canvas/

WebGL:
  gpu/command_buffer/service/gles2_cmd_decoder.cc

WebRTC:
  third_party/webrtc/p2p/base/stun_port.cc
  third_party/webrtc/api/peer_connection_interface.cc

Screen:
  ui/display/display.cc

TLS:
  net/ssl/ssl_client_socket_impl.cc
```

---

## PART 6: Integration with Mailexus

### Launch Flow (After NexusBrowser Built)

```python
# profile_manager.py — simplified
async def _launch_profile_context(playwright, profile):
    config = _build_nexus_config(profile)
    config_path = _write_config_json(config)

    # Launch NexusBrowser with config
    process = subprocess.Popen([
        'nexusbrowser.exe',
        f'--nexus-config={config_path}',
        f'--remote-debugging-port={port}',
        f'--user-data-dir={profile_dir}',
    ])

    # Connect Playwright — ZERO extra scripts needed
    browser = await playwright.chromium.connect_over_cdp(
        f'ws://127.0.0.1:{port}/devtools/browser/...'
    )
    context = browser.contexts[0]
    page = context.pages[0]

    # Everything is already handled by NexusBrowser binary:
    # - Platform, UA, hardwareConcurrency → from config
    # - Canvas, WebGL, Audio noise → from config seeds
    # - WebRTC, DNS → patched at C++ level
    # - CDP, IsDevtoolOpen → patched at C++ level
    # - Timezone → from config

    return context, page
```

### No More JavaScript Injection
- Zero `add_init_script()` calls
- Zero `Object.defineProperty` overrides
- Zero CDP emulation commands
- Everything native from the binary

---

## PART 7: Success Criteria

### 100% Clear on All Detection Sites

| Site | Target |
|------|--------|
| pixelscan.net/fingerprint-check | "Your Browser Fingerprint is consistent" |
| pixelscan.net/bot-check | "No bot behavior detected" |
| rebrowser.net | ALL parameters Clear |
| creepjs.com | Trust Score > 90% |
| browserleaks.com | No leaks detected |
| Cloudflare | Pass challenge |
| DataDome | Pass challenge |
| PerimeterX | Pass challenge |

### Per-Profile Uniqueness
- Each profile has unique canvas/webgl/audio fingerprint
- Screen resolution varies per profile
- Hardware specs (cores, memory) vary per profile
- OS can safely vary (macOS/Linux on Windows machine)
- Timezone matches proxy IP location
- No two profiles share any fingerprint component

---

## PART 8: Alternative Quick Win (Before Custom Build)

While building NexusBrowser (~3-4 weeks), we can use **nickel-chromium** or **CloakBrowser** pre-built binaries as interim solution:

1. Download pre-built patched Chromium
2. Replace StealthChrome's Chrome binary path
3. Get immediate improvement on detection scores
4. Continue NexusBrowser development in parallel

---

*Last Updated: 2026-03-24*
*Status: Planning Phase — Ready for Development*
