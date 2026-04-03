# MailNexus Pro - Feature Checklist & Roadmap

## Completed Features

### Core Infrastructure
- [x] Electron desktop application with modern dark UI
- [x] Flask REST API backend (localhost:5000)
- [x] Server-Sent Events (SSE) for real-time log streaming
- [x] Multi-worker parallel processing with asyncio + threading
- [x] Thread-safe Excel handler with row-level locking
- [x] Auto-generated Excel reports (all/success/failed)
- [x] Clickable hyperlinks in Excel reports
- [x] PyInstaller packaging for production builds
- [x] Electron Builder for Windows installer (NSIS)

### Authentication & Login
- [x] Gmail login automation (email + password)
- [x] TOTP/Authenticator 2FA support (auto-generated codes)
- [x] Backup code authentication
- [x] Multi-screen login flow detection (10+ screen states)
- [x] Captcha detection (waits for manual intervention)
- [x] Security block detection (locked/suspended accounts)
- [x] Google account logout after operations

### Proxy System
- [x] HTTP proxy support
- [x] SOCKS5 proxy support (with authentication)
- [x] SOCKS5 auth bridge (local TCP relay for Playwright)
- [x] Multi-format proxy parsing (6 formats)
- [x] 1:1 proxy-to-worker assignment
- [x] Proxy enable/disable toggle in UI
- [x] Multi-line proxy editor in UI

### Browser Fingerprinting
- [x] Per-worker unique fingerprint generation
- [x] OS type selection (Windows/macOS/Linux/Android/Random)
- [x] Chrome version pool (120-131)
- [x] User-Agent generation matching OS + version
- [x] Timezone auto-lookup from proxy IP (geo-lookup)
- [x] Random timezone fallback (40+ global timezones)
- [x] Anti-detection Chromium flags
- [x] Fingerprint config in UI

### Debug Tools
- [x] Debug browser inspector (1-10 simultaneous browsers)
- [x] Public IP detection
- [x] Geo-location display (city, country)
- [x] User-Agent verification
- [x] Timezone verification
- [x] Proxy auth confirmation
- [x] Live debug logs via SSE

### Step 1: Language & Security
- [x] L1: Change account language to English (US)
- [x] L2: Activity fix (clear notifications + security checkup)
- [x] L4: Enable Safe Browsing
- [x] L5: Disable Safe Browsing

### Step 2: Account Operations
- [x] Op 1: Change password
- [x] Op 2: Update recovery email
- [x] Op 3: Update recovery phone
- [x] Op 4: Change authenticator app
- [x] Op 5: Generate backup codes
- [x] Op 6: Add/replace 2FA phone
- [x] Op 7: Remove all devices
- [x] Op 8: Change account name

### Step 3: Google Maps Reviews
- [x] R1: Delete all reviews
- [x] R2: Delete not-posted/draft reviews
- [x] R3: Write review (stars + optional text)
- [x] R4: Profile lock ON (make private)
- [x] R5: Profile lock OFF (make public)
- [x] Popup overlay detection (6 CSS selectors)
- [x] Multi-tier star click (dispatch_event, force click, JS mouse events)
- [x] Reload-based pending retry (10s wait, 5s intervals, 6 max reloads)
- [x] Auto-delete stuck reviews after max retries
- [x] Share link extraction from contributor page
- [x] Star-only reviews (no text) - skip share link
- [x] Review status tracking (live/pending/not_posted)
- [x] Live/pending/failed count reporting

### UI Features
- [x] Dashboard with real-time stats
- [x] File picker for Excel upload
- [x] Step selection (1-4) with radio buttons
- [x] Operation checkboxes per step
- [x] Common parameter fields (password, recovery, worker count)
- [x] Start/Stop/Reset controls
- [x] Live progress bar
- [x] Current account display
- [x] Live log panel (SSE streaming)
- [x] Configuration editor
- [x] Proxy manager panel
- [x] Fingerprint settings panel
- [x] Reports list with download/delete
- [x] Backend start/stop with status indicator
- [x] R3 (Write Review) checked by default
- [x] R1 (Delete All) unchecked by default

---

## Missing Features & Improvements

### High Priority

- [ ] **SMS/OTP Interception**: Auto-capture SMS codes for phone-based 2FA (currently requires manual input)
- [ ] **Account Creation**: Bulk create new Gmail accounts (currently only manages existing accounts)
- [ ] **Retry Failed Accounts**: One-click retry for all FAILED accounts without re-uploading
- [ ] **Schedule Operations**: Schedule batch operations to run at specific times
- [ ] **Email Operations**: Read, send, forward, delete emails in bulk
- [ ] **Profile Photo Upload**: Upload profile pictures to Gmail accounts
- [ ] **YouTube Operations**: Subscribe, like, comment automation

### Medium Priority

- [ ] **Multi-Step Pipeline**: Chain Step 1 → Step 2 → Step 3 in a single run without re-uploading
- [ ] **Account Groups**: Tag and organize accounts into groups for targeted operations
- [ ] **Proxy Health Check**: Test all proxies before starting and auto-exclude dead ones
- [ ] **Proxy Rotation**: Rotate proxies mid-session if one fails
- [ ] **Import from CSV**: Support CSV files in addition to Excel
- [ ] **Export Formats**: Export reports as CSV, JSON, PDF in addition to Excel
- [ ] **Operation History**: Track all operations performed on each account over time
- [ ] **Dark/Light Theme Toggle**: Add light theme option for UI
- [ ] **Multi-Language UI**: Support Bengali, Hindi, and other languages in the interface
- [ ] **Google Business Profile**: Manage Google Business profiles (name, address, hours, photos)
- [ ] **Review Templates**: Pre-built review text templates with variable substitution
- [ ] **Review Scheduling**: Post reviews at random intervals to appear natural
- [ ] **Star Distribution**: Smart star rating distribution (not all 5-star)

### Low Priority

- [ ] **macOS/Linux Build**: Package for macOS and Linux (currently Windows only)
- [ ] **Cloud Dashboard**: Web-based dashboard for remote monitoring
- [ ] **API Access**: REST API for external tool integration
- [ ] **Webhook Notifications**: Send notifications (Telegram, Discord, Slack) on completion
- [ ] **Account Import from Gmail**: Import account list directly from Gmail contacts
- [ ] **Browser Profile Persistence**: Save and reuse browser profiles across sessions
- [ ] **Captcha Solver Integration**: Integrate with 2Captcha or Anti-Captcha services
- [ ] **IP Rotation Service**: Built-in residential proxy integration
- [ ] **Batch Preview**: Preview which operations will run on which accounts before starting
- [ ] **Undo Operations**: Undo last batch operation (restore previous passwords, etc.)
- [ ] **Keyboard Shortcuts**: Power-user keyboard shortcuts for common actions
- [ ] **Custom Operation Scripts**: Plugin system for user-defined operations
- [ ] **Account Health Score**: Calculate and display account health metrics

### Technical Debt & Improvements

- [ ] **Unit Tests**: Add comprehensive test suite for all operations
- [ ] **CI/CD Pipeline**: Automated builds and releases on GitHub
- [ ] **Error Categorization**: Classify errors (network, auth, operation) for better debugging
- [ ] **Structured Logging**: JSON-formatted logs for machine parsing
- [ ] **Config Validation**: Schema validation for all config files
- [ ] **Database Backend**: Replace Excel with SQLite for better concurrency
- [ ] **Worker Pool**: Dynamic worker pool with auto-scaling
- [ ] **Memory Optimization**: Reduce memory usage for large account batches (1000+)
- [ ] **Playwright Update**: Keep Playwright and Chromium versions current
- [ ] **Code Documentation**: Add docstrings and inline comments to all modules

---

## Version History

### V2 (Current)
- Proxy system with SOCKS5 auth bridge
- Browser fingerprinting (OS/UA/TZ)
- Debug browser inspector
- Enhanced UI with configuration panels
- Google Maps review automation (R1-R5)
- Multi-worker parallel processing
- Real-time SSE logging
- Excel report generation with hyperlinks
- Reload-based review status polling
- Auto-delete stuck reviews

### V1 (Initial)
- Basic Gmail login automation
- Step 1 & Step 2 operations
- Single-worker processing
- Basic Excel input/output
- Command-line interface
