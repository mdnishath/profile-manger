# MailNexus Pro - System Architecture

## Overview

MailNexus Pro is a professional desktop application for bulk Gmail account management and Google Maps review automation. It combines an Electron.js desktop interface with a Python Flask backend, using Playwright for browser automation.

---

## High-Level Architecture

```
+---------------------------------------------------+
|              Electron Desktop App                  |
|  +---------------------------------------------+  |
|  |         Renderer (HTML/CSS/JS)               |  |
|  |  Dashboard | Process | Config | Debug | Reports |
|  +---------------------------------------------+  |
|         |  REST API (localhost:5000)  |  SSE Logs   |
+---------|-----------------------------|-------------+
          v                             v
+---------------------------------------------------+
|              Flask Backend (server.py)              |
|  - File upload & Excel processing                  |
|  - Worker thread management                        |
|  - Real-time progress tracking (SSE)               |
|  - Report generation                               |
|  - Configuration management                        |
+---------------------------------------------------+
          |
          v
+---------------------------------------------------+
|          Multi-Worker Orchestration Layer           |
|  +-------+  +-------+  +-------+  +-------+       |
|  |Worker1|  |Worker2|  |Worker3|  |Worker N|       |
|  +-------+  +-------+  +-------+  +-------+       |
|  Each worker:                                      |
|    - Unique proxy (SOCKS5/HTTP)                    |
|    - Unique browser fingerprint (OS/UA/TZ)         |
|    - Independent Chromium instance                 |
|    - Thread-safe Excel row locking                 |
+---------------------------------------------------+
          |
          v
+---------------------------------------------------+
|            Playwright Chromium Browsers             |
|  - Anti-detection flags                            |
|  - Per-worker fingerprint injection                |
|  - SOCKS5 auth bridge (local relay)                |
+---------------------------------------------------+
```

---

## Directory Structure

```
gmail_boat/
├── config/                           # Configuration files
│   ├── proxy.json                    # Proxy settings (SOCKS5/HTTP)
│   ├── fingerprint.json              # Browser fingerprint config
│   ├── urls.json                     # Target URLs and delays
│   └── settings.json                 # Global bot settings
│
├── electron-app/                     # Electron desktop app
│   ├── main.js                       # Electron main process
│   ├── preload.js                    # Security preload scripts
│   ├── package.json                  # Node.js dependencies
│   ├── backend/
│   │   ├── server.py                 # Flask REST API server
│   │   └── main_entry.py            # PyInstaller entry point
│   └── renderer/
│       ├── index.html                # UI layout
│       ├── app.js                    # UI controllers & logic
│       └── styles.css                # Styling (dark theme)
│
├── shared/                           # Shared utilities
│   ├── proxy_manager.py              # Proxy pool & assignment
│   ├── fingerprint_manager.py        # Per-worker fingerprints
│   ├── socks_bridge.py               # SOCKS5 auth relay
│   ├── browser.py                    # Chromium launch & config
│   ├── debug_launcher.py             # Debug browser inspector
│   ├── excel_handler.py              # Thread-safe Excel R/W
│   ├── worker_runner.py              # Multi-worker orchestration
│   ├── logger.py                     # Logging utilities
│   └── signout.py                    # Google logout handler
│
├── src/                              # Core auth & utilities
│   ├── login_flow.py                 # Gmail login orchestration
│   ├── screen_detector.py            # Login screen state detection
│   ├── gmail_authenticator.py        # Authentication handler
│   ├── utils.py                      # Config manager, TOTP
│   └── excel_processor.py            # Excel reading
│
├── step1/                            # Step 1: Language & Activity
│   ├── runner.py                     # Step 1 worker
│   ├── language_change.py            # Set language to English
│   └── operations/
│       ├── activity_fix.py           # Clear activity/notifications
│       └── safe_browsing.py          # Safe browsing toggle
│
├── step2/                            # Step 2: Account Operations
│   ├── runner.py                     # Step 2 worker
│   └── operations/
│       ├── password_change.py        # Change password
│       ├── recovery_email.py         # Update recovery email
│       ├── recovery_phone.py         # Update recovery phone
│       ├── authenticator.py          # Change authenticator
│       ├── backup_codes.py           # Generate backup codes
│       ├── phone_2fa.py              # Add/replace 2FA phone
│       ├── remove_devices.py         # Remove devices
│       └── name_change.py            # Change account name
│
├── step3/                            # Step 3: Google Maps Reviews
│   ├── runner.py                     # Step 3 worker
│   └── operations/
│       ├── write_review.py           # Post reviews (R3)
│       ├── delete_all_reviews.py     # Delete all reviews (R1)
│       ├── delete_not_posted_reviews.py  # Delete drafts (R2)
│       └── profile_lock.py          # Profile lock toggle (R4/R5)
│
├── step4/                            # Step 4: Future operations
│
├── output/                           # Generated reports
├── success/                          # Successful account archives
├── failed/                           # Failed account archives
└── docs/                             # Documentation
```

---

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Desktop Framework | Electron.js (v28+) |
| Frontend | HTML5, CSS3, Vanilla JavaScript |
| Backend | Python 3.9+, Flask, Flask-CORS |
| Browser Automation | Playwright (Chromium) |
| Threading | Python asyncio + threading |
| Excel Processing | openpyxl, pandas |
| 2FA/TOTP | pyotp |
| Logging | loguru |
| Proxy | SOCKS5/HTTP + custom auth bridge |
| Packaging | PyInstaller + Electron Builder |

---

## Flask Backend API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| POST | `/api/shutdown` | Shutdown server |
| POST | `/api/file-info` | Get Excel file stats |
| POST | `/api/start-processing` | Start bot processing |
| POST | `/api/stop-processing` | Stop running bot |
| GET | `/api/progress` | Current progress & metrics |
| GET | `/api/log-stream` | SSE real-time log stream |
| POST | `/api/logs/clear` | Clear in-memory logs |
| GET | `/api/config` | Load configuration |
| POST | `/api/config` | Save configuration |
| GET | `/api/proxy` | Load proxy settings |
| POST | `/api/proxy` | Save proxy settings |
| GET | `/api/fingerprint` | Load fingerprint config |
| POST | `/api/fingerprint` | Save fingerprint config |
| GET | `/api/reports` | List generated reports |
| DELETE | `/api/reports/all` | Delete all reports |
| POST | `/api/debug/launch` | Launch debug browsers |
| POST | `/api/debug/close` | Close debug browsers |
| GET | `/api/debug/status` | Debug browser status |

---

## Data Flow

### Excel Processing Pipeline

```
User uploads Excel file
        |
        v
Flask /api/start-processing
        |
        v
prepare_excel_with_common_settings()
  - Mark empty Status rows as PENDING
  - Apply common ops/passwords to PENDING rows
        |
        v
ExcelProcessor distributes accounts to N workers
  - Thread-safe row-level locking
  - Each worker gets unique proxy + fingerprint
        |
        v
Each worker runs autonomously:
  1. Launch Chromium (proxy + fingerprint)
  2. Login (email → password → 2FA/backup)
  3. Execute selected operations
  4. Logout
  5. Update Excel row (Status + Share Link)
        |
        v
Report Generation:
  - output/accounts_output_TIMESTAMP.xlsx (all results)
  - success/success_TIMESTAMP.xlsx (successful only)
  - failed/failed_TIMESTAMP.xlsx (failed + errors)
  - Hyperlinks applied to all URL cells
```

### Proxy Flow

```
config/proxy.json → ProxyManager.load()
        |
        v
ProxyManager.assign(num_workers)
  - Shuffle proxy list
  - 1:1 mapping: worker → proxy
  - Extra workers run without proxy
        |
        v
For SOCKS5 with auth:
  SocksBridge starts local relay (127.0.0.1:random_port)
  Browser → Bridge (no auth) → Real Proxy (with auth)
```

### Fingerprint Flow

```
config/fingerprint.json → FingerprintManager.load()
        |
        v
FingerprintManager.assign(num_workers)
  For each worker:
    - Choose OS (random or fixed)
    - Pick Chrome version (120-131)
    - Generate matching User-Agent
    - Determine timezone:
        auto_timezone + proxy → geo-lookup IP
        otherwise → random from global pool
        |
        v
Applied to Chromium context:
  - navigator.userAgent
  - navigator.platform
  - Intl.DateTimeFormat timezone
```

### Login Flow

```
execute_login_flow(page, account, ...)
        |
        v
while not logged_in:
  detect_current_screen()
    ├── EMAIL_INPUT      → Fill email, click Next
    ├── PASSWORD_INPUT   → Fill password, click Next
    ├── AUTHENTICATOR    → Generate TOTP, fill, verify
    ├── BACKUP_CODE      → Fill backup code, verify
    ├── CAPTCHA          → Wait 30s for manual input
    ├── SECURITY_BLOCK   → FAIL (account locked)
    └── SUCCESS          → Return success
```

---

## Step Operations Detail

### Step 1: Language & Security

| Code | Operation | Description |
|------|-----------|-------------|
| L1 | Language Change | Set account language to English (US) |
| L2 | Activity Fix | Clear notifications + security checkup |
| L4 | Safe Browsing ON | Enable Google Safe Browsing |
| L5 | Safe Browsing OFF | Disable Google Safe Browsing |

### Step 2: Account Management

| Code | Operation | Description |
|------|-----------|-------------|
| Op 1 | Change Password | Set new password |
| Op 2 | Recovery Email | Update recovery email |
| Op 3 | Recovery Phone | Update recovery phone |
| Op 4 | Authenticator | Replace authenticator app |
| Op 5 | Backup Codes | Generate new backup codes |
| Op 6 | 2FA Phone | Add/replace 2FA phone |
| Op 7 | Remove Devices | Remove all connected devices |
| Op 8 | Name Change | Update account display name |

### Step 3: Google Maps Reviews

| Code | Operation | Description |
|------|-----------|-------------|
| R1 | Delete All Reviews | Delete every posted review |
| R2 | Delete Drafts | Delete pending/draft reviews |
| R3 | Write Review | Post new review (stars + optional text) |
| R4 | Profile Lock ON | Make profile private |
| R5 | Profile Lock OFF | Make profile public |

**R3 Write Review - Detailed Flow:**
- Navigate to Google Maps place URL
- Wait for popup overlay (6 CSS selectors)
- Select star rating (multi-tier click: dispatch_event → force click → JS mouse events)
- Fill review text (if provided)
- Click Post button
- **Star-only**: Mark as posted, no share link
- **With text**: Navigate to contributor page → Reviews tab → reload polling (10s wait, 5s intervals, 6 max reloads) → extract share link or auto-delete if stuck

---

## Key Components

### ExcelProcessor (shared/excel_handler.py)
Thread-safe Excel handler with row-level locking. Prevents duplicate processing across workers. Supports read retries with backoff.

### ProxyManager (shared/proxy_manager.py)
Loads and parses multiple proxy formats: `ip:port`, `ip:port:user:pass`, `user:pass@ip:port`, `http://`, `socks5://`. Strictly assigns one proxy per worker.

### FingerprintManager (shared/fingerprint_manager.py)
Generates unique browser fingerprints per worker: OS type, Chrome version, User-Agent, timezone. Supports geo-lookup from proxy IP for realistic timezone matching.

### SocksBridge (shared/socks_bridge.py)
Local SOCKS5 authentication relay. Solves Playwright's limitation of not supporting SOCKS5 auth natively. Creates transparent bidirectional TCP relay.

### ScreenDetector (src/screen_detector.py)
Identifies current login screen state using DOM selectors. Handles 10+ screen states: email input, password, 2FA, captcha, security blocks, success.

---

## Deployment Modes

### Development
```
Electron (npm start) → Flask server.py → Python step scripts
Config: project root config/
Browsers: downloaded on first run
```

### Production (Packaged)
```
MailNexus Pro.exe → backend.exe (PyInstaller) → bundled scripts
Config: process.resourcesPath/config/
Browsers: ~/AppData/Local/MailNexus Pro/playwright/
```

---

## Error Handling

- **Login failures**: Invalid credentials skip, locked accounts fail, captcha waits for manual input
- **Operation failures**: Each operation in try/except, partial success allowed
- **Network issues**: Proxy timeout retry (3x), page load timeout (15-30s)
- **Excel locking**: Read/write retry with backoff (5 retries, 2s delay)
- **Review stuck**: Reload polling (6 max), auto-delete if not live after all retries
