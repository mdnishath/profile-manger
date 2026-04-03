# Remaining Work - Electron Gmail Bot

## ✅ Completed
1. Electron project structure
2. Modern UI design (matching your image)
3. Frontend navigation and state management
4. Real-time progress UI
5. Professional dark theme

## 🔄 In Progress - Python Backend Server

Need to create: `backend/server.py`

This will be a Flask API that:
- Accepts requests from Electron frontend
- Calls existing gmail_bot_production.py logic
- Provides real-time progress updates
- Returns results to frontend

### API Endpoints Needed:
```
POST /api/file-info          # Get Excel file stats
POST /api/start-processing   # Start processing
POST /api/stop-processing    # Stop processing
GET  /api/progress           # Get current progress
GET  /api/reports            # Get list of reports
```

## 🔧 Critical Fixes Needed

### 1. Authenticator & Backup Code Save Fix
**File:** `test_operations.py` (or wherever change_authenticator_app is)

**Problem:** 2FA key and backup codes not saving to Excel

**Solution:**
- After generating new auth key, MUST save to Excel immediately
- After generating backup codes, MUST save to Excel immediately
- Add verification that data was saved

### 2. New Button Selectors
**File:** `test_operations.py` or new `selectors.py`

Add these selectors:
```python
# Authenticator Next Button (after "can't scan")
AUTHENTICATOR_NEXT_BTN = 'button[data-id="OCpkoe"]'

# Verify Button
VERIFY_BTN = 'button[data-id="dtOep"]'

# Get New Codes Button
GET_NEW_CODES_BTN = 'button[jsname="Wilgpb"]'
```

### 3. Backup Code Login Screen
**File:** `src/screen_detector.py`

Add new screen type:
```python
class LoginScreen(Enum):
    ...
    BACKUP_CODE_INPUT = "backup_code_input"
```

Add detection:
```python
async def detect_backup_code_screen(self):
    backup_input = 'input#backupCodePin'
    if await self.page.locator(backup_input).count() > 0:
        return LoginScreen.BACKUP_CODE_INPUT
```

### 4. Try Another Way Logic
**File:** `gmail_bot_production.py` or `test_operations.py`

Add logic:
```python
# If authenticator fails, try backup code
if screen == LoginScreen.TOTP_FAILED:
    # Click "Try another way"
    await page.locator('button:has-text("Try another way")').click()
    await asyncio.sleep(2)

    # Check for backup code input
    screen = await detector.detect_current_screen()
    if screen == LoginScreen.BACKUP_CODE_INPUT:
        # Get backup code from Excel
        backup_code = account.get('Backup Code', '')
        if backup_code:
            await page.locator('input#backupCodePin').fill(backup_code)
            await page.locator('button:has-text("Next")').click()
```

### 5. Login Success Detection
**File:** `gmail_bot_production.py`

**Current:** Detects success screen
**Required:** MUST capture password change URL

```python
# Login is only successful if we capture this URL
password_url = None

# Try to click "Change password" and capture URL
if current_screen == LoginScreen.SUCCESS_SCREEN:
    await page.locator('a[aria-label="Change password"]').click()
    await asyncio.sleep(3)
    password_url = page.url

# If password_url is None, login FAILED
if not password_url:
    raise Exception("Login failed - could not capture password URL")
```

### 6. Real-time Progress Updates
**File:** Backend API server

Need to implement:
- WebSocket or SSE for real-time updates
- Update progress after each account
- Send live logs to frontend
- Update Excel in real-time

Current issue: Progress bar updates only at end

Solution:
```python
# After each account
progress = {
    'current': completed_count,
    'total': total_count,
    'percent': (completed_count / total_count) * 100,
    'current_account': email,
    'status': 'processing'
}
# Broadcast to frontend
```

## 📋 Files to Create

### 1. `backend/server.py`
Flask API server with all endpoints

### 2. `backend/processor_wrapper.py`
Wrapper around existing code to provide progress callbacks

### 3. `backend/selectors.py`
All button selectors in one place

### 4. `backend/excel_handler.py`
Real-time Excel updates with locking

## 🏗️ Build Process

After all fixes:

```bash
cd electron-app

# Install dependencies
npm install

# Test in dev mode
npm start

# Build .exe
npm run build:win
```

Output: `dist/Gmail Bot Pro Setup.exe`

## ⚡ Priority Order

1. **Create Python backend API** (server.py) - Critical
2. **Fix authenticator/backup code save** - Critical
3. **Add new button selectors** - High
4. **Add Try Another Way screen** - High
5. **Fix login success detection** - Critical
6. **Real-time progress** - High
7. **Test everything** - Critical
8. **Build .exe** - Final

## 📝 Notes

- Keep existing code working
- Backend API wraps existing logic
- Frontend just displays data from backend
- Real-time via polling (simple) or WebSocket (better)

## 🎯 Expected Result

- Professional Electron UI (like your image)
- Real-time progress and logs
- All operations working correctly
- Data saved to Excel reliably
- Clean .exe installer
- Works offline after installation

---

**Next Step:** Create `backend/server.py` Flask API
